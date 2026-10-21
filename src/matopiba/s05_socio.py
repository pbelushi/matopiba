"""Etapa 5: indicadores socioeconômicos por município.

Cada bloco gera data/interim/socio_<bloco>.parquet. Consultas ao Base dos Dados agregam no
servidor (nunca baixam microdados) e passam por dry run com limite de GB (settings.yaml).
Ao final, gera outputs/logs/cobertura_socio.md.

Uso:
  python -m matopiba.s05_socio                 # todos os blocos + relatório
  python -m matopiba.s05_socio pib saude       # só alguns blocos (+ relatório)
  python -m matopiba.s05_socio cobertura       # só o relatório
"""

import gzip
import json
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

from matopiba.config import path, settings
from matopiba.gcp import bq_query

CFG = settings()["socio"]
ANO_BASE = settings()["monetario"]["ano_base"]
BD = "basedosdados"


def _q(sql: str, gb: float | None = None) -> pd.DataFrame:
    return bq_query(sql, max_gb=gb or CFG["max_gb_padrao"])


def _salvar(df: pd.DataFrame, bloco: str) -> pd.DataFrame:
    df.to_parquet(path("interim") / f"socio_{bloco}.parquet", index=False)
    print(f"  socio_{bloco}: {len(df):,} linhas, {df['id_municipio'].nunique():,} municípios",
          flush=True)
    return df


def deflator() -> pd.Series:
    """Fator para reais constantes do ano-base: IPCA médio do ano-base / IPCA médio do ano."""
    ipca = _q(f"SELECT ano, AVG(indice) indice FROM `{BD}.br_ibge_ipca.mes_brasil` GROUP BY 1")
    s = ipca.set_index("ano")["indice"]
    return s.loc[ANO_BASE] / s


# ---------------------------------------------------------------- população e PIB

def populacao() -> pd.DataFrame:
    df = _q(f"SELECT ano, id_municipio, populacao FROM `{BD}.br_ibge_populacao.municipio`")
    return _salvar(df, "populacao")


def pib() -> pd.DataFrame:
    df = _q(f"""SELECT id_municipio, ano, pib, impostos_liquidos, va, va_agropecuaria,
                       va_industria, va_servicos, va_adespss
                FROM `{BD}.br_ibge_pib.municipio`""")
    pop = pd.read_parquet(path("interim") / "socio_populacao.parquet")
    f = df["ano"].map(deflator())
    for c in ["pib", "impostos_liquidos", "va", "va_agropecuaria", "va_industria",
              "va_servicos", "va_adespss"]:
        df[f"{c}_real"] = df[c] * f
    df = df.merge(pop, on=["ano", "id_municipio"], how="left")
    df["pib_pc_real"] = df["pib_real"] / df["populacao"]
    return _salvar(df.drop(columns="populacao"), "pib")


# ---------------------------------------------------------------- emprego formal (RAIS)

