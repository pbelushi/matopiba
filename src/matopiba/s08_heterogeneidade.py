"""Etapa 8.5: heterogeneidade e mecanismos.

1. Concentração fundiária (AMC, Censo Agro 2006→2017): Δ Gini da terra, Δ % da área em
   estabelecimentos de 1.000 ha ou mais e Δ % de estabelecimentos com menos de 10 ha contra
   Δ participação da soja (OLS e 2SLS com o ganho tecnológico; nível inicial como controle).
   (Gini da renda e pobreza: ver s08_censos.)
2. Emprego agro vs. não agro (Callaway–Sant'Anna): vínculos por habitante e salário médio.
3. Polos vs. vizinhos: os `n_polos` municípios do Matopiba com maior área de soja em 2025 e
   seus vizinhos nunca tratados (transbordamento; coorte do vizinho = primeira coorte dos polos
   adjacentes), contra os demais nunca tratados.

Saídas:
  outputs/tabelas/s08_heterog_fundiaria.{csv,tex}
  outputs/tabelas/s08_heterog_emprego.{csv,tex}
  outputs/tabelas/s08_heterog_polos.{csv,tex}

Uso: python -m matopiba.s08_heterogeneidade
"""

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from matopiba.analise import (CFG, DESFECHOS, amostra_did, carregar, cs_did, estrelas, iv_fe,
                              preparar_desfecho, salvar_tabela)
from matopiba.config import path


def fundiaria() -> pd.DataFrame:
    c = pd.read_parquet(path("processed") / "painel_censos.parquet")
    c = c[c["tipo_censo"] == "agropecuario"]
    amc = pd.read_parquet(path("processed") / "painel_amc.parquet",
                          columns=["id_amc", "sigla_uf", "id_microrregiao", "grupo"])
    info = amc.drop_duplicates("id_amc")
    cols = ["gini_terra", "share_area_1000ha_mais", "share_estab_menos_10ha", "share_soja",
            "z_bcp_tend"]
    a = c[c["ano"] == 2006].set_index("id_amc")[cols].astype(float)
    b = c[c["ano"] == 2017].set_index("id_amc")[cols].astype(float)
    d = (b - a).add_prefix("d_").join(a.add_prefix("ini_")).reset_index().merge(info)
    d = d[d["grupo"].isin(CFG["grupos"])]
    d["cluster"] = d["id_microrregiao"].astype(str)
    rot = {"gini_terra": "Gini da terra", "share_area_1000ha_mais": "% área em >= 1.000 ha",
           "share_estab_menos_10ha": "% estabelecimentos < 10 ha"}
    linhas = []
    for k, r in rot.items():
        iv = iv_fe(d, f"d_{k}", "d_share_soja", "d_z_bcp_tend", fe=["sigla_uf"],
                   controles=[f"ini_{k}"])
        s = d.dropna(subset=[f"d_{k}", f"ini_{k}"])
        o = smf.ols(f"d_{k} ~ d_share_soja + ini_{k} + C(sigla_uf)", data=s).fit(
            cov_type="cluster", cov_kwds={"groups": s["cluster"]})
        linhas.append({"desfecho (Δ 2006–2017)": r, "OLS": o.params["d_share_soja"],
                       "OLS ep": o.bse["d_share_soja"], "OLS p": o.pvalues["d_share_soja"],
                       "2SLS": iv["iv_coef"], "2SLS ep": iv["iv_ep"], "2SLS p": iv["iv_p"],
                       "F efetivo": iv["F_efetivo"], "AR 95% inf": iv["ar_ic_inf"],
                       "AR 95% sup": iv["ar_ic_sup"], "n AMC": iv["n"]})
        print(f"  fundiária {k}: OLS {o.params['d_share_soja']:.3f}"
              f"{estrelas(o.pvalues['d_share_soja'])} | 2SLS {iv['iv_coef']:.3f} "
              f"(F {iv['F_efetivo']:.1f})", flush=True)
    return pd.DataFrame(linhas)


