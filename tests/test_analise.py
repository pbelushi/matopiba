"""O Callaway–Sant'Anna próprio (analise.cs_did) confere com o pacote `differences`."""

import numpy as np
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