def rais() -> pd.DataFrame:
    """Vínculos ativos em 31/12, massa salarial e salário médio, agro vs. resto.

    Agro: CNAE 2.0 divisões 01–03 (2006+); CNAE 1.0 divisões 01, 02 e 05 (1994–2005);
    subsetor IBGE 25 antes disso. Valores em R$ só a partir de 1999 (o BD não traz a
    remuneração em moeda antes disso); salário em salários mínimos para todos os anos.
    """
    df = _q(f"""
    WITH v AS (
      SELECT ano, id_municipio, valor_remuneracao_media, valor_remuneracao_dezembro,
             valor_remuneracao_media_sm,
             CASE
               WHEN cnae_2 IS NOT NULL THEN IF(SUBSTR(cnae_2, 1, 2) IN ('01','02','03'),
                                               'agro', 'nao_agro')
               WHEN cnae_1 IS NOT NULL THEN IF(SUBSTR(cnae_1, 1, 2) IN ('01','02','05'),
                                               'agro', 'nao_agro')
               WHEN subsetor_ibge IS NOT NULL AND subsetor_ibge NOT IN ('-1', 'OUTR/IGN')
                 THEN IF(subsetor_ibge IN ('25', 'AGRICULTURA'), 'agro', 'nao_agro')
               ELSE 'ignorado' END AS setor
      FROM `{BD}.br_me_rais.microdados_vinculos`
      WHERE vinculo_ativo_3112 = '1' AND id_municipio IS NOT NULL
    )
    SELECT ano, id_municipio, setor, COUNT(*) AS vinculos,
           SUM(valor_remuneracao_media) AS massa_media, SUM(valor_remuneracao_dezembro)
           AS massa_dezembro, SUM(valor_remuneracao_media_sm) AS soma_sm
    FROM v GROUP BY 1, 2, 3""", CFG["max_gb_rais"])
    w = df.pivot_table(index=["id_municipio", "ano"], columns="setor",
                       values=["vinculos", "massa_media", "massa_dezembro", "soma_sm"],
                       aggfunc="sum", fill_value=0)
    w.columns = [f"{a}_{b}" for a, b in w.columns]
    w = w.reset_index()
    for m in ["vinculos", "massa_media", "massa_dezembro", "soma_sm"]:
        cols = [c for c in w.columns if c.startswith(m + "_")]
        w[f"{m}_total"] = w[cols].sum(axis=1)
    f = w["ano"].map(deflator())
    real = w["ano"] >= CFG["rais_ano_valores"]
    for s in ["total", "agro", "nao_agro"]:
        w[f"massa_salarial_real_{s}"] = (w[f"massa_media_{s}"] * 12 * f).where(real)
        w[f"salario_medio_real_{s}"] = (w[f"massa_media_{s}"] / w[f"vinculos_{s}"] * f).where(real)
        w[f"salario_medio_sm_{s}"] = w[f"soma_sm_{s}"] / w[f"vinculos_{s}"]
    w["share_vinculos_agro"] = w["vinculos_agro"] / w["vinculos_total"]
    w["share_setor_ignorado"] = w.get("vinculos_ignorado", 0) / w["vinculos_total"]
    keep = ["id_municipio", "ano", "share_vinculos_agro", "share_setor_ignorado"]
    keep += [c for c in w.columns if c.startswith(("vinculos_", "massa_salarial_real_",
                                                   "salario_medio_"))]
    return _salvar(w[keep], "rais")


# ---------------------------------------------------------------- saúde

def saude() -> pd.DataFrame:
    a0, a1 = CFG["saude_anos"]
    nv = _q(f"""
    SELECT ano, id_municipio_residencia AS id_municipio, COUNT(*) AS nascidos_vivos,
           COUNTIF(pre_natal_agr = '4') AS nv_prenatal_7mais,
           COUNTIF(pre_natal_agr IN ('1','2','3','4')) AS nv_prenatal_informado,
           COUNTIF(classificacao_pre_natal IN ('4','5')) AS nv_prenatal_adequado_k,
           COUNTIF(classificacao_pre_natal IN ('1','2','3','4','5')) AS nv_prenatal_class
    FROM `{BD}.br_ms_sinasc.microdados`
    WHERE ano BETWEEN {a0} AND {a1} AND id_municipio_residencia IS NOT NULL
    GROUP BY 1, 2""")
    ob = _q(f"""
    SELECT ano, id_municipio, SUM(numero_obitos) AS obitos_menor_1
    FROM `{BD}.br_ms_sim.municipio_causa_idade`
    WHERE ano BETWEEN {a0} AND {a1} AND idade = 0 AND id_municipio IS NOT NULL
    GROUP BY 1, 2""")
    df = nv.merge(ob, on=["ano", "id_municipio"], how="outer")
    df["nascidos_vivos"] = df["nascidos_vivos"].fillna(0)
    # sem registro de óbito infantil num município-ano com nascimentos = zero óbitos
    df["obitos_menor_1"] = df["obitos_menor_1"].fillna(0)
    df["tmi"] = (df["obitos_menor_1"] / df["nascidos_vivos"] * 1000).where(
        df["nascidos_vivos"] > 0)
    df["flag_tmi_instavel"] = df["nascidos_vivos"] < CFG["tmi_nv_min"]
    df["pct_prenatal_7mais"] = df["nv_prenatal_7mais"] / df["nv_prenatal_informado"]
    df["pct_prenatal_adequado_kotelchuck"] = (
        df["nv_prenatal_adequado_k"] / df["nv_prenatal_class"]).where(df["nv_prenatal_class"] > 0)
    df["dado_preliminar"] = df["ano"] >= CFG["saude_ano_preliminar"]
    return _salvar(df, "saude")


