"""Testes dos painéis da Etapa 7 (rodar depois de `python -m matopiba.s07_paineis`)."""

import numpy as np
import pandas as pd
import pytest

from matopiba.config import path, settings
from matopiba.s07_paineis import VARS

ANOS = list(range(settings()["mapbiomas"]["anos"][0], settings()["mapbiomas"]["anos"][1] + 1))


@pytest.fixture(scope="module")
def universo():
    return pd.read_parquet(path("processed") / "universo.parquet")


@pytest.fixture(scope="module")
def mun():
    return pd.read_parquet(path("processed") / "painel_municipio.parquet")


@pytest.fixture(scope="module")
def amc():
    return pd.read_parquet(path("processed") / "painel_amc.parquet")


@pytest.fixture(scope="module")
def censos():
    return pd.read_parquet(path("processed") / "painel_censos.parquet")


@pytest.mark.parametrize("nome,chave", [("mun", ["id_municipio", "ano"]),
                                        ("amc", ["id_amc", "ano"]),
                                        ("censos", ["id_amc", "ano"])])
def test_chaves_unicas(request, nome, chave):
    df = request.getfixturevalue(nome)
    assert df[chave].notna().all().all()
    assert not df.duplicated(chave).any()


@pytest.mark.parametrize("nome", ["mun", "amc", "censos"])
def test_sem_linhas_duplicadas(request, nome):
    df = request.getfixturevalue(nome)
    assert not df.astype(str).duplicated().any()


def test_painel_municipio_balanceado(mun, universo):
    assert len(mun) == len(universo) * len(ANOS)
    assert set(mun["id_municipio"]) == set(universo["id_municipio"])
    assert (mun.groupby("id_municipio")["ano"].nunique() == len(ANOS)).all()


def test_painel_amc_balanceado(amc, universo):
    assert set(amc["id_amc"]) == set(universo["id_amc"])
    assert len(amc) == universo["id_amc"].nunique() * len(ANOS)


def test_somas_preservadas_na_agregacao(mun, amc):
    somas = [c for c, v in VARS.items() if v.agregacao == "soma" and c in mun and c in amc]
    assert len(somas) > 30
    a = mun.groupby("ano")[somas].sum(min_count=1)
    b = amc.groupby("ano")[somas].sum(min_count=1)
    pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9)


def test_razoes_recalculadas_na_amc(amc, mun):
    for c in ["tmi", "pib_pc_real", "share_soja", "share_agri_temp", "luz_pc",
              "share_vinculos_agro"]:
        v = VARS[c]
        esperado = amc[v.num] / amc[v.den].where(amc[v.den] > 0) * v.mult
        np.testing.assert_allclose(amc[c], esperado, rtol=1e-12, equal_nan=True)
    # em AMCs com vários municípios a razão das somas difere da média das razões
    m = mun.groupby(["id_amc", "ano"])["share_soja"].mean().rename("media_razoes")
    x = amc.set_index(["id_amc", "ano"]).join(m)
    multi = x[x["n_municipios"] > 1].dropna(subset=["share_soja", "media_razoes"])
    assert (multi["share_soja"] - multi["media_razoes"]).abs().max() > 1e-6


def test_participacoes_entre_0_e_1(mun, amc):
    for df in (mun, amc):
        for c in ["share_soja", "share_agri_temp", "share_nativa", "share_pasto"]:
            s = df[c].dropna()
            assert ((s >= 0) & (s <= 1.02)).all(), c


def test_tratamento_coerente(mun):
    t = settings()["tratamento"]
    x = int(round(t["limiar_padrao"] * 100))
    tr, ano_tr = mun[f"trat_agri_temp_{x:02d}"], mun[f"ano_trat_agri_temp_{x:02d}"]
    ok = tr.notna()
    assert ((tr[ok] == 1) == (mun.loc[ok, "ano"] >= ano_tr[ok])).all()
    # no ano de entrada a participação cruza o limiar
    entrada = mun[mun["ano"] == ano_tr]
    assert (entrada["share_agri_temp"] >= t["limiar_padrao"]).all()


def test_censos_tem_anos_censitarios(censos):
    dem = censos[censos["tipo_censo"] == "demografico"]
    assert set(dem["ano"]) == set(settings()["tratamento"]["anos_censo"])
    assert set(censos.loc[censos["tipo_censo"] == "agropecuario", "ano"]) == {2006, 2017}
    assert dem.loc[dem["ano"] == 2010, "idhm"].notna().mean() > 0.99
