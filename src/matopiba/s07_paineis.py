"""Etapa 7: montagem dos painéis município × ano, AMC × ano e AMC × censo.

Cada variável declara em VARS a fonte, a regra de agregação para AMC, a descrição e a
unidade; a mesma tabela gera docs/DICIONARIO.md. Regras de agregação:
  soma        soma dos municípios (áreas, contagens, valores)
  razao       recalculada a partir dos componentes já agregados (nunca média de razões)
  media_pop   média ponderada pela população (taxas sem componentes disponíveis)
  media_area  média ponderada pela área municipal (atributos do território)
  media_pond  média ponderada por outra variável (indicada em `peso`)
  max         flags (verdadeiro se algum município da AMC tem a flag)
Tratamentos e instrumentos são recalculados em cada nível a partir das variáveis agregadas.

Saídas:
  data/processed/painel_municipio.parquet
  data/processed/painel_amc.parquet
  data/processed/painel_censos.parquet
  docs/DICIONARIO.md

Uso: python -m matopiba.s07_paineis
"""

import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

from matopiba.config import ROOT, path, settings

TRAT = settings()["tratamento"]
INST = settings()["instrumento"]
ANOS = list(range(settings()["mapbiomas"]["anos"][0], settings()["mapbiomas"]["anos"][1] + 1))


@dataclass(frozen=True)
class V:
    fonte: str
    agregacao: str
    descricao: str
    unidade: str = ""
    num: str | None = None       # razao: numerador
    den: str | None = None       # razao: denominador
    mult: float = 1.0            # razao: multiplicador
    peso: str | None = None      # media_pond: variável de peso


_AREAS_MB = {
    "soja": "soja (39)", "outras_temp": "outras lavouras temporárias (41)",
    "algodao": "algodão (62)", "arroz": "arroz (40)", "cana": "cana (20)",
    "perenes": "lavouras perenes (35, 46, 47, 48)", "pasto": "pastagem (15)",
    "mosaico": "mosaico de usos (21)", "silvicultura": "silvicultura (9)",
    "florestal": "formação florestal (3)", "savanica": "formação savânica (4)",
    "campestre": "formação campestre (12)", "urbano": "área urbanizada (24)",
    "agua": "rio, lago, oceano e aquicultura (31, 33)",
    "agri_temp": "agricultura temporária: soja + arroz + outras temporárias + algodão",
    "nativa": "vegetação nativa (níveis 1 e 2 do MapBiomas: floresta e vegetação herbácea "
              "e arbustiva)",
}