# ---------------------------------------------------------------- educação

def _baixar_zip(url: str, destino) -> None:
    import io
    import zipfile

    destino.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    # o servidor do INEP às vezes derruba a conexão (WinError 10054): tentar de novo
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                conteudo = r.read()
            break
        except OSError as e:
            if tentativa == 4:
                raise
            print(f"  download falhou ({e}); nova tentativa em {30 * (tentativa + 1)}s",
                  flush=True)
            time.sleep(30 * (tentativa + 1))
    zipfile.ZipFile(io.BytesIO(conteudo)).extractall(destino)


def _ideb_inep(bd: pd.DataFrame) -> pd.DataFrame:
    """IDEB da rede pública nas planilhas do INEP, só para município-ano-etapa ausentes no BD
    (o BD não tem 2015)."""
    partes = []
    for etapa, info in CFG["inep_ideb"].items():
        arq = path("raw") / info["arquivo"]
        if not arq.exists():
            _baixar_zip(info["url"], arq.parents[1])
        d = pd.read_excel(arq, header=9, engine="calamine", dtype={"CO_MUNICIPIO": str})
        d = d[d["REDE"].astype(str).str.startswith("P")]
        anos = sorted({int(c[-4:]) for c in d.columns if str(c).startswith("VL_OBSERVADO_")})
        for a in anos:
            partes.append(pd.DataFrame({
                "ano": a, "id_municipio": d["CO_MUNICIPIO"].str.strip(), "etapa": etapa,
                "ideb": pd.to_numeric(d[f"VL_OBSERVADO_{a}"], errors="coerce"),
                "nota_saeb_media_padronizada": pd.to_numeric(d.get(f"VL_NOTA_MEDIA_{a}"),
                                                             errors="coerce"),
                "indicador_rendimento": pd.to_numeric(d.get(f"VL_INDICADOR_REND_{a}"),
                                                      errors="coerce"),
            }))
    if not partes:
        return pd.DataFrame()
    inep = pd.concat(partes, ignore_index=True)
    tem = set(zip(bd["id_municipio"], bd["ano"], bd["etapa"], strict=True))
    novo = inep[[k not in tem for k in zip(inep["id_municipio"], inep["ano"], inep["etapa"],
                                            strict=True)]]
    return novo.dropna(subset=["ideb"]).assign(fonte_ideb="inep_planilha")


def educacao() -> pd.DataFrame:
    ideb = _q(f"""
    SELECT ano, id_municipio, anos_escolares, ideb, nota_saeb_media_padronizada,
           indicador_rendimento
    FROM `{BD}.br_inep_ideb.municipio`
    WHERE rede = 'publica' AND ensino = 'fundamental'""")
    ideb["etapa"] = ideb["anos_escolares"].map(lambda s: "iniciais" if "iniciais" in s
                                               else "finais")
    ideb["fonte_ideb"] = "basedosdados"
    ideb = pd.concat([ideb, _ideb_inep(ideb)], ignore_index=True)
    w = ideb.pivot_table(index=["id_municipio", "ano"], columns="etapa",
                         values=["ideb", "nota_saeb_media_padronizada", "indicador_rendimento"])
    w.columns = [f"{a}_{b}" for a, b in w.columns]
    mat = _q(f"""
    SELECT ano, id_municipio, etapa_ensino, SUM(quantidade_matricula) AS m
    FROM `{BD}.br_inep_sinopse_estatistica_educacao_basica.etapa_ensino_serie`
    GROUP BY 1, 2, 3""")
    etapas = {
        "Educação Infantil - Creche": "matriculas_creche",
        "Educação Infantil - Pré-Escola": "matriculas_pre_escola",
        "Ensino Fundamental - Anos Iniciais": "matriculas_fund_iniciais",
        "Ensino Fundamental - Anos Finais": "matriculas_fund_finais",
        "Ensino Médio Regular": "matriculas_medio",
    }
    outras = pd.Series(np.where(mat["etapa_ensino"].str.startswith("EJA"), "matriculas_eja",
                                "matriculas_profissional"), index=mat.index)
    mat["col"] = mat["etapa_ensino"].map(etapas).fillna(outras)
    m = mat.pivot_table(index=["id_municipio", "ano"], columns="col", values="m",
                        aggfunc="sum", fill_value=0)
    m["matriculas_basica_total"] = m.sum(axis=1)
    df = w.join(m, how="outer").reset_index()
    return _salvar(df, "educacao")


