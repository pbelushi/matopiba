"""O Callaway–Sant'Anna próprio (analise.cs_did) confere com o pacote `differences`."""

import numpy as np
import pandas as pd
import pytest
from differences import ATTgt

from matopiba.analise import DESFECHOS, amostra_did, carregar, cs_did, preparar_desfecho


@pytest.fixture(scope="module")
def amostra():
    return amostra_did(carregar())


@pytest.mark.parametrize("desfecho", [d for d in DESFECHOS if d.nome in ("log_pib_pc",
                                                                          "log_luz_pc")])
def test_cs_confere_com_differences(amostra, desfecho):
    s = amostra.copy()
    s["y"] = preparar_desfecho(s, desfecho)
    meu = cs_did(s, "y")
    x = s.dropna(subset=["y"])
    anos = x["ano"].nunique()
    x = x[x.groupby("unidade")["ano"].transform("nunique") == anos]
    x = x[x["coorte"].isna() | (x["coorte"] > x["ano"].min())]
    att = ATTgt(data=x.set_index(["unidade", "ano"])[["y", "coorte"]], cohort_column="coorte")
    att.fit(formula="y", control_group="never_treated", progress_bar=False)
    ref = att.aggregate("simple").iloc[0, 0]
    assert np.isclose(meu["simples"]["att"], ref, rtol=1e-6)
    ev = att.aggregate("event").iloc[:, 0]
    mine = meu["evento"].set_index("e")["att"]
    comum = mine.index.intersection(ev.index)
    assert np.allclose(mine[comum], ev[comum], atol=1e-3)


def test_dr_so_intercepto_igual_incondicional(amostra):
    """O DiD duplamente robusto sem covariáveis (só intercepto) é o CS incondicional."""
    s = amostra.assign(y=preparar_desfecho(amostra, DESFECHOS[0]))
    s = s.dropna(subset=["y"])
    s = s[s.groupby("unidade")["ano"].transform("nunique") == s["ano"].nunique()]
    sem = cs_did(s, "y", balancear=False)["simples"]
    vazio = pd.DataFrame(index=s["unidade"].unique())
    dr = cs_did(s, "y", balancear=False, covariaveis=vazio)["simples"]
    assert np.isclose(sem["att"], dr["att"], rtol=1e-10)
    assert np.isclose(sem["ep"], dr["ep"], rtol=1e-8)


def test_antecipacao_desloca_a_base(amostra):
    """Com antecipação δ, ATT(g, g) usa a base g-1-δ."""
    s = amostra.assign(y=preparar_desfecho(amostra, DESFECHOS[0]))
    gt = cs_did(s, "y", antecipacao=2)["gt"].set_index(["coorte", "ano"])
    g = int(gt.index.get_level_values(0).max())
    w = s.dropna(subset=["y"]).pivot_table(index="unidade", columns="ano", values="y")
    info = s.drop_duplicates("unidade").set_index("unidade")["coorte"]
    w = w.dropna()
    dy = w[g] - w[g - 3]
    c = info.loc[w.index]
    # coortes depois do fim da janela contam como nunca tratadas
    trat, nunca = c == g, c.isna() | (c > w.columns.max())
    assert np.isclose(gt.loc[(g, g), "att"], dy[trat].mean() - dy[nunca].mean())
