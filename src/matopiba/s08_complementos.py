"""Etapa 8.6e: testes complementares do DiD (Callaway–Sant'Anna), com os dados dos painéis.

1. Concentração versus perda líquida: área urbana e luzes urbanas per capita por microrregião
   (agregando só os municípios de Matopiba e Cerrado fora, onde há luz urbana), contra o nível
   municipal. Se o efeito negativo municipal sumir na microrregião, a urbanização foi
   realocada para cidades vizinhas; se persistir, é perda líquida. Área urbana também na
   janela 2000–2025 (MapBiomas mais estável).
2. Luzes fora da máscara urbana sem 2013 (primeiro ano do VIIRS anual).
3. CS condicional (duplamente robusto, Sant'Anna e Zhao 2020) com covariáveis de 2000, contra o
   incondicional na mesma amostra (coortes > 2000, para as covariáveis serem pré-tratamento).
   A participação agrícola de 2000 fica fora da especificação principal (quase separa
   tratados e controles) e entra como sensibilidade para PIB e luzes; a tabela traz o N
   efetivo dos controles com os pesos do escore de propensão.
4. PIB per capita com antecipação de 2 anos (base g-3), incondicional e condicional.
5. Vínculos não agro: log per capita (como em s08_heterogeneidade) contra nível (nº de
   vínculos e vínculos por mil habitantes) e log do nº sem dividir pela população.

Cada linha traz o ATT agregado, o teste de Wald dos pré-coeficientes (base universal,
e = -5…-2) e a inclinação da pré-tendência.

Saídas:
  outputs/tabelas/s08_complementos.{csv,tex}
  outputs/figuras/s08_complementos_eventos.png

Uso: python -m matopiba.s08_complementos
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matopiba.analise import (CFG, DESFECHOS, amostra_did, carregar, cs_did, desfecho,
                              estrelas, preparar_desfecho, salvar_tabela)
from matopiba.config import path
from matopiba.s07_paineis import agregar, tratamentos
from matopiba.s08_honestdid import pre_tendencia

C = CFG["complementos"]
AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#8a897f", "#1c1c1a", "#5f5e5a", "#e4e3df"


def microrregiao(p: pd.DataFrame) -> pd.DataFrame:
    """Painel de microrregiões com os municípios dos grupos de análise."""
    m = agregar(p[p["grupo"].isin(CFG["grupos"])], "id_microrregiao", extras=[])
    univ = pd.read_parquet(path("processed") / "universo.parquet")
    univ = univ[univ["grupo"].isin(CFG["grupos"])]
    g = (univ.groupby(["id_microrregiao", "grupo"])["area_ha"].sum().reset_index()
         .sort_values("area_ha").drop_duplicates("id_microrregiao", keep="last")
         .set_index("id_microrregiao")["grupo"])
    m["grupo"] = m["id_microrregiao"].map(g)
    m = tratamentos(m, "id_microrregiao")
    m["unidade"] = m["id_microrregiao"]
    m["cluster"] = m["id_microrregiao"].astype(str)
    return m


def covariaveis_2000(p: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    a = pd.read_parquet(path("interim") / "socio_atlas.parquet").query("ano == 2000")
    mig = pd.read_parquet(path("interim") / "socio_migracao.parquet").query("ano == 2000")
    x = p[p["ano"] == 2000].set_index("id_municipio")
    cov = pd.DataFrame({
        "log_pop_2000": np.log(x["populacao"].astype(float)),
        "share_agri_temp_2000": x["share_agri_temp"].astype(float),
        "share_nativa_2000": x["share_nativa"].astype(float),
    })
    cov["log_renda_pc_2000"] = np.log(a.set_index("id_municipio")["renda_pc"].astype(float))
    cov["analfabetismo_2000"] = a.set_index("id_municipio")["taxa_analfabetismo_15_mais"]
    cov["pct_nao_natural_2000"] = mig.set_index("id_municipio")["pct_nao_natural_municipio"]
    return cov[cols].astype(float)


def sobreposicao(s: pd.DataFrame, cov: pd.DataFrame) -> dict:
    """Logit agrupado (tratados vs. nunca tratados): N efetivo dos controles com pesos
    p/(1-p) e maior peso individual como fração do total."""
    import statsmodels.api as sm

    u = s.drop_duplicates("unidade").set_index("unidade")
    c = cov.loc[cov.index.intersection(u.index)].dropna()
    D = u.loc[c.index, "coorte"].notna().astype(float)
    X = sm.add_constant(c)
    ps = sm.Logit(D, X).fit(disp=0).predict(X)
    w = (ps / (1 - ps))[D == 0]
    return {"N efetivo controles": float(w.sum() ** 2 / (w ** 2).sum()),
            "maior peso controle": float(w.max() / w.sum())}


def estimar(s: pd.DataFrame, d, rotulo: str, **kw) -> tuple[dict, pd.DataFrame]:
    x = s.assign(y=preparar_desfecho(s, d)).dropna(subset=["y"])
    x = x[x.groupby("unidade")["ano"].transform("nunique") == x["ano"].nunique()]
    sm = cs_did(x, "y", balancear=False, **kw)
    un = cs_did(x, "y", balancear=False, base="universal", **kw)
    ev, V = un["evento"], un["vcov_evento"]
    pre = [e for e in range(-5, -1) if e in V.index]
    if kw.get("antecipacao"):          # com antecipação δ, a referência é e = -1-δ
        pre = [e for e in range(-5 - kw["antecipacao"], -1 - kw["antecipacao"])
               if e in V.index]
    pt = pre_tendencia(ev.set_index("e").loc[pre, "att"].to_numpy(),
                       V.loc[pre, pre].to_numpy(), pre) if len(pre) > 1 else {}
    r = sm["simples"]
    linha = {"teste": rotulo, "desfecho": d.rotulo, "anos": r.get("anos"),
             "ATT": r.get("att"), "ep": r.get("ep"), "p": r.get("p"),
             "tratados": r.get("n_unidades_tratadas"), "controles": r.get("n_controles"),
             "coortes": r.get("n_coortes"), "células (g,t)": len(sm["gt"]),
             "pré Wald p": pt.get("wald_p"), "pré inclinação": pt.get("inclinacao"),
             "pré inclinação ep": pt.get("inclinacao_ep")}
    print(f"  {rotulo} | {d.nome}: {r.get('att', np.nan):.4f}{estrelas(r.get('p', 1))} "
          f"({r.get('ep', np.nan):.4f}), {r.get('n_unidades_tratadas')} tratados; "
          f"pré Wald p {pt.get('wald_p', np.nan):.3f}", flush=True)
    return linha, ev.assign(teste=rotulo, desfecho=d.nome)


def figura(ev: pd.DataFrame) -> None:
    paineis = [("log_pib_pc", "PIB per capita, antecipação 2 anos (incondicional)",
                "PIB pc: CS, antecipação de 2 anos"),
               ("log_pib_pc", "PIB per capita, antecipação 2 anos (condicional, covariáveis 2000)",
                "PIB pc: antecipação 2 + covariáveis 2000"),
               ("log_luz_fora_sem2013", "luzes fora da máscara, sem 2013",
                "Luzes fora da máscara, 2014–2025")]
    fig, axes = plt.subplots(1, len(paineis), figsize=(15, 4.2))
    for ax, (nome, teste, tit) in zip(axes, paineis, strict=True):
        e = ev[(ev["desfecho"] == nome) & (ev["teste"] == teste) & ev["e"].between(-8, 10)]
        ax.errorbar(e["e"], e["att"], yerr=1.96 * e["ep"], fmt="o", color=AZUL,
                    markersize=3.5, elinewidth=1, capsize=0)
        ref = -3 if "antecipação" in teste else -1
        ax.scatter([ref], [0], color=CINZA, s=14, zorder=3)
        ax.axvline(-0.5, color="#a8a79f", linewidth=0.8, linestyle="--")
        if ref == -3:
            ax.axvspan(-2.5, -0.5, color=GRADE, alpha=0.6, linewidth=0)
        ax.axhline(0, color="#a8a79f", linewidth=0.8)
        ax.set_title(tit, fontsize=10, color=TINTA, loc="left")
        ax.set_xlabel("anos desde o tratamento", fontsize=8, color=TINTA2)
        ax.grid(axis="y", color=GRADE, linewidth=0.6)
        for lado in ["top", "right"]:
            ax.spines[lado].set_visible(False)
        ax.tick_params(colors=TINTA2, labelsize=8)
    fig.text(0.01, -0.03, "CS, base universal; IC 95%, cluster por microrregião. Com antecipação "
             "a referência é e = -3 e a faixa cinza marca os anos de antecipação.",
             fontsize=8, color=TINTA2)
    fig.tight_layout()
    fig.savefig(path("figuras") / "s08_complementos_eventos.png", dpi=200, facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    p = carregar()
    s = amostra_did(p)
    linhas, eventos = [], []

    def roda(amostra, nome, rotulo, **kw):
        lin, ev = estimar(amostra, desfecho(nome), rotulo, **kw)
        linhas.append(lin)
        eventos.append(ev)

    # 1. concentração vs perda líquida
    sm = amostra_did(microrregiao(p))
    for nome in ["log_area_urbana", "log_area_urbana_2000", "log_luz_urbana_pc"]:
        roda(s, nome, "município")
        roda(sm, nome, "microrregião (só municípios dos grupos)")
    # 2. luzes fora da máscara sem 2013
    roda(s, "log_luz_fora", "município")
    roda(s, "log_luz_fora_sem2013", "luzes fora da máscara, sem 2013")
    # 3. CS condicional com covariáveis de 2000 (coortes > 2000 nos dois)
    cov = covariaveis_2000(p, C["covariaveis_2000"])
    cov_s = covariaveis_2000(p, C["covariaveis_2000"] + C["covariaveis_2000_sens"])
    s01 = s[~(s["coorte"] <= 2000)]
    s01 = s01[s01["unidade"].isin(cov_s.dropna().index)]
    sob, sob_s = sobreposicao(s01, cov), sobreposicao(s01, cov_s)
    print(f"  sobreposição: {sob} | com participação agrícola 2000: {sob_s}", flush=True)
    for d in DESFECHOS:
        roda(s01, d.nome, "incondicional (coortes > 2000)")
        roda(s01, d.nome, "condicional, covariáveis 2000 (coortes > 2000)",
             covariaveis=cov)
        linhas[-1].update(sob)
        if d.nome in C["desfechos_sens"]:
            roda(s01, d.nome, "condicional, covariáveis 2000 + participação agrícola 2000",
                 covariaveis=cov_s)
            linhas[-1].update(sob_s)
    # 4. PIB com antecipação
    a = C["antecipacao_pib"]
    roda(s, "log_pib_pc", f"PIB per capita, antecipação {a} anos (incondicional)",
         antecipacao=a)
    roda(s01, "log_pib_pc",
         f"PIB per capita, antecipação {a} anos (condicional, covariáveis 2000)",
         antecipacao=a, covariaveis=cov)

    # 5. vínculos não agro em nível (a queda em log per capita vem do numerador?)
    for nome in ["log_vinc_nao_agro_pc", "vinc_nao_agro", "vinc_nao_agro_mil_hab",
                 "log_vinc_nao_agro"]:
        roda(s, nome, "vínculos não agro: log per capita vs. nível")

    t = pd.DataFrame(linhas)
    salvar_tabela(t, "s08_complementos", "Testes complementares do DiD (Callaway–Sant'Anna): "
                  "microrregião, janelas alternativas, CS condicional e antecipação", casas=4)
    figura(pd.concat(eventos, ignore_index=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