# ---------------------------------------------------------------- Atlas Brasil e censos

def atlas() -> pd.DataFrame:
    cols = ["idhm", "idhm_e", "idhm_l", "idhm_r", "indice_gini", "indice_theil",
            "prop_pobreza", "prop_pobreza_extrema", "prop_vulner_pobreza", "renda_pc",
            "expectativa_vida", "mortalidade_1", "taxa_analfabetismo_15_mais",
            "expectativa_anos_estudo"]
    df = _q(f"SELECT ano, id_municipio, {', '.join(cols)} FROM `{BD}.mundo_onu_adh.municipio`")
    return _salvar(df, "atlas")


def _sidra(tabela: int, variaveis: list[int], classif: dict[int, str | list], nivel: str,
           ufs: list[str] | None = None) -> pd.DataFrame:
    """Consulta a API v3 de agregados do IBGE. `classif` = {id: 'Total' | 'todas'}."""
    url_meta = f"https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/metadados"
    meta = _get_json(url_meta)
    partes = []
    for cid, sel in classif.items():
        cl = next(c for c in meta["classificacoes"] if c["id"] == cid)
        if sel == "Total":
            cats = [str(c["id"]) for c in cl["categorias"] if c["nome"] == "Total"]
        else:
            cats = [str(c["id"]) for c in cl["categorias"] if c["nome"] != "Total"]
        partes.append(f"{cid}[{','.join(cats)}]")
    clas = "|".join(partes)
    vars_ = "|".join(map(str, variaveis))
    periodo = str(meta["periodicidade"]["fim"])
    locs = [f"{nivel}[N3[{u}]]" for u in ufs] if ufs else [f"{nivel}[all]"]
    linhas = []
    for loc in locs:
        url = (f"https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos/{periodo}"
               f"/variaveis/{vars_}?localidades={loc}&classificacao={clas}")
        for v in _get_json(url):
            for r in v["resultados"]:
                cat = {k: list(c["categoria"].values())[0] for k, c in
                       zip([c["id"] for c in r["classificacoes"]], r["classificacoes"],
                           strict=True)}
                for s in r["series"]:
                    val = s["serie"][periodo]
                    linhas.append({"id_municipio": s["localidade"]["id"], "variavel": v["id"],
                                   **{f"c{k}": n for k, n in cat.items()},
                                   "valor": pd.to_numeric(val, errors="coerce")
                                   if val not in ("-",) else 0.0})
    return pd.DataFrame(linhas)


def _get_json(url: str, tentativas: int = 4):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            return json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
        except Exception:  # noqa: BLE001
            if i == tentativas - 1:
                raise
            time.sleep(5 * (i + 1))


