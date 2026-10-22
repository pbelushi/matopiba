"""Etapa 8.6d: edificações urbanas (Open Buildings, 4 m, máscara urbana de 2012), 2016→2023.

Com o Open Buildings só em 2016 e 2023 e apenas 23 tratados com pré-períodos dentro da série
(coortes 2019–2022), a especificação é em diferenças longas entre as pontas, por município
(Matopiba e Cerrado fora):

  2SLS       Δy contra Δ participação da soja, instrumentada pelo ganho tecnológico GAEZ ×
             duração do período (como em s08_censos)
  OLS        Δy contra Δ participação da agricultura temporária (tratamento contínuo)
  DiD 2×2    Δy de quem cruza o limiar de 10% entre 2017 e 2023 contra os nunca tratados
             até 2023 (exclui os já tratados em 2016); sem teste de pré-tendência possível

Cada especificação sem e com o nível inicial do desfecho como controle. EF de UF; cluster por
microrregião.

Saídas:
  outputs/tabelas/s08_edificacoes.{csv,tex}

Uso: python -m matopiba.s08_edificacoes
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from matopiba.analise import CFG, amostra_did, carregar, estrelas, iv_fe, salvar_tabela
from matopiba.config import settings

A0, A1 = settings()["urbano"]["ob"]["anos_calculo"]
DESF = {"log_n": ("n_edificacoes_urb", True, "log nº de edificações (máscara urbana)"),
        "log_area": ("area_construida_urb_ha", True, "log área construída (máscara urbana)"),
        "altura": ("altura_media_urb_m", False, "altura média, m (máscara urbana)")}


def base() -> pd.DataFrame:
    p = carregar()
    p = p[p["grupo"].isin(CFG["grupos"]) & p["ano"].isin([A0, A1])].copy()
    for k, (col, log, _) in DESF.items():
        v = p[col].astype(float)
        p[k] = np.log(v.where(v > 0)) if log else v
    cols = [*DESF, "share_soja", "share_agri_temp"]
    w = p.pivot_table(index="unidade", columns="ano", values=cols)
    d = pd.DataFrame({f"d_{c}": w[(c, A1)] - w[(c, A0)] for c in cols})
    for k in DESF:
        d[f"ini_{k}"] = w[(k, A0)]
    info = p.drop_duplicates("unidade").set_index("unidade")[
        ["sigla_uf", "cluster", "ganho_tecnologico"]]
    d = d.join(info)
    d["d_z"] = d["ganho_tecnologico"] * (A1 - A0) / 10
    # DiD 2×2: coorte do limiar padrão
    s = amostra_did(carregar()).drop_duplicates("unidade").set_index("unidade")
    d["coorte"] = s["coorte"]
    d["amostra_2x2"] = d.index.isin(s.index) & ~(d["coorte"] <= A0)
    d["D"] = d["coorte"].between(A0 + 1, A1).astype(float)
    return d.reset_index()


def estimar(d: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for k, (_, _, rot) in DESF.items():
        for ctrl in [False, True]:
            cont = [f"ini_{k}"] if ctrl else None
            extra = f" + ini_{k}" if ctrl else ""
            r = iv_fe(d, f"d_{k}", "d_share_soja", "d_z", fe=["sigla_uf"], controles=cont)
            s = d.dropna(subset=[f"d_{k}", "d_share_agri_temp", f"ini_{k}"])
            o = smf.ols(f"d_{k} ~ d_share_agri_temp + C(sigla_uf){extra}", data=s).fit(
                cov_type="cluster", cov_kwds={"groups": s["cluster"]})
            s2 = d[d["amostra_2x2"]].dropna(subset=[f"d_{k}", f"ini_{k}"])
            dd = smf.ols(f"d_{k} ~ D + C(sigla_uf){extra}", data=s2).fit(
                cov_type="cluster", cov_kwds={"groups": s2["cluster"]})
            linhas.append({
                "desfecho": rot, "controle nível inicial": "sim" if ctrl else "não",
                "2SLS (Δ soja)": r["iv_coef"], "2SLS ep": r["iv_ep"], "2SLS p": r["iv_p"],
                "AR 95% inf": r["ar_ic_inf"], "AR 95% sup": r["ar_ic_sup"],
                "F efetivo": r["F_efetivo"], "forma reduzida": r["rf_coef"], "FR ep": r["rf_ep"],
                "OLS (Δ agri. temp.)": o.params["d_share_agri_temp"],
                "OLS ep": o.bse["d_share_agri_temp"], "OLS p": o.pvalues["d_share_agri_temp"],
                "DiD 2×2": dd.params["D"], "DiD ep": dd.bse["D"], "DiD p": dd.pvalues["D"],
                "tratados 2×2": int(s2["D"].sum()), "controles 2×2": int((s2["D"] == 0).sum()),
                "n municípios": r["n"], "clusters": r["n_clusters"]})
            print(f"  {k} ctrl={ctrl}: 2SLS {r['iv_coef']:.3f}{estrelas(r['iv_p'])} "
                  f"(F {r['F_efetivo']:.1f}) | OLS {o.params['d_share_agri_temp']:.3f}"
                  f"{estrelas(o.pvalues['d_share_agri_temp'])} | DiD {dd.params['D']:.3f}"
                  f"{estrelas(dd.pvalues['D'])} ({int(s2['D'].sum())} tratados)", flush=True)
    return pd.DataFrame(linhas)


def main() -> int:
    t = estimar(base())
    salvar_tabela(t, "s08_edificacoes",
                  f"Edificações na máscara urbana de 2012 (Open Buildings, 4 m), diferenças "
                  f"longas {A0}–{A1} por município: 2SLS (soja instrumentada pelo ganho "
                  f"tecnológico GAEZ), OLS (agricultura temporária) e DiD 2×2; EF de UF; "
                  f"cluster por microrregião", casas=3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