def emprego(s: pd.DataFrame) -> pd.DataFrame:
    s = s.copy()
    s["log_vinc_agro_pc"] = np.log((s["vinculos_agro"] / s["populacao"]).where(
        s["vinculos_agro"] > 0))
    s["log_vinc_nao_agro_pc"] = np.log((s["vinculos_nao_agro"] / s["populacao"]).where(
        s["vinculos_nao_agro"] > 0))
    s["log_sal_agro"] = np.log(s["salario_medio_real_agro"].where(
        s["salario_medio_real_agro"] > 0))
    s["log_sal_nao_agro"] = np.log(s["salario_medio_real_nao_agro"].where(
        s["salario_medio_real_nao_agro"] > 0))
    specs = [("log_vinc_agro_pc", "log vínculos agro por hab.", (1995, 2025)),
             ("log_vinc_nao_agro_pc", "log vínculos não agro por hab.", (1995, 2025)),
             ("log_sal_agro", "log salário médio real, agro", (1999, 2025)),
             ("log_sal_nao_agro", "log salário médio real, não agro", (1999, 2025))]
    linhas = []
    for col, rot, anos in specs:
        x = s.assign(y=s[col].where(s["ano"].between(*anos)))
        r = cs_did(x, "y")["simples"]
        linhas.append({"desfecho": rot, "anos": r["anos"], "CS ATT": r["att"], "ep": r["ep"],
                       "p": r["p"], "pré-tendência": r["pre_media"],
                       "tratados": r["n_unidades_tratadas"], "controles": r["n_controles"]})
        print(f"  emprego {col}: {r['att']:.3f}{estrelas(r['p'])} ({r['ep']:.3f})", flush=True)
    return pd.DataFrame(linhas)


def polos_vizinhos(p: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    n = CFG["n_polos"]
    ult = p["ano"].max()
    polos = (p[(p["ano"] == ult) & (p["grupo"] == "matopiba")]
             .nlargest(n, "area_soja_ha")[["id_municipio", "nome"]])
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")[["id_municipio", "geometry"]]
    g_polos = malha[malha["id_municipio"].isin(polos["id_municipio"])]
    viz = gpd.sjoin(malha, g_polos.rename(columns={"id_municipio": "polo"}),
                    predicate="touches")[["id_municipio", "polo"]]
    viz = viz[~viz["id_municipio"].isin(polos["id_municipio"])]
    coorte_polo = s.drop_duplicates("unidade").set_index("unidade")["coorte"]
    viz["coorte_polo"] = viz["polo"].map(coorte_polo)
    coorte_viz = viz.groupby("id_municipio")["coorte_polo"].min()
    nunca = s["coorte"].isna()
    linhas = []
    for d in DESFECHOS:
        y = preparar_desfecho(s, d)
        # (a) polos: coorte própria, contra nunca tratados não vizinhos
        a = s[s["unidade"].isin(polos["id_municipio"]) | (nunca & ~s["unidade"].isin(
            coorte_viz.index))].assign(y=y)
        ra = cs_did(a, "y")["simples"]
        # (b) vizinhos nunca tratados: "tratados" na coorte do polo adjacente
        b = s[nunca].assign(y=y).copy()
        b["coorte"] = b["unidade"].map(coorte_viz)
        rb = cs_did(b, "y")["simples"]
        for grupo, r in [("polos", ra), ("vizinhos não tratados (transbordamento)", rb)]:
            linhas.append({"desfecho": d.rotulo, "grupo": grupo, "CS ATT": r.get("att"),
                           "ep": r.get("ep"), "p": r.get("p"),
                           "tratados": r.get("n_unidades_tratadas"),
                           "controles": r.get("n_controles")})
        print(f"  polos/vizinhos {d.nome}: polos {ra.get('att', np.nan):.3f} | vizinhos "
              f"{rb.get('att', np.nan):.3f}{estrelas(rb.get('p', 1))}", flush=True)
    t = pd.DataFrame(linhas)
    t.attrs["polos"] = ", ".join(polos["nome"])
    return t


def main() -> int:
    p = carregar()
    s = amostra_did(p)
    f = fundiaria()
    salvar_tabela(f, "s08_heterog_fundiaria",
                  "Concentração fundiária (AMC, Censo Agro 2006→2017): Δ desfecho contra Δ "
                  "participação da soja; controle de nível inicial e EF de UF")
    e = emprego(s)
    salvar_tabela(e, "s08_heterog_emprego",
                  "Emprego formal agro vs. não agro: ATT de Callaway–Sant'Anna (agricultura "
                  "temporária >= 10%)", casas=4)
    pv = polos_vizinhos(p, s)
    salvar_tabela(pv, "s08_heterog_polos",
                  f"Polos ({pv.attrs['polos']}) e transbordamento para vizinhos nunca tratados:"
                  " ATT de Callaway–Sant'Anna", casas=4)
    print("polos:", pv.attrs["polos"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
