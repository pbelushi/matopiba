"""Etapa 8.6f: validação da verticalização (altura do Open Buildings) com os Censos.

1. Medida: altura média das edificações na máscara urbana de 2012 (Open Buildings, 4 m; 2016
   e 2023) contra a participação dos apartamentos nos domicílios particulares permanentes
   (Censos 2010 e 2022, SIDRA 3216 e 6326), por município de Matopiba e Cerrado fora:
   correlações de Pearson e Spearman e regressão com EF de UF, em nível (2023 × 2022) e em
   variação (2016→2023 × 2010→2022).
2. Efeito: as diferenças longas de s08_edificacoes (2SLS com a soja instrumentada pelo ganho
   tecnológico GAEZ, OLS com a agricultura temporária e DiD 2×2) aplicadas à participação dos
   apartamentos entre 2010 e 2022. Se a altura capta verticalização, o sinal deve se repetir.

Saídas:
  outputs/tabelas/s08_verticalizacao.{csv,tex}
  outputs/figuras/s08_verticalizacao.png

Uso: python -m matopiba.s08_verticalizacao
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from matopiba.analise import CFG, amostra_did, carregar, estrelas, iv_fe, salvar_tabela
from matopiba.config import path

AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#8a897f", "#1c1c1a", "#5f5e5a", "#e4e3df"


def base() -> pd.DataFrame:
    p = carregar()
    p = p[p["grupo"].isin(CFG["grupos"])]
    w = p.pivot_table(index="unidade", columns="ano",
                      values=["altura_media_urb_m", "pct_apartamentos", "share_soja",
                              "share_agri_temp", "area_construida_urb_ha"])
    d = pd.DataFrame({
        "altura_2016": w[("altura_media_urb_m", 2016)],
        "altura_2023": w[("altura_media_urb_m", 2023)],
        "apto_2010": 100 * w[("pct_apartamentos", 2010)],
        "apto_2022": 100 * w[("pct_apartamentos", 2022)],
        "area_constr_2023": w[("area_construida_urb_ha", 2023)],
        "d_share_soja": w[("share_soja", 2022)] - w[("share_soja", 2010)],
        "d_share_agri_temp": w[("share_agri_temp", 2022)] - w[("share_agri_temp", 2010)],
    })
    d["d_altura"] = d["altura_2023"] - d["altura_2016"]
    d["d_apto"] = d["apto_2022"] - d["apto_2010"]
    info = p.drop_duplicates("unidade").set_index("unidade")[
        ["sigla_uf", "cluster", "ganho_tecnologico"]]
    d = d.join(info)
    d["d_z"] = d["ganho_tecnologico"] * 12 / 10           # 2010→2022, em décadas
    s = amostra_did(carregar()).drop_duplicates("unidade").set_index("unidade")
    d["coorte"] = s["coorte"]
    d["amostra_2x2"] = d.index.isin(s.index) & ~(d["coorte"] <= 2010)
    d["D"] = d["coorte"].between(2011, 2022).astype(float)
    return d.reset_index()


def correlacoes(d: pd.DataFrame) -> list[dict]:
    linhas = []
    for rot, x, y in [("nível: altura 2023 × % apartamentos 2022", "apto_2022", "altura_2023"),
                      ("nível: altura 2016 × % apartamentos 2010", "apto_2010", "altura_2016"),
                      ("variação: Δ altura 2016→2023 × Δ % apartamentos 2010→2022", "d_apto",
                       "d_altura")]:
        s = d.dropna(subset=[x, y])
        r = smf.ols(f"{y} ~ {x} + C(sigla_uf)", data=s).fit(
            cov_type="cluster", cov_kwds={"groups": s["cluster"]})
        linhas.append({"teste": rot, "Pearson": stats.pearsonr(s[x], s[y])[0],
                       "Spearman": stats.spearmanr(s[x], s[y])[0],
                       "coef. (EF UF)": r.params[x], "ep": r.bse[x], "p": r.pvalues[x],
                       "n": len(s)})
        print(f"  {rot}: Pearson {linhas[-1]['Pearson']:.3f}, Spearman "
              f"{linhas[-1]['Spearman']:.3f}, coef {r.params[x]:.4f}{estrelas(r.pvalues[x])} "
              f"(n {len(s)})", flush=True)
    return linhas


def efeito(d: pd.DataFrame) -> list[dict]:
    linhas = []
    d = d.assign(ini_apto=d["apto_2010"])
    for ctrl in [False, True]:
        cont = ["ini_apto"] if ctrl else None
        extra = " + ini_apto" if ctrl else ""
        r = iv_fe(d, "d_apto", "d_share_soja", "d_z", fe=["sigla_uf"], controles=cont)
        s = d.dropna(subset=["d_apto", "d_share_agri_temp", "ini_apto"])
        o = smf.ols(f"d_apto ~ d_share_agri_temp + C(sigla_uf){extra}", data=s).fit(
            cov_type="cluster", cov_kwds={"groups": s["cluster"]})
        s2 = d[d["amostra_2x2"]].dropna(subset=["d_apto", "ini_apto"])
        dd = smf.ols(f"d_apto ~ D + C(sigla_uf){extra}", data=s2).fit(
            cov_type="cluster", cov_kwds={"groups": s2["cluster"]})
        rot = f"efeito sobre Δ % apartamentos 2010→2022 (nível inicial: {'sim' if ctrl else 'não'})"
        linhas.append({"teste": rot, "2SLS (Δ soja)": r["iv_coef"], "2SLS ep": r["iv_ep"],
                       "2SLS p": r["iv_p"], "F efetivo": r["F_efetivo"],
                       "OLS (Δ agri. temp.)": o.params["d_share_agri_temp"],
                       "OLS ep": o.bse["d_share_agri_temp"],
                       "OLS p": o.pvalues["d_share_agri_temp"],
                       "DiD 2×2": dd.params["D"], "DiD ep": dd.bse["D"], "DiD p": dd.pvalues["D"],
                       "tratados 2×2": int(s2["D"].sum()), "n": r["n"]})
        print(f"  {rot}: 2SLS {r['iv_coef']:.2f}{estrelas(r['iv_p'])} (F {r['F_efetivo']:.1f}) | "
              f"OLS {o.params['d_share_agri_temp']:.2f}{estrelas(o.pvalues['d_share_agri_temp'])}"
              f" | DiD {dd.params['D']:.3f}{estrelas(dd.pvalues['D'])} "
              f"({int(s2['D'].sum())} tratados)", flush=True)
    return linhas


def figura(d: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, (x, y, xl, yl) in zip(axes, [
            ("apto_2022", "altura_2023", "% de apartamentos, 2022",
             "altura média na máscara, 2023 (m)"),
            ("d_apto", "d_altura", "Δ % de apartamentos, 2010→2022 (p.p.)",
             "Δ altura média, 2016→2023 (m)")], strict=True):
        s = d.dropna(subset=[x, y])
        ax.scatter(s[x], s[y], s=6, color=CINZA, alpha=0.35, linewidths=0)
        # médias por vintil de x
        b = s.assign(q=pd.qcut(s[x].rank(method="first"), 20, labels=False)).groupby("q")[
            [x, y]].mean()
        ax.plot(b[x], b[y], "o-", color=AZUL, markersize=4, linewidth=1.5,
                label="média por vintil")
        ax.set_xlabel(xl, fontsize=9, color=TINTA2)
        ax.set_ylabel(yl, fontsize=9, color=TINTA2)
        ax.set_title(f"Spearman {stats.spearmanr(s[x], s[y])[0]:.2f} (n = {len(s)})",
                     fontsize=10, color=TINTA, loc="left")
        ax.grid(color=GRADE, linewidth=0.6)
        for lado in ["top", "right"]:
            ax.spines[lado].set_visible(False)
        ax.tick_params(colors=TINTA2, labelsize=8)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Altura das edificações (Open Buildings, máscara urbana de 2012) × "
                 "apartamentos nos Censos — Matopiba e Cerrado fora", x=0.01, ha="left",
                 fontsize=11, color=TINTA)
    fig.tight_layout()
    fig.savefig(path("figuras") / "s08_verticalizacao.png", dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    d = base()
    t = pd.DataFrame(correlacoes(d) + efeito(d))
    salvar_tabela(t, "s08_verticalizacao", "Validação da altura do Open Buildings com a "
                  "participação dos apartamentos (Censos 2010 e 2022), por município", casas=4)
    figura(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
