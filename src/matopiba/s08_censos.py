"""Etapa 8.4: censos em diferenças longas (AMC), Δ desfecho contra Δ área agrícola instrumentada.

Δx = variação da participação da soja na área; Δz = ganho tecnológico GAEZ × duração do
período (décadas). Efeitos fixos de UF (e de período no empilhado); cluster por microrregião.
Períodos:
  2000–2010: IDHM e componentes, Gini, % de pobres, renda per capita, alfabetização (Atlas)
  2010–2022: renda domiciliar per capita (Atlas 2010 deflacionado pelo IPCA ago/2010→jul/2022
             vs. Censo 2022) e alfabetização 15+ (Atlas 2010 vs. Censo 2022)
Também: OLS com Δ agricultura temporária (tratamento contínuo do CLAUDE.md). Cada
especificação é estimada sem e com o nível inicial do desfecho como controle (convergência e
efeito teto), porque o ganho tecnológico é maior onde a renda e a alfabetização já eram altas.

Saídas:
  outputs/tabelas/s08_censos_dif_longas.{csv,tex}

Uso: python -m matopiba.s08_censos
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from matopiba.analise import CFG, estrelas, iv_fe, salvar_tabela
from matopiba.config import path
from matopiba.gcp import bq_query

DESF_2000_2010 = {
    "idhm": "IDHM", "idhm_e": "IDHM Educação", "idhm_l": "IDHM Longevidade",
    "idhm_r": "IDHM Renda", "indice_gini": "Gini da renda", "prop_pobreza": "% de pobres",
    "log_renda": "log renda per capita", "alfabetizacao": "Taxa de alfabetização 15+ (%)",
}
DESF_2010_2022 = {"log_renda": "log renda per capita", "alfabetizacao":
                  "Taxa de alfabetização 15+ (%)"}


def fator_ipca(de: tuple[int, int], para: tuple[int, int]) -> float:
    q = bq_query("SELECT ano, mes, indice FROM `basedosdados.br_ibge_ipca.mes_brasil`", 0.1)
    i = q.set_index(["ano", "mes"])["indice"]
    return float(i.loc[para] / i.loc[de])


def base_censos() -> pd.DataFrame:
    c = pd.read_parquet(path("processed") / "painel_censos.parquet")
    c = c[c["tipo_censo"] == "demografico"].copy()
    amc = pd.read_parquet(path("processed") / "painel_amc.parquet",
                          columns=["id_amc", "ano", "sigla_uf", "id_microrregiao", "grupo"])
    info = amc.drop_duplicates("id_amc")[["id_amc", "sigla_uf", "id_microrregiao", "grupo"]]
    c = c.merge(info, on="id_amc")
    c = c[c["grupo"].isin(CFG["grupos"])]
    f = fator_ipca((2010, 8), (2022, 7))
    renda = np.where(c["ano"] == 2022, c["renda_dom_pc_media"],
                     c["renda_pc"] * np.where(c["ano"] == 2010, f, np.nan))
    # para 2000–2010 basta a renda do Atlas (mesma base monetária)
    c["log_renda"] = np.log(np.where(c["ano"].isin([1991, 2000]), c["renda_pc"], renda))
    c["log_renda_atlas"] = np.log(c["renda_pc"])
    c["alfabetizacao"] = np.where(c["ano"] == 2022, 100 * c["taxa_alfabetizacao"],
                                  100 - c["taxa_analfabetismo_15_mais"])
    return c


def diferencas(c: pd.DataFrame, a: int, b: int, desfechos: dict) -> pd.DataFrame:
    chave = ["id_amc", "sigla_uf", "id_microrregiao"]
    cols = [*desfechos, "share_soja", "share_agri_temp", "z_bcp_tend"]
    x = c[c["ano"] == a].set_index(chave)[cols].astype(float)
    y = c[c["ano"] == b].set_index(chave)[cols].astype(float)
    if a == 2000 and "log_renda" in desfechos:  # 2000–2010: renda do Atlas nos dois anos
        x["log_renda"] = c[c["ano"] == a].set_index(chave)["log_renda_atlas"]
        y["log_renda"] = c[c["ano"] == b].set_index(chave)["log_renda_atlas"]
    d = (y - x).add_prefix("d_")
    # nível inicial de cada desfecho (controle de convergência / teto)
    d = d.join(x[list(desfechos)].add_prefix("ini_")).reset_index()
    d["periodo"] = f"{a}-{b}"
    d["cluster"] = d["id_microrregiao"].astype(str)
    return d


def estimar() -> pd.DataFrame:
    c = base_censos()
    periodos = {(2000, 2010): DESF_2000_2010, (2010, 2022): DESF_2010_2022}
    blocos = {f"{a}-{b}": diferencas(c, a, b, des) for (a, b), des in periodos.items()}
    emp = pd.concat([blocos["2000-2010"][["id_amc", "sigla_uf", "cluster", "periodo",
                                          "d_share_soja", "d_share_agri_temp", "d_z_bcp_tend",
                                          *[f"d_{k}" for k in DESF_2010_2022],
                                          *[f"ini_{k}" for k in DESF_2010_2022]]],
                     blocos["2010-2022"]], ignore_index=True)
    specs = [(p, blocos[p], des, ["sigla_uf"]) for p, des in
             [("2000-2010", DESF_2000_2010), ("2010-2022", DESF_2010_2022)]]
    specs.append(("empilhado", emp, DESF_2010_2022, ["sigla_uf", "periodo"]))
    linhas = []
    for per, d, des, fe in specs:
        for k, rot in des.items():
          for ctrl in [False, True]:
            controles = [f"ini_{k}"] if ctrl else None
            r = iv_fe(d, f"d_{k}", "d_share_soja", "d_z_bcp_tend", fe=fe, controles=controles)
            s = d.dropna(subset=[f"d_{k}", "d_share_agri_temp", f"ini_{k}"])
            fe_f = " + ".join(f"C({f})" for f in fe) + (f" + ini_{k}" if ctrl else "")
            o = smf.ols(f"d_{k} ~ d_share_agri_temp + {fe_f}", data=s).fit(
                cov_type="cluster", cov_kwds={"groups": s["cluster"]})
            linhas.append({
                "período": per, "desfecho": rot,
                "controle nível inicial": "sim" if ctrl else "não",
                "2SLS (Δ soja)": r["iv_coef"],
                "2SLS ep": r["iv_ep"], "2SLS p": r["iv_p"], "AR 95% inf": r["ar_ic_inf"],
                "AR 95% sup": r["ar_ic_sup"], "F efetivo": r["F_efetivo"],
                "forma reduzida": r["rf_coef"], "FR ep": r["rf_ep"],
                "OLS (Δ soja)": r["ols_coef"], "OLS ep": r["ols_ep"],
                "OLS (Δ agri. temp.)": o.params["d_share_agri_temp"],
                "OLS agri ep": o.bse["d_share_agri_temp"], "n AMC": r["n"],
                "clusters": r["n_clusters"]})
            print(f"  {per} {k} ctrl={ctrl}: 2SLS {r['iv_coef']:.3f}{estrelas(r['iv_p'])} "
                  f"(F {r['F_efetivo']:.1f}) | OLS agri {o.params['d_share_agri_temp']:.3f}"
                  f"{estrelas(o.pvalues['d_share_agri_temp'])}", flush=True)
    return pd.DataFrame(linhas)


def main() -> int:
    t = estimar()
    salvar_tabela(t, "s08_censos_dif_longas",
                  "Diferenças longas entre censos (AMC): Δ desfecho contra Δ participação da "
                  "soja instrumentada pelo ganho tecnológico GAEZ; EF de UF; cluster por "
                  "microrregião", casas=3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