def censo2022() -> pd.DataFrame:
    base = _q(f"""SELECT id_municipio, populacao, domicilios, taxa_alfabetizacao, idade_mediana
                  FROM `{BD}.br_ibge_censo_2022.municipio`""")
    t = f"{BD}.br_ibge_censo_2022.caracteristica_domicilio_grupo_idade_raca"
    esg = _q(f"""SELECT id_municipio,
      SUM(IF(tipo_esgotamento_sanitario IN ('Rede geral, rede pluvial ou fossa ligada à rede',
         'Fossa séptica ou fossa filtro não ligada à rede'), populacao, 0)) AS adequado,
      SUM(IF(tipo_esgotamento_sanitario NOT IN ('Rede geral ou pluvial',
         'Fossa séptica ou fossa filtro ligada à rede'), populacao, 0)) AS total
      FROM `{t}_esgotamento_sanitario` GROUP BY 1""", 2)
    agua = _q(f"""SELECT id_municipio,
      SUM(IF(tipo_ligacao_rede_geral = 'Possui ligação à rede geral e a utiliza como forma principal',
             populacao, 0)) AS rede,
      SUM(IF(NOT STRPOS(tipo_ligacao_rede_geral, ' - ') > 0, populacao, 0)) AS total
      FROM `{t}_ligacao_abastecimento_agua` GROUP BY 1""", 2)
    lixo = _q(f"""SELECT id_municipio,
      SUM(IF(tipo_destino_lixo = 'Coletado', populacao, 0)) AS coletado,
      SUM(IF(tipo_destino_lixo NOT IN ('Coletado no domicílio por serviço de limpeza',
             'Depositado em caçamba de serviço de limpeza'), populacao, 0)) AS total
      FROM `{t}_destino_lixo` GROUP BY 1""", 2)
    df = base.copy()
    df["pct_esgoto_adequado"] = df["id_municipio"].map(
        esg.set_index("id_municipio").eval("adequado / total"))
    df["pct_agua_rede_geral"] = df["id_municipio"].map(agua.set_index("id_municipio")
                                                       .eval("rede / total"))
    df["pct_lixo_coletado"] = df["id_municipio"].map(lixo.set_index("id_municipio")
                                                     .eval("coletado / total"))
    t = CFG["sidra_renda_2022"]
    r = _sidra(t["tabela"], list(t["variaveis"].values()),
               {c: "Total" for c in t["classificacoes"]}, "N6")
    nomes = {v: k for k, v in t["variaveis"].items()}
    r = r.pivot_table(index="id_municipio", columns="variavel", values="valor")
    r.columns = [nomes[int(c)] for c in r.columns]
    df = df.merge(r.reset_index(), on="id_municipio", how="left")
    df["ano"] = 2022
    return _salvar(df, "censo2022")


def migracao() -> pd.DataFrame:
    """% de não naturais do município (1991, 2000, 2010) e da UF (2010), ponderado."""
    t = f"{BD}.br_ibge_censo_demografico.microdados_pessoa"
    specs = {
        1991: ("v7301", "v0314 = '3'", "v0314 IS NOT NULL", None),
        2000: ("p001", "v0415 = '2'", "v0415 IS NOT NULL", None),
        2010: ("peso_amostral", "v0618 = '3'", "v0618 IS NOT NULL", "v0619 = '3'"),
    }
    partes = []
    for ano, (peso, nao_nat, valido, nao_nat_uf) in specs.items():
        uf = (f", SUM(IF({nao_nat_uf}, {peso}, 0)) / SUM(IF({valido}, {peso}, 0)) "
              "AS pct_nao_natural_uf") if nao_nat_uf else ""
        d = _q(f"""SELECT id_municipio, {ano} AS ano,
            SUM(IF({nao_nat}, {peso}, 0)) / SUM(IF({valido}, {peso}, 0))
              AS pct_nao_natural_municipio{uf}
            FROM `{t}_{ano}` GROUP BY 1""", CFG["max_gb_censo"])
        partes.append(d)
    return _salvar(pd.concat(partes, ignore_index=True), "migracao")


# ---------------------------------------------------------------- transferências