VARS: dict[str, V] = {
    "area_ha": V("universo (IBGE 2024)", "soma", "Área do município", "ha"),
    "cerrado_share": V("universo (IBGE biomas 2025)", "media_area",
                       "Fração da área no bioma Cerrado", "0–1"),
    **{f"area_{k}_ha": V("MapBiomas C11", "soma", f"Área de {d}", "ha")
       for k, d in _AREAS_MB.items()},
    **{f"share_{k}": V("MapBiomas C11", "razao", f"Participação de {d} na área municipal",
                       "0–1", num=f"area_{k}_ha", den="area_ha") for k, d in _AREAS_MB.items()},
    "area_total_mb_ha": V("MapBiomas C11", "soma", "Soma de todas as classes do MapBiomas", "ha"),
    "flag_area_mb": V("MapBiomas C11", "max",
                      "Soma das classes difere da área IBGE em > 2% em algum ano (costeiros)"),
    "desmat_ha": V("MapBiomas C11 desmatamento", "soma",
                   "Desmatamento bruto: perda de vegetação primária + secundária", "ha/ano"),
    "desmat_prim_ha": V("MapBiomas C11 desmatamento", "soma",
                        "Perda de vegetação nativa primária", "ha/ano"),
    "desmat_sec_ha": V("MapBiomas C11 desmatamento", "soma",
                       "Perda de vegetação nativa secundária", "ha/ano"),
    "perda_nativa_liq_ha": V("MapBiomas C11", "soma",
                             "Perda líquida de vegetação nativa (nativa t-1 − nativa t)",
                             "ha/ano"),
    # luzes
    "luz_soma": V("VIIRS (2013+) e Li-DMSP encadeado (1992–2012)", "soma",
                  "Soma da radiância noturna (série principal encadeada)", "nW/cm²/sr"),
    "luz_media": V("idem", "media_area", "Radiância média por pixel (série principal)",
                   "nW/cm²/sr"),
    "luz_pc": V("luzes + população", "razao", "Radiância por habitante (série principal)",
                "nW/cm²/sr por hab.", num="luz_soma", den="populacao"),
    "viirs_soma": V("NOAA VIIRS anual", "soma", "Soma de radiância VIIRS (average_masked)",
                    "nW/cm²/sr"),
    "dmsp_soma": V("NOAA DMSP-OLS V4", "soma", "Soma de DN do DMSP (stable_lights)", "DN"),
    "li_dmsp_soma": V("Li et al. (2020)", "soma", "Soma de DN do DMSP intercalibrado", "DN"),
    "chen_soma": V("Chen et al. (2021)", "soma",
                   "Soma de radiância VIIRS-like (robustez; quebra em 2011–2013)", "nW/cm²/sr"),
    "flag_luz_base_zero": V("luzes", "max",
                            "Li-DMSP ou VIIRS zero no ano-base do encadeamento (2013)"),
    # área construída
    "area_urbana_mb_ha": V("MapBiomas C11", "soma", "Área urbanizada (= area_urbano_ha)", "ha"),
    "area_construida_ha": V("Open Buildings Temporal", "soma",
                            "Área construída 'suave' (presença × área), só Matopiba e Cerrado "
                            "fora, 2016–2023", "ha"),
    "n_edificacoes": V("Open Buildings Temporal", "soma",
                       "Contagem estimada de edificações, só Matopiba e Cerrado fora", "nº"),
    # máscara urbana fixa (Etapa 4b; só Matopiba e Cerrado fora)
    "area_mascara_2000_ha": V("MapBiomas C11 (Etapa 4b)", "soma",
                              "Área da máscara urbana de 2000 (classe 24 + buffer de 1 km)",
                              "ha"),
    "area_mascara_2012_ha": V("MapBiomas C11 (Etapa 4b)", "soma",
                              "Área da máscara urbana de 2012 (classe 24 + buffer de 1 km)",
                              "ha"),
    "viirs_urbano_soma": V("NOAA VIIRS anual (Etapa 4b)", "soma",
                           "Radiância VIIRS dentro da máscara urbana de 2012", "nW/cm²/sr"),
    "viirs_fora_soma": V("NOAA VIIRS anual (Etapa 4b)", "soma",
                         "Radiância VIIRS fora da máscara urbana de 2012", "nW/cm²/sr"),
    "luz_urbana_pc": V("VIIRS + população", "razao",
                       "Radiância dentro da máscara urbana de 2012 por habitante",
                       "nW/cm²/sr por hab.", num="viirs_urbano_soma", den="populacao"),
    "n_edificacoes_urb": V("Open Buildings Temporal, 4 m (Etapa 4b)", "soma",
                           "Edificações dentro da máscara urbana de 2012", "nº"),
    "area_construida_urb_ha": V("Open Buildings Temporal, 4 m (Etapa 4b)", "soma",
                                "Área construída (presença > 0,5) na máscara urbana de 2012",
                                "ha"),
    "area_suave_urb_ha": V("Open Buildings Temporal, 4 m (Etapa 4b)", "soma",
                           "Área construída 'suave' (presença × área) na máscara de 2012",
                           "ha"),
    "volume_urb_m3": V("Open Buildings Temporal, 4 m (Etapa 4b)", "soma",
                       "Volume construído (altura × área, presença > 0,5) na máscara de 2012",
                       "m³"),
    "altura_media_urb_m": V("Open Buildings Temporal, 4 m (Etapa 4b)", "razao",
                            "Altura média das edificações na máscara de 2012 (ponderada pela "
                            "área)", "m", num="volume_urb_m3", den="area_construida_urb_ha",
                            mult=1e-4),
    # população e PIB
    "populacao": V("IBGE (BD br_ibge_populacao)", "soma", "População residente", "hab."),
    "pib_real": V("IBGE PIB dos Municípios", "soma", "PIB", "R$ de 2023"),
    "va_agropecuaria_real": V("IBGE PIB dos Municípios", "soma", "VA da agropecuária",
                              "R$ de 2023"),
    "va_industria_real": V("IBGE PIB dos Municípios", "soma", "VA da indústria", "R$ de 2023"),
    "va_servicos_real": V("IBGE PIB dos Municípios", "soma",
                          "VA dos serviços (exceto adm. pública)", "R$ de 2023"),
    "va_adespss_real": V("IBGE PIB dos Municípios", "soma",
                         "VA da administração, defesa, educação e saúde públicas e seguridade",
                         "R$ de 2023"),
    "impostos_liquidos_real": V("IBGE PIB dos Municípios", "soma",
                                "Impostos líquidos de subsídios", "R$ de 2023"),
    "pib_pc_real": V("IBGE", "razao", "PIB per capita", "R$ de 2023/hab.", num="pib_real",
                     den="populacao"),
    "share_va_agro": V("IBGE", "razao", "Participação da agropecuária no VA", "0–1",
                       num="va_agropecuaria_real", den="va_real"),
    "va_real": V("IBGE PIB dos Municípios", "soma", "Valor adicionado total", "R$ de 2023"),
    # RAIS
    **{f"vinculos_{s}": V("RAIS", "soma", f"Vínculos formais ativos em 31/12 — {d}", "nº")
       for s, d in [("total", "total"), ("agro", "agropecuária"), ("nao_agro", "demais setores"),
                    ("ignorado", "setor ignorado")]},
    **{f"massa_salarial_real_{s}": V("RAIS", "soma",
                                     f"Massa salarial anual (12 × remuneração média) — {d}",
                                     "R$ de 2023")
       for s, d in [("total", "total"), ("agro", "agropecuária"), ("nao_agro", "demais")]},
    **{f"salario_medio_real_{s}": V("RAIS", "razao", f"Salário médio mensal — {d} (1999+)",
                                    "R$ de 2023", num=f"massa_salarial_real_{s}",
                                    den=f"vinculos_{s}", mult=1 / 12)
       for s, d in [("total", "total"), ("agro", "agropecuária"), ("nao_agro", "demais")]},
    **{f"salario_medio_sm_{s}": V("RAIS", "media_pond", f"Salário médio — {d}",
                                  "salários mínimos", peso=f"vinculos_{s}")
       for s, d in [("total", "total"), ("agro", "agropecuária"), ("nao_agro", "demais")]},
    "share_vinculos_agro": V("RAIS", "razao", "Participação da agropecuária nos vínculos",
                             "0–1", num="vinculos_agro", den="vinculos_total"),
    "vinculos_pc": V("RAIS + população", "razao", "Vínculos formais por habitante", "nº/hab.",
                     num="vinculos_total", den="populacao"),
    "vinculos_nao_agro_mil_hab": V("RAIS + população", "razao",
                                   "Vínculos formais não agro por mil habitantes",
                                   "nº/mil hab.", num="vinculos_nao_agro", den="populacao",
                                   mult=1000),
    # domicílios (Censos 2010 e 2022, SIDRA)
    "n_domicilios_censo": V("Censo (SIDRA 3216, 6326)", "soma",
                            "Domicílios particulares permanentes (2010, 2022)", "nº"),
    "n_apartamentos": V("Censo (SIDRA 3216, 6326)", "soma",
                        "Domicílios particulares permanentes do tipo apartamento", "nº"),
    "pct_apartamentos": V("Censo (SIDRA 3216, 6326)", "razao",
                          "Participação dos apartamentos nos domicílios", "0–1",
                          num="n_apartamentos", den="n_domicilios_censo"),
    # saúde
    "nascidos_vivos": V("SINASC", "soma", "Nascidos vivos (residência da mãe)", "nº"),
    "obitos_menor_1": V("SIM", "soma", "Óbitos de menores de 1 ano (residência)", "nº"),
    "tmi": V("SIM/SINASC", "razao", "Taxa de mortalidade infantil", "por 1.000 nascidos vivos",
             num="obitos_menor_1", den="nascidos_vivos", mult=1000),
    "nv_prenatal_7mais": V("SINASC", "soma", "Nascidos vivos com 7+ consultas de pré-natal",
                           "nº"),
    "nv_prenatal_informado": V("SINASC", "soma", "Nascidos vivos com nº de consultas informado",
                               "nº"),
    "pct_prenatal_7mais": V("SINASC", "razao", "Proporção com 7+ consultas de pré-natal", "0–1",
                            num="nv_prenatal_7mais", den="nv_prenatal_informado"),
    "nv_prenatal_adequado_k": V("SINASC", "soma",
                                "Nascidos vivos com pré-natal adequado ou mais (Kotelchuck)",
                                "nº"),
    "nv_prenatal_class": V("SINASC", "soma", "Nascidos vivos com pré-natal classificado", "nº"),
    "pct_prenatal_adequado_kotelchuck": V("SINASC", "razao",
                                          "Proporção com pré-natal adequado ou mais (Kotelchuck,"
                                          " 2014+)", "0–1", num="nv_prenatal_adequado_k",
                                          den="nv_prenatal_class"),
    # educação
    "ideb_iniciais": V("INEP (BD + planilhas para 2015)", "media_pop",
                       "IDEB, anos iniciais, rede pública", "0–10"),
    "ideb_finais": V("INEP (BD + planilhas para 2015)", "media_pop",
                     "IDEB, anos finais, rede pública", "0–10"),
    "nota_saeb_media_padronizada_iniciais": V("INEP", "media_pop",
                                              "Nota SAEB padronizada, anos iniciais", "0–10"),
    "nota_saeb_media_padronizada_finais": V("INEP", "media_pop",
                                            "Nota SAEB padronizada, anos finais", "0–10"),
    **{f"matriculas_{k}": V("INEP Sinopse", "soma", f"Matrículas — {d}", "nº")
       for k, d in [("creche", "creche"), ("pre_escola", "pré-escola"),
                    ("fund_iniciais", "fundamental anos iniciais"),
                    ("fund_finais", "fundamental anos finais"), ("medio", "ensino médio regular"),
                    ("eja", "EJA"), ("profissional", "educação profissional"),
                    ("basica_total", "educação básica, total")]},
    # transferências
    "familias_media_mensal": V("CGU (BF, Auxílio Brasil, Novo BF)", "soma",
                               "Famílias beneficiárias, média mensal no ano", "nº"),
    "familias_dezembro": V("CGU", "soma", "Famílias beneficiárias em dezembro", "nº"),
    "valor_transferencias_real": V("CGU", "soma", "Valor total pago no ano", "R$ de 2023"),
    "familias_por_mil_hab": V("CGU + população", "razao",
                              "Famílias beneficiárias (média mensal) por 1.000 habitantes", "",
                              num="familias_media_mensal", den="populacao", mult=1000),
    # instrumento (atributos do território + preço)
    "yl_alto_media": V("FAO-GAEZ v4", "media_area",
                       "Rendimento atingível de soja, sequeiro, alto insumo (1981–2010)",
                       "kg/ha"),
    "yl_baixo_media": V("FAO-GAEZ v4", "media_area",
                        "Rendimento atingível de soja, sequeiro, baixo insumo (1981–2010)",
                        "kg/ha"),
    "yl_alto_frac_acima": V("FAO-GAEZ v4", "media_area",
                            "Fração da área com rendimento (alto insumo) >= 2.000 kg/ha", "0–1"),
    "apt_alto_media": V("FAO-GAEZ v4", "media_area", "Índice de aptidão (alto insumo)", "0–1"),
    "preco_soja_real_usd2010": V("World Bank Pink Sheet", "max",
                                 "Preço internacional da soja", "US$ de 2010/t"),
}

