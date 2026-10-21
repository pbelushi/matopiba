"""Etapa 8.6: robustez do DiD (Callaway–Sant'Anna, agricultura temporária).

Especificações (todas com os 5 desfechos principais):
  principal          município, limiar 10%
  amc                AMC (municípios criados depois de 1985 deixam de cair do painel balanceado)
  microrregiao       microrregião (absorve transbordamentos entre municípios vizinhos)
  sem_polos          exclui os `n_polos` maiores polos de soja do Matopiba
  limiar_05/limiar_20
  migracao           TWFE com e sem controle de migração (% não naturais em 2000 × tendência),
                     comparação dos coeficientes
  placebo_antecipado coorte fictícia 5 anos antes, usando só anos pré-tratamento reais

Saídas:
  outputs/tabelas/s08_robustez.{csv,tex}

Uso: python -m matopiba.s08_robustez
"""

import sys

import numpy as np
import pandas as pd

from matopiba.analise import (CFG, DESFECHOS, amostra_did, carregar, cs_did, estrelas,
                              preparar_desfecho, salvar_tabela, twfe)
from matopiba.config import path
from matopiba.s07_paineis import agregar, tratamentos


def _cs(s: pd.DataFrame, espec: str, balancear: bool = True) -> list[dict]:
    linhas = []
    for d in DESFECHOS:
        r = cs_did(s.assign(y=preparar_desfecho(s, d)), "y", balancear=balancear)["simples"]
        linhas.append({"especificação": espec, "desfecho": d.rotulo, "estimador": "CS",
                       "coef": r.get("att"), "ep": r.get("ep"), "p": r.get("p"),
                       "tratados": r.get("n_unidades_tratadas"),
                       "controles": r.get("n_controles")})
        print(f"  {espec} {d.nome}: {r.get('att', np.nan):.4f}{estrelas(r.get('p', 1))}",
              flush=True)
    return linhas


def microrregiao(p: pd.DataFrame) -> pd.DataFrame:
    m = agregar(p, "id_microrregiao", extras=[])
    univ = pd.read_parquet(path("processed") / "universo.parquet")
    g = (univ.groupby(["id_microrregiao", "grupo"])["area_ha"].sum().reset_index()
         .sort_values("area_ha").drop_duplicates("id_microrregiao", keep="last")
         .set_index("id_microrregiao")["grupo"])
    m["grupo"] = m["id_microrregiao"].map(g)
    m = tratamentos(m, "id_microrregiao")
    m["unidade"] = m["id_microrregiao"]
    m["cluster"] = m["id_microrregiao"].astype(str)  # a própria unidade
    return m


def placebo(s: pd.DataFrame) -> pd.DataFrame:
    """Coorte fictícia g-5 com os dados dos tratados restritos a anos < g (pré-tratamento)."""
    x = s.copy()
    real = x["coorte"]
    x = x[real.isna() | (x["ano"] < real)]
    x["coorte"] = real.loc[x.index] - 5
    return x


def main() -> int:
    p = carregar()
    s = amostra_did(p)
    linhas = []
    linhas += _cs(s, "principal (município, 10%)")
    amc = carregar("amc")
    linhas += _cs(amostra_did(amc), "AMC")
    linhas += _cs(amostra_did(microrregiao(p)), "microrregião")
    ult = p["ano"].max()
    polos = (p[(p["ano"] == ult) & (p["grupo"] == "matopiba")]
             .nlargest(CFG["n_polos"], "area_soja_ha")["id_municipio"])
    linhas += _cs(s[~s["unidade"].isin(polos)], f"sem os {CFG['n_polos']} maiores polos")
    linhas += _cs(amostra_did(p, limiar=0.05), "limiar 5%")
    linhas += _cs(amostra_did(p, limiar=0.20), "limiar 20%")
    linhas += _cs(placebo(s), "placebo: tratamento antecipado em 5 anos", balancear=False)

    mig = pd.read_parquet(path("interim") / "socio_migracao.parquet").query("ano == 2000")
    s2 = s.merge(mig[["id_municipio", "pct_nao_natural_municipio"]].rename(
        columns={"id_municipio": "unidade", "pct_nao_natural_municipio": "mig2000"}),
        on="unidade", how="left")
    s2["mig_x_tend"] = s2["mig2000"] * (s2["ano"] - 2000) / 10
    for d in DESFECHOS:
        x = s2.assign(y=preparar_desfecho(s2, d)).dropna(subset=["mig_x_tend"])
        for ctrl, rot in [(None, "TWFE sem controle de migração"),
                          (["mig_x_tend"], "TWFE com migração 2000 × tendência")]:
            r = twfe(x, "y", "tratado", controles=ctrl)
            linhas.append({"especificação": rot, "desfecho": d.rotulo, "estimador": "TWFE",
                           "coef": r["coef"], "ep": r["ep"], "p": r["p"],
                           "tratados": np.nan, "controles": np.nan})
            print(f"  {rot} {d.nome}: {r['coef']:.4f}{estrelas(r['p'])}", flush=True)
    t = pd.DataFrame(linhas)
    salvar_tabela(t, "s08_robustez",
                  "Robustez do DiD escalonado (agricultura temporária): níveis de agregação, "
                  "exclusão de polos, limiares, migração e placebo", casas=4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