def transferencias() -> pd.DataFrame:
    """Famílias beneficiárias (NIS distintos por mês) e valor pago, por programa.

    Bolsa Família (até out/2021), Auxílio Brasil (nov/2021–fev/2023), Novo Bolsa Família
    (mar/2023+), pela competência do pagamento.
    """
    t = f"{BD}.br_cgu_beneficios_cidadao"
    partes = []
    for prog in ["bolsa_familia_pagamento", "auxilio_brasil", "novo_bolsa_familia"]:
        d = _q(f"""SELECT ano_competencia AS ano, mes_competencia AS mes, id_municipio,
                     COUNT(DISTINCT nis_favorecido) AS familias, SUM(valor_parcela) AS valor
                   FROM `{t}.{prog}` WHERE id_municipio IS NOT NULL GROUP BY 1, 2, 3""",
               CFG["max_gb_transferencias"])
        d["programa"] = prog
        partes.append(d)
    m = pd.concat(partes, ignore_index=True)
    mens = m.groupby(["id_municipio", "ano", "mes"], as_index=False)[["familias", "valor"]].sum()
    anual = mens.groupby(["id_municipio", "ano"]).agg(
        familias_media_mensal=("familias", "mean"), meses=("mes", "nunique"),
        valor_total=("valor", "sum")).reset_index()
    dez = mens[mens["mes"] == 12].set_index(["id_municipio", "ano"])["familias"]
    anual["familias_dezembro"] = anual.set_index(["id_municipio", "ano"]).index.map(dez)
    anual["valor_total_real"] = anual["valor_total"] * anual["ano"].map(deflator())
    prog = m.groupby(["id_municipio", "ano"])["programa"].agg(lambda s: "+".join(sorted(set(s))))
    anual["programas"] = anual.set_index(["id_municipio", "ano"]).index.map(prog)
    return _salvar(anual, "transferencias")


# ---------------------------------------------------------------- estrutura fundiária

def _gini_agrupado(g: pd.DataFrame) -> float:
    """Gini da terra a partir de classes de área (n de estabelecimentos e área por classe)."""
    g = g[(g["n"] > 0)].sort_values("ordem")
    if g["area"].sum() <= 0 or len(g) < 2:
        return np.nan
    x = np.concatenate([[0], np.cumsum(g["n"]) / g["n"].sum()])
    y = np.concatenate([[0], np.cumsum(g["area"]) / g["area"].sum()])
    return float(1 - np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1])))


def fundiaria() -> pd.DataFrame:
    ufs = sorted(pd.read_parquet(path("processed") / "universo.parquet")["id_municipio"]
                 .str[:2].unique())
    partes = []
    for ano, t in CFG["sidra_censo_agro"].items():
        meta = _get_json(f"https://servicodados.ibge.gov.br/api/v3/agregados/{t['tabela']}"
                         "/metadados")
        cl = next(c for c in meta["classificacoes"] if c["id"] == 220)
        ordem = {c["nome"]: i for i, c in enumerate(cl["categorias"])}
        classif = {c: "Total" for c in t["classificacoes_total"]}
        classif[220] = "todas"
        d = _sidra(t["tabela"], [183, 184], classif, "N6", ufs)
        d = d.rename(columns={"c220": "classe"})
        # unstack (e não pivot_table com soma) para preservar os NaN dos valores suprimidos
        w = (d.set_index(["id_municipio", "classe", "variavel"])["valor"].unstack("variavel")
             .reset_index().rename(columns={"183": "n", "184": "area", 183: "n", 184: "area"}))
        w = w[~w["classe"].str.contains("sem área", case=False)].copy()
        w["ordem"] = w["classe"].map(ordem)
        # limites das classes; a classe aberta do topo recebe o dobro do limite inferior
        lims = (pd.Series({c: _limite_inferior(c) for c in w["classe"].unique()})
                .sort_values())
        sup = lims.shift(-1).fillna(lims * 2)
        w["lim_inf"] = w["classe"].map(lims)
        # área suprimida por sigilo ("X"): n × ponto médio da classe
        sup_area = w["area"].isna() & (w["n"] > 0)
        w["area_imputada"] = np.where(sup_area, w["n"] * (w["lim_inf"]
                                      + w["classe"].map(sup)) / 2, 0.0)
        w["area"] = w["area"].fillna(0) + w["area_imputada"]
        w["n"] = w["n"].fillna(0)
        out = w.groupby("id_municipio").apply(
            lambda g: pd.Series({
                "n_estabelecimentos": g["n"].sum(),
                "area_estabelecimentos_ha": g["area"].sum(),
                "share_area_imputada": g["area_imputada"].sum() / g["area"].sum()
                if g["area"].sum() > 0 else np.nan,
                "gini_terra": _gini_agrupado(g),
                "share_estab_menos_10ha": g.loc[g["lim_inf"] < 10, "n"].sum() / g["n"].sum()
                if g["n"].sum() > 0 else np.nan,
                "share_area_1000ha_mais": g.loc[g["lim_inf"] >= 1000, "area"].sum()
                / g["area"].sum() if g["area"].sum() > 0 else np.nan,
            }), include_groups=False).reset_index()
        out["ano"] = int(ano)
        partes.append(out)
    return _salvar(pd.concat(partes, ignore_index=True), "fundiaria")