DERIVADAS = {
    "ganho_tecnologico": ("Ganho tecnológico: (rendimento alto − baixo insumo)", "t/ha"),
    "z_bcp_pos": ("Instrumento principal: ganho tecnológico × (ano >= 2003)", "t/ha"),
    "z_bcp_tend": ("Instrumento alternativo: ganho tecnológico × décadas desde 1985", "t/ha"),
    "z_yl_alto_l1": ("Instrumento do CLAUDE.md: potencial alto (t/ha) × log preço real t-1", ""),
    "z_yl_alto": ("Potencial alto (t/ha) × log preço real t", ""),
    "log_preco_real": ("log do preço real da soja", ""),
    "log_preco_real_l1": ("log do preço real da soja, defasado 1 ano", ""),
    "flag_tmi_instavel": ("Nascidos vivos < 50 (taxa instável)", ""),
    "dado_preliminar_saude": ("Ano com SIM/SINASC preliminar", ""),
    "intensidade_{v}": ("Intensidade: {v}(último ano) − {v}(2000)", "0–1"),
    "ano_trat_{v}_{x}": ("Primeiro ano em que {v} >= {xp} (NaN = nunca tratado)", "ano"),
    "trat_{v}_{x}": ("1 a partir de ano_trat_{v}_{x}", "0/1"),
    "ja_tratado_inicio_{v}_{x}": ("{v} >= {xp} já em 1985 (sem pré-período)", "0/1"),
}