def _limite_inferior(nome: str) -> float:
    """Limite inferior (ha) de uma classe como 'De 10 a menos de 20 ha' ou '2.500 ha e mais'."""
    import re
    s = nome.replace(".", "").replace(",", ".")
    n = re.findall(r"[\d.]+", s)
    if not n:
        return np.nan
    if s.lower().startswith("mais de 0"):
        return 0.0
    return float(n[0])


# ---------------------------------------------------------------- conflitos (CPT)

def conflitos() -> pd.DataFrame | None:
    arq = path("raw") / CFG["cpt_arquivo"]
    if not arq.exists():
        print(f"  conflitos: arquivo da CPT não encontrado em {arq} (download manual)")
        return None
    df = pd.read_csv(arq, dtype={"id_municipio": str})
    return _salvar(df, "conflitos")


# ---------------------------------------------------------------- cobertura

def cobertura() -> str:
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    n = len(universo)
    linhas = ["# Cobertura dos indicadores socioeconômicos (Etapa 5)", "",
              f"Universo: {n:,} municípios. % de municípios = média, entre os anos com dado, da "
              "fração do universo com valor não nulo (mínimo entre parênteses).",
              f"Valores monetários `*_real` em R$ constantes de {ANO_BASE} (IPCA médio anual); "
              "Atlas Brasil em R$ de agosto de 2010; renda do Censo 2022 em R$ correntes de 2022.",
              ""]
    for arq in sorted(path("interim").glob("socio_*.parquet")):
        df = pd.read_parquet(arq)
        df = df[df["id_municipio"].isin(universo["id_municipio"])]
        linhas += [f"## {arq.stem}", "", "| variável | anos | nº anos | % municípios |",
                   "|---|---|---|---|"]
        for c in df.columns:
            if c in ("id_municipio", "ano") or df[c].dtype == object:
                continue
            d = df.dropna(subset=[c])
            if d.empty:
                linhas.append(f"| {c} | — | 0 | 0% |")
                continue
            por_ano = d.groupby("ano")["id_municipio"].nunique() / n
            linhas.append(f"| {c} | {d['ano'].min()}–{d['ano'].max()} | {len(por_ano)} | "
                          f"{por_ano.mean():.1%} ({por_ano.min():.1%}) |")
        linhas.append("")
    if not (path("interim") / "socio_conflitos.parquet").exists():
        linhas += ["## socio_conflitos", "", "Pendente: dados da CPT (download manual).", ""]
    texto = "\n".join(linhas)
    (path("logs") / "cobertura_socio.md").write_text(texto, encoding="utf-8")
    return texto


BLOCOS = {
    "populacao": populacao, "pib": pib, "rais": rais, "saude": saude, "educacao": educacao,
    "atlas": atlas, "censo2022": censo2022, "migracao": migracao,
    "transferencias": transferencias, "fundiaria": fundiaria, "conflitos": conflitos,
}


def main() -> int:
    pedidos = [a for a in sys.argv[1:] if not a.startswith("-")] or list(BLOCOS)
    for b in pedidos:
        if b == "cobertura":
            continue
        t = time.time()
        print(f"[{b}]", flush=True)
        BLOCOS[b]()
        print(f"  {time.time() - t:.0f}s", flush=True)
    print(cobertura())
    return 0


if __name__ == "__main__":
    sys.exit(main())