ID_COLS = ["id_municipio", "nome", "sigla_uf", "id_microrregiao", "nome_microrregiao",
           "id_regiao_imediata", "id_amc", "grupo", "matopiba"]


# ---------------------------------------------------------------- leitura

def _ler(nome: str, cols: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(path("interim") / f"{nome}.parquet", columns=cols)


def painel_municipio(universo: pd.DataFrame) -> pd.DataFrame:
    idx = pd.MultiIndex.from_product([universo["id_municipio"], ANOS],
                                     names=["id_municipio", "ano"]).to_frame(index=False)
    p = idx.merge(universo, on="id_municipio")
    mb = _ler("mapbiomas_mun_ano")
    p = p.merge(mb[[c for c in mb.columns if c in VARS or c in ("id_municipio", "ano")]],
                how="left")
    lz = _ler("luzes_mun_ano")
    p = p.merge(lz[[c for c in lz.columns if c in VARS or c in ("id_municipio", "ano")]],
                how="left")
    cons = _ler("construido_mun_ano", ["id_municipio", "ano", "area_urbana_mb_ha",
                                       "area_construida_ha", "n_edificacoes"])
    p = p.merge(cons, how="left")
    urb = _ler("urbano_mun_ano")
    p = p.merge(urb[[c for c in urb.columns if c in VARS or c in ("id_municipio", "ano")]],
                how="left")
    for b in ["socio_populacao", "socio_pib", "socio_rais", "socio_educacao",
              "socio_domicilios"]:
        d = _ler(b)
        p = p.merge(d[[c for c in d.columns if c in VARS or c in ("id_municipio", "ano")]],
                    on=["id_municipio", "ano"], how="left")
    s = _ler("socio_saude").rename(columns={"dado_preliminar": "dado_preliminar_saude"})
    p = p.merge(s[[c for c in s.columns if c in VARS or c in
                   ("id_municipio", "ano", "dado_preliminar_saude")]], how="left")
    t = _ler("socio_transferencias").rename(columns={"valor_total_real":
                                                     "valor_transferencias_real"})
    # anos parciais (menos de 12 meses) não entram no painel anual
    t = t[t["meses"] == 12]
    p = p.merge(t[["id_municipio", "ano", "familias_media_mensal", "familias_dezembro",
                   "valor_transferencias_real"]], how="left")
    inst = _ler("instrumento")
    terr = inst.drop_duplicates("id_municipio")[
        ["id_municipio"] + [c for c in inst.columns if c.startswith(("yl_", "apt_"))
                            and c in VARS]]
    preco = inst.drop_duplicates("ano")[["ano", "preco_soja_real_usd2010"]]
    p = p.merge(terr, how="left").merge(preco, how="left")
    return p


# ---------------------------------------------------------------- agregação

def agregar(p: pd.DataFrame, chave: str, extras: list[str]) -> pd.DataFrame:
    """Agrega o painel municipal para `chave` (ex.: id_amc) seguindo as regras de VARS."""
    cols = [c for c in p.columns if c in VARS]
    g = p.groupby([chave, "ano"])
    out = g[[c for c in cols if VARS[c].agregacao == "soma"]].sum(min_count=1)
    for c in [c for c in cols if VARS[c].agregacao == "max"]:
        out[c] = g[c].max()
    pesos = {"media_pop": "populacao", "media_area": "area_ha"}
    for c in [c for c in cols if VARS[c].agregacao in ("media_pop", "media_area", "media_pond")]:
        w = VARS[c].peso or pesos[VARS[c].agregacao]
        ok = p[c].notna() & p[w].notna()
        num = (p[c] * p[w]).where(ok).groupby([p[chave], p["ano"]]).sum(min_count=1)
        den = p[w].where(ok).groupby([p[chave], p["ano"]]).sum(min_count=1)
        out[c] = num / den
    for c in extras:
        out[c] = g[c].first()
    out = out.reset_index()
    return razoes(out)


def razoes(p: pd.DataFrame) -> pd.DataFrame:
    for c, v in VARS.items():
        if v.agregacao == "razao" and v.num in p and v.den in p:
            den = p[v.den].where(p[v.den] > 0)
            p[c] = p[v.num] / den * v.mult
    if "nascidos_vivos" in p:
        p["flag_tmi_instavel"] = p["nascidos_vivos"] < settings()["socio"]["tmi_nv_min"]
    return p


# ---------------------------------------------------------------- tratamentos e instrumento

def tratamentos(p: pd.DataFrame, chave: str) -> pd.DataFrame:
    p = p.sort_values([chave, "ano"])
    a0, a1 = ANOS[0], ANOS[-1]
    for v in TRAT["variaveis"]:
        for x in [TRAT["limiar_padrao"], *TRAT["limiares_sensibilidade"]]:
            suf = f"{v.replace('share_', '')}_{int(round(x * 100)):02d}"
            acima = p[v] >= x
            primeiro = p["ano"].where(acima).groupby(p[chave]).transform("min")
            p[f"ano_trat_{suf}"] = primeiro
            p[f"trat_{suf}"] = (p["ano"] >= primeiro).astype("Int8").where(p[v].notna())
            p[f"ja_tratado_inicio_{suf}"] = (primeiro == a0)
        base = p[v].where(p["ano"] == TRAT["intensidade_ano_base"]).groupby(p[chave]).transform("max")
        fim = p[v].where(p["ano"] == a1).groupby(p[chave]).transform("max")
        p[f"intensidade_{v.replace('share_', '')}"] = fim - base
    return p


def instrumentos(p: pd.DataFrame) -> pd.DataFrame:
    p["ganho_tecnologico"] = (p["yl_alto_media"] - p["yl_baixo_media"]) / 1000
    p["z_bcp_pos"] = p["ganho_tecnologico"] * (p["ano"] >= INST["bcp"]["ano_pos"])
    p["z_bcp_tend"] = p["ganho_tecnologico"] * (p["ano"] - ANOS[0]) / 10
    lp = np.log(p["preco_soja_real_usd2010"])
    lp_l1 = p["ano"].map(dict(zip(p["ano"] + 1, lp, strict=True)))
    p["log_preco_real"] = lp
    p["log_preco_real_l1"] = lp_l1
    p["z_yl_alto"] = p["yl_alto_media"] / 1000 * lp
    p["z_yl_alto_l1"] = p["yl_alto_media"] / 1000 * lp_l1
    return p


# ---------------------------------------------------------------- painel censitário

CENSO_VARS = {
    # variável: (bloco, regra)  — regra: media_pop exata para proporções da população
    "idhm": ("socio_atlas", "media_pop"), "idhm_e": ("socio_atlas", "media_pop"),
    "idhm_l": ("socio_atlas", "media_pop"), "idhm_r": ("socio_atlas", "media_pop"),
    "indice_gini": ("socio_atlas", "media_pop"), "indice_theil": ("socio_atlas", "media_pop"),
    "prop_pobreza": ("socio_atlas", "media_pop"),
    "prop_pobreza_extrema": ("socio_atlas", "media_pop"),
    "prop_vulner_pobreza": ("socio_atlas", "media_pop"), "renda_pc": ("socio_atlas", "media_pop"),
    "expectativa_vida": ("socio_atlas", "media_pop"),
    "mortalidade_1": ("socio_atlas", "media_pop"),
    "taxa_analfabetismo_15_mais": ("socio_atlas", "media_pop"),
    "expectativa_anos_estudo": ("socio_atlas", "media_pop"),
    "pct_nao_natural_municipio": ("socio_migracao", "media_pop"),
    "pct_nao_natural_uf": ("socio_migracao", "media_pop"),
    "taxa_alfabetizacao": ("socio_censo2022", "media_pop"),
    "pct_esgoto_adequado": ("socio_censo2022", "media_pop"),
    "pct_agua_rede_geral": ("socio_censo2022", "media_pop"),
    "pct_lixo_coletado": ("socio_censo2022", "media_pop"),
    "renda_dom_pc_media": ("socio_censo2022", "media_pop"),
    "renda_dom_pc_mediana": ("socio_censo2022", "media_pop"),
}

CENSO_DESC = {
    "idhm": "IDHM (Atlas Brasil)", "idhm_e": "IDHM Educação", "idhm_l": "IDHM Longevidade",
    "idhm_r": "IDHM Renda", "indice_gini": "Índice de Gini da renda (Atlas)",
    "indice_theil": "Índice de Theil-L (Atlas)", "prop_pobreza": "% de pobres (Atlas)",
    "prop_pobreza_extrema": "% de extremamente pobres (Atlas)",
    "prop_vulner_pobreza": "% de vulneráveis à pobreza (Atlas)",
    "renda_pc": "Renda per capita (Atlas, R$ de ago/2010)",
    "expectativa_vida": "Esperança de vida ao nascer (Atlas)",
    "mortalidade_1": "Mortalidade até 1 ano (Atlas, por mil)",
    "taxa_analfabetismo_15_mais": "Taxa de analfabetismo, 15 anos ou mais (Atlas)",
    "expectativa_anos_estudo": "Expectativa de anos de estudo (Atlas)",
    "pct_nao_natural_municipio": "% de não naturais do município (Censo, ponderado)",
    "pct_nao_natural_uf": "% de não naturais da UF (Censo 2010)",
    "taxa_alfabetizacao": "Taxa de alfabetização, 15+ (Censo 2022)",
    "pct_esgoto_adequado": "% moradores com esgoto por rede ou fossa séptica (Censo 2022)",
    "pct_agua_rede_geral": "% moradores com água da rede geral como forma principal (2022)",
    "pct_lixo_coletado": "% moradores com lixo coletado (Censo 2022)",
    "renda_dom_pc_media": "Rendimento domiciliar per capita médio (Censo 2022, R$ de 2022)",
    "renda_dom_pc_mediana": "Rendimento domiciliar per capita mediano (Censo 2022; média "
                            "ponderada das medianas na AMC — aproximação)",
    "n_estabelecimentos": "Estabelecimentos agropecuários (Censo Agro)",
    "area_estabelecimentos_ha": "Área dos estabelecimentos (Censo Agro, ha)",
    "gini_terra": "Gini da terra (Censo Agro; na AMC, média ponderada pelo nº de "
                  "estabelecimentos — aproximação)",
    "share_estab_menos_10ha": "% de estabelecimentos com menos de 10 ha",
    "share_area_1000ha_mais": "% da área em estabelecimentos de 1.000 ha ou mais",
    "share_area_imputada": "% da área do Censo Agro imputada (sigilo)",
    "tipo_censo": "demografico | agropecuario",
}


def painel_censos(universo: pd.DataFrame, amc: pd.DataFrame) -> pd.DataFrame:
    anos = TRAT.get("anos_censo", [1991, 2000, 2010, 2022])
    pop = _ler("socio_populacao")
    c22 = _ler("socio_censo2022")
    pop = pd.concat([pop[pop["ano"] != 2022],
                     c22[["id_municipio", "populacao"]].assign(ano=2022)], ignore_index=True)
    base = pd.MultiIndex.from_product([universo["id_municipio"], anos],
                                      names=["id_municipio", "ano"]).to_frame(index=False)
    d = base.merge(universo[["id_municipio", "id_amc"]]).merge(pop, how="left")
    for bloco in sorted({b for b, _ in CENSO_VARS.values()}):
        x = _ler(bloco)
        cols = [c for c, (b, _) in CENSO_VARS.items() if b == bloco]
        d = d.merge(x[["id_municipio", "ano", *cols]], on=["id_municipio", "ano"], how="left")
    g = d.groupby(["id_amc", "ano"])
    out = g[["populacao"]].sum(min_count=1)
    for c in CENSO_VARS:
        ok = d[c].notna() & d["populacao"].notna()
        num = (d[c] * d["populacao"]).where(ok).groupby([d["id_amc"], d["ano"]]).sum(min_count=1)
        out[c] = num / d["populacao"].where(ok).groupby([d["id_amc"], d["ano"]]).sum(min_count=1)
    out = out.reset_index().assign(tipo_censo="demografico")
    # uso da terra, luzes e instrumento nos anos censitários (do painel AMC)
    cols_amc = ["id_amc", "ano", "area_ha", "share_soja", "share_agri_temp", "share_pasto",
                "share_nativa", "luz_pc", "pib_pc_real", "ganho_tecnologico", "z_bcp_pos",
                "z_bcp_tend"]
    out = out.merge(amc[[c for c in cols_amc if c in amc.columns]], on=["id_amc", "ano"],
                    how="left")
    # Censo Agropecuário (2006, 2017) como linhas próprias
    f = _ler("socio_fundiaria").merge(universo[["id_municipio", "id_amc"]])
    f["area_1000"] = f["share_area_1000ha_mais"] * f["area_estabelecimentos_ha"]
    f["n_10"] = f["share_estab_menos_10ha"] * f["n_estabelecimentos"]
    f["area_imp"] = f["share_area_imputada"] * f["area_estabelecimentos_ha"]
    f["gini_x_n"] = f["gini_terra"] * f["n_estabelecimentos"]
    fa = f.groupby(["id_amc", "ano"])[["n_estabelecimentos", "area_estabelecimentos_ha",
                                       "area_1000", "n_10", "area_imp", "gini_x_n"]].sum(
        min_count=1).reset_index()
    fa["gini_terra"] = fa["gini_x_n"] / fa["n_estabelecimentos"]
    fa["share_area_1000ha_mais"] = fa["area_1000"] / fa["area_estabelecimentos_ha"]
    fa["share_estab_menos_10ha"] = fa["n_10"] / fa["n_estabelecimentos"]
    fa["share_area_imputada"] = fa["area_imp"] / fa["area_estabelecimentos_ha"]
    fa = fa.drop(columns=["area_1000", "n_10", "area_imp", "gini_x_n"]).assign(
        tipo_censo="agropecuario")
    fa = fa.merge(amc[[c for c in cols_amc if c in amc.columns]], on=["id_amc", "ano"],
                  how="left")
    return pd.concat([out, fa], ignore_index=True).sort_values(["id_amc", "ano"])


# ---------------------------------------------------------------- dicionário

def dicionario(paineis: dict[str, pd.DataFrame]) -> str:
    linhas = ["# Dicionário de variáveis", "",
              "Gerado por `src/matopiba/s07_paineis.py` a partir da tabela `VARS`. Valores "
              "monetários em R$ constantes de 2023 (IPCA médio anual), exceto onde indicado.",
              "Agregação para AMC: `soma`; `razao` (recalculada a partir dos componentes "
              "agregados); `media_pop` / `media_area` / `media_pond` (médias ponderadas); `max` "
              "(flags).", ""]
    for nome, df in paineis.items():
        linhas += [f"## {nome}", "", f"{len(df):,} linhas × {df.shape[1]} colunas. Chave: "
                   + ("`id_municipio`, `ano`" if "municipio" in nome else "`id_amc`, `ano`"), "",
                   "| variável | descrição | unidade | fonte | agregação AMC |",
                   "|---|---|---|---|---|"]
        for c in df.columns:
            if c in VARS:
                v = VARS[c]
                ag = v.agregacao + (f" ({v.num} / {v.den})" if v.agregacao == "razao" else "")
                ag += f" (peso {v.peso})" if v.peso else ""
                linhas.append(f"| `{c}` | {v.descricao} | {v.unidade} | {v.fonte} | {ag} |")
            elif c in CENSO_DESC:
                linhas.append(f"| `{c}` | {CENSO_DESC[c]} | | | media_pop |")
            else:
                linhas.append(f"| `{c}` | {_desc_derivada(c)} | | | |")
        linhas.append("")
    return "\n".join(linhas)


def _desc_derivada(c: str) -> str:
    fixos = {"id_municipio": "Código IBGE do município (7 dígitos)", "ano": "Ano",
             "id_amc": "Área mínima comparável (Ehrl 2017 estendida, ver DECISOES.md)",
             "nome": "Nome do município", "sigla_uf": "UF", "id_microrregiao": "Microrregião IBGE",
             "nome_microrregiao": "Nome da microrregião", "id_regiao_imediata": "Região imediata",
             "nome_regiao_imediata": "Nome da região imediata",
             "grupo": "matopiba | cerrado_fora | outros (na AMC: grupo de maior área)",
             "matopiba": "Município do Matopiba (Portaria MAPA 244/2015)",
             "n_municipios": "Nº de municípios na AMC",
             "share_matopiba": "Fração da área da AMC no Matopiba"}
    if c in fixos:
        return fixos[c]
    for k, (d, _u) in DERIVADAS.items():
        if "{" not in k and c == k:
            return d
    for pref in ["ano_trat_", "trat_", "ja_tratado_inicio_", "intensidade_"]:
        if c.startswith(pref):
            resto = c[len(pref):]
            if pref == "intensidade_":
                return f"Intensidade: share_{resto}(último ano) − share_{resto}(2000)"
            v, x = resto.rsplit("_", 1)
            txt = {"ano_trat_": f"Primeiro ano em que share_{v} >= {int(x)}% (NaN = nunca)",
                   "trat_": f"1 a partir do primeiro ano em que share_{v} >= {int(x)}%",
                   "ja_tratado_inicio_": f"share_{v} >= {int(x)}% já em {ANOS[0]}"}
            return txt[pref]
    return "—"


# ---------------------------------------------------------------- main

def main() -> int:
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    mun = painel_municipio(universo)
    mun = razoes(mun)
    mun = instrumentos(mun)
    mun = tratamentos(mun, "id_municipio")
    mun.to_parquet(path("processed") / "painel_municipio.parquet", index=False)

    # AMC: grupo da AMC = grupo com maior área; fração no Matopiba
    gp = (universo.groupby(["id_amc", "grupo"])["area_ha"].sum().reset_index()
          .sort_values("area_ha").drop_duplicates("id_amc", keep="last")
          .set_index("id_amc")["grupo"])
    amc = agregar(mun, "id_amc", extras=[])
    amc["grupo"] = amc["id_amc"].map(gp)
    am = universo.assign(a=universo["area_ha"] * universo["matopiba"]).groupby("id_amc")
    amc["share_matopiba"] = amc["id_amc"].map(am["a"].sum() / am["area_ha"].sum())
    amc["n_municipios"] = amc["id_amc"].map(universo.groupby("id_amc").size())
    amc["sigla_uf"] = amc["id_amc"].map(universo.groupby("id_amc")["sigla_uf"].first())
    amc["id_microrregiao"] = amc["id_amc"].map(
        universo.groupby("id_amc")["id_microrregiao"].first())
    amc = instrumentos(amc)
    amc = tratamentos(amc, "id_amc")
    amc.to_parquet(path("processed") / "painel_amc.parquet", index=False)

    cen = painel_censos(universo, amc)
    cen.to_parquet(path("processed") / "painel_censos.parquet", index=False)

    texto = dicionario({"painel_municipio": mun, "painel_amc": amc, "painel_censos": cen})
    (ROOT / "docs" / "DICIONARIO.md").write_text(texto, encoding="utf-8")
    for nome, df in [("painel_municipio", mun), ("painel_amc", amc), ("painel_censos", cen)]:
        print(f"{nome}: {len(df):,} linhas × {df.shape[1]} colunas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
