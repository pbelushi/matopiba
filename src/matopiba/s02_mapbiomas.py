"""Etapa 2: uso e cobertura da terra (MapBiomas) por município e ano.

Saídas:
  data/interim/mapbiomas_mun_ano.parquet   painel município × ano (áreas, participações,
                                           desmatamento)
  outputs/tabelas/s02_validacao_ee.csv     soja: tabela MapBiomas vs. Earth Engine
  outputs/figuras/s02_soja_matopiba_cerrado.png
  outputs/logs/s02_mapbiomas.md            resultado dos testes de aceite

Uso: python -m matopiba.s02_mapbiomas
"""

import sys
import urllib.request

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

from matopiba.config import path, settings
from matopiba.gcp import ee_init

CFG = settings()["mapbiomas"]
CRS_AREA = settings()["crs_area"]
ANOS = list(range(CFG["anos"][0], CFG["anos"][1] + 1))
CORES = {"matopiba": "#2a78d6", "cerrado_fora": "#eb6834"}
ROTULOS = {"matopiba": "Matopiba", "cerrado_fora": "Cerrado fora do Matopiba"}


def _baixar(url: str, arquivo: str):
    arq = path("raw") / arquivo
    if not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".xlsx"):
            urllib.request.urlretrieve(url, arq)
        else:  # zip no Google Drive (link de download com confirm=t)
            import io
            import zipfile

            with urllib.request.urlopen(url, timeout=900) as r:
                zipfile.ZipFile(io.BytesIO(r.read())).extractall(arq.parent)
    return arq


def cobertura_tabela(ids: set[str]) -> pd.DataFrame:
    """Área (ha) por município, classe e ano, somando os recortes por bioma."""
    arq = _baixar(CFG["cobertura_url"], CFG["cobertura_arquivo"])
    df = pd.read_excel(arq, "COVERAGE_11", engine="calamine")
    df["id_municipio"] = df["geocode"].astype("int64").astype(str)
    df = df[df["id_municipio"].isin(ids)]
    ycols = [f"y{a}" for a in ANOS]
    longo = df.melt(["id_municipio", "class"], ycols, var_name="ano", value_name="area_ha")
    longo["ano"] = longo["ano"].str[1:].astype(int)
    longo["fonte"] = "tabela"
    return (
        longo.groupby(["id_municipio", "class", "ano", "fonte"], as_index=False)["area_ha"]
        .sum()
    )


def cobertura_ee(ee, ids: list[str], malha: gpd.GeoDataFrame) -> pd.DataFrame:
    """Área por classe calculada no Earth Engine, para municípios ausentes da tabela."""
    img = ee.Image(CFG["ee_asset"])
    linhas = []
    for mid in ids:
        geom = _ee_geom(ee, malha, mid)
        for ano in ANOS:
            r = (
                ee.Image.pixelArea()
                .addBands(img.select(f"classification_{ano}"))
                .reduceRegion(
                    ee.Reducer.sum().group(groupField=1, groupName="class"),
                    geom, scale=30, maxPixels=1e13, tileScale=4,
                )
                .getInfo()
            )
            for g in r["groups"]:
                linhas.append((mid, int(g["class"]), ano, "ee", g["sum"] / 1e4))
    return pd.DataFrame(linhas, columns=["id_municipio", "class", "ano", "fonte", "area_ha"])


def _ee_geom(ee, malha: gpd.GeoDataFrame, mid: str):
    g = malha.loc[malha["id_municipio"] == mid].to_crs(CRS_AREA).geometry.simplify(15)
    return ee.Geometry(g.to_crs(4326).iloc[0].__geo_interface__)


def desmatamento(ids: set[str]) -> pd.DataFrame:
    arq = _baixar(CFG["desmatamento_url"], CFG["desmatamento_arquivo"])
    d = pd.read_excel(arq, "ANNUAL_DEFORESTATION", engine="calamine")
    d["id_municipio"] = d["GEOCODE"].astype("int64").astype(str)
    d = d[d["id_municipio"].isin(ids)]
    ycols = [c for c in d.columns if str(c).startswith("y")]
    longo = d.melt(["id_municipio", "TRANSITION_CLASS_ID"], ycols, var_name="ano",
                   value_name="ha")
    longo["ano"] = longo["ano"].str[1:].astype(int)
    tipo = longo["TRANSITION_CLASS_ID"].map({4: "desmat_prim_ha", 6: "desmat_sec_ha"})
    w = longo.assign(tipo=tipo).pivot_table(
        index=["id_municipio", "ano"], columns="tipo", values="ha", aggfunc="sum",
        fill_value=0,
    )
    w["desmat_ha"] = w.sum(axis=1)
    return w.reset_index(), (min(int(c[1:]) for c in ycols), max(int(c[1:]) for c in ycols))


def painel(longo: pd.DataFrame, universo: pd.DataFrame, defor: pd.DataFrame,
           anos_defor: tuple[int, int]) -> pd.DataFrame:
    idx = pd.MultiIndex.from_product([universo["id_municipio"], ANOS],
                                     names=["id_municipio", "ano"])
    por_classe = longo.pivot_table(index=["id_municipio", "ano"], columns="class",
                                   values="area_ha", aggfunc="sum", fill_value=0)
    por_classe = por_classe.reindex(idx, fill_value=0)

    def soma(codes):
        cols = [c for c in codes if c in por_classe.columns]
        return por_classe[cols].sum(axis=1)

    p = pd.DataFrame(index=idx)
    for nome, codes in CFG["classes"].items():
        p[f"area_{nome}_ha"] = soma(codes)
    p["area_agri_temp_ha"] = soma(CFG["agri_temp"])
    p["area_nativa_ha"] = soma(CFG["nativa"])
    p["area_total_mb_ha"] = por_classe.sum(axis=1)
    p = p.reset_index()

    fonte = longo.groupby("id_municipio")["fonte"].first()
    p["fonte_mapbiomas"] = p["id_municipio"].map(fonte).fillna("ausente")
    # sem cobertura do MapBiomas (ex.: Fernando de Noronha): áreas ficam NaN, não zero
    area_cols = [c for c in p.columns if c.startswith("area_")]
    sem = p["fonte_mapbiomas"].eq("ausente") | p["area_total_mb_ha"].eq(0)
    p.loc[sem, area_cols] = float("nan")
    p.loc[sem, "fonte_mapbiomas"] = "ausente"
    p = p.merge(universo[["id_municipio", "area_ha"]], on="id_municipio")
    desvio = (p["area_total_mb_ha"] / p["area_ha"] - 1).fillna(-1.0)
    p["flag_area_mb"] = desvio.abs().groupby(p["id_municipio"]).transform("max") > CFG[
        "tolerancia_soma_area"
    ]
    for col in [c for c in p.columns if c.startswith("area_") and c.endswith("_ha")
                and c not in ("area_ha", "area_total_mb_ha")]:
        p["share_" + col[len("area_"):-len("_ha")]] = p[col] / p["area_ha"]

    p = p.sort_values(["id_municipio", "ano"])
    p["perda_nativa_liq_ha"] = -p.groupby("id_municipio")["area_nativa_ha"].diff()
    p = p.merge(defor, on=["id_municipio", "ano"], how="left")
    dentro = p["ano"].between(*anos_defor)
    for c in ["desmat_prim_ha", "desmat_sec_ha", "desmat_ha"]:
        p.loc[dentro, c] = p.loc[dentro, c].fillna(0)
    p["colecao_mapbiomas"] = CFG["colecao"]
    return p.drop(columns="area_ha").reset_index(drop=True)


def validar_ee(ee, p: pd.DataFrame, universo: pd.DataFrame, malha) -> pd.DataFrame:
    """Recalcula a área de soja no EE para uma amostra de municípios e anos."""
    v = CFG["validacao"]
    a0 = v["anos"][0]
    elegiveis = p[(p["ano"] == a0) & (p["area_soja_ha"] >= 1000)]["id_municipio"]
    elegiveis = universo[universo["id_municipio"].isin(elegiveis)]
    # metade Matopiba, metade Cerrado fora
    n = v["n_municipios"] // 2
    amostra = pd.concat([
        elegiveis[elegiveis["grupo"] == g].sample(n, random_state=v["semente"])
        for g in ["matopiba", "cerrado_fora"]
    ])
    img = ee.Image(CFG["ee_asset"])
    linhas = []
    for r in amostra.itertuples():
        geom = _ee_geom(ee, malha, r.id_municipio)
        bandas = [img.select(f"classification_{a}").eq(39).rename(str(a)) for a in v["anos"]]
        soja = ee.Image.cat(bandas).multiply(ee.Image.pixelArea())
        res = soja.reduceRegion(ee.Reducer.sum(), geom, scale=30, maxPixels=1e13,
                                tileScale=4).getInfo()
        for a in v["anos"]:
            tab = p.loc[(p["id_municipio"] == r.id_municipio) & (p["ano"] == a),
                        "area_soja_ha"].iloc[0]
            linhas.append({"id_municipio": r.id_municipio, "nome": r.nome,
                           "sigla_uf": r.sigla_uf, "grupo": r.grupo, "ano": a,
                           "soja_tabela_ha": tab, "soja_ee_ha": res[str(a)] / 1e4})
    out = pd.DataFrame(linhas)
    out["divergencia"] = out["soja_ee_ha"] / out["soja_tabela_ha"] - 1
    return out


def figura_soja(p: pd.DataFrame, universo: pd.DataFrame, saida) -> None:
    s = (
        p.merge(universo[["id_municipio", "grupo"]])
        .query("grupo in ['matopiba', 'cerrado_fora']")
        .groupby(["grupo", "ano"])["area_soja_ha"].sum() / 1e6
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    for g in ["matopiba", "cerrado_fora"]:
        serie = s.loc[g]
        ax.plot(serie.index, serie.values, color=CORES[g], linewidth=2, label=ROTULOS[g])
        ax.annotate(f"{ROTULOS[g]}\n{serie.iloc[-1]:.1f} Mha", (serie.index[-1], serie.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=9,
                    color="#1c1c1a")
    ax.set_ylabel("Área de soja (milhões de ha)", color="#5f5e5a")
    ax.set_xlim(ANOS[0], ANOS[-1] + 9)
    ax.set_xticks(range(ANOS[0], ANOS[-1] + 1, 5))
    ax.set_ylim(0, None)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    for lado in ["top", "right"]:
        ax.spines[lado].set_visible(False)
    for lado in ["left", "bottom"]:
        ax.spines[lado].set_color("#a8a79f")
    ax.tick_params(colors="#5f5e5a")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Área de soja: Matopiba vs. Cerrado fora do Matopiba",
                 loc="left", fontsize=12, color="#1c1c1a")
    fig.text(0.01, 0.01, f"Fonte: MapBiomas Coleção {CFG['colecao']}, estatísticas municipais "
             "(classe 39). Cerrado fora: cerrado_share >= 50%.", fontsize=8, color="#5f5e5a")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(saida, dpi=200, facecolor="white")
    plt.close(fig)


def main() -> int:
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")
    ids = set(universo["id_municipio"])
    ee = ee_init()

    longo = cobertura_tabela(ids)
    ausentes = sorted(ids - set(longo["id_municipio"]))
    if ausentes:
        longo = pd.concat([longo, cobertura_ee(ee, ausentes, malha)], ignore_index=True)
    defor, anos_defor = desmatamento(ids)
    p = painel(longo, universo, defor, anos_defor)
    p.to_parquet(path("interim") / "mapbiomas_mun_ano.parquet", index=False)

    val = validar_ee(ee, p, universo, malha)
    val.to_csv(path("tabelas") / "s02_validacao_ee.csv", index=False)
    figura_soja(p, universo, path("figuras") / "s02_soja_matopiba_cerrado.png")

    # --- aceite ---
    n_esp = len(universo) * len(ANOS)
    chave_unica = not p.duplicated(["id_municipio", "ano"]).any()
    area = p.merge(universo[["id_municipio", "area_ha", "grupo"]])
    area["desvio"] = (area["area_total_mb_ha"] / area["area_ha"] - 1).fillna(-1.0)
    tol = CFG["tolerancia_soma_area"]
    fora = area[area["desvio"].abs() > tol]
    mun_fora = fora.drop_duplicates("id_municipio")
    analise = fora[fora["grupo"].isin(["matopiba", "cerrado_fora"])]
    max_div = val["divergencia"].abs().max()
    testes = {
        f"Painel balanceado: {len(p):,} linhas = {len(universo):,} municípios × {len(ANOS)} "
        f"anos, chave única": len(p) == n_esp and chave_unica,
        f"Soma das classes ≈ área do município (tolerância {tol:.0%}) em todos os municípios "
        f"do Matopiba e do Cerrado fora (fora: {analise['id_municipio'].nunique()})":
            analise.empty,
        f"Divergência tabela × EE < {CFG['validacao']['tolerancia']:.0%} "
        f"(máx. {max_div:.2%}, {len(val)} pares)": max_div < CFG["validacao"]["tolerancia"],
    }
    mat = area[area["grupo"] == "matopiba"]["desvio"]
    info = [
        f"Coleção {CFG['colecao']}, anos {ANOS[0]}–{ANOS[-1]}; desmatamento {anos_defor}",
        f"Municípios calculados no EE (ausentes da tabela): {ausentes}",
        f"AVISO — universo todo: {1 - len(fora) / len(area):.2%} das linhas dentro da "
        f"tolerância; {len(mun_fora)} municípios fora, todos do grupo "
        f"{sorted(mun_fora['grupo'].unique())} (costeiros + Fernando de Noronha), marcados "
        "com flag_area_mb. Aceito pelo usuário: o critério vale para os grupos de análise.",
        f"Desvio soma das classes/área IBGE — mediana {area['desvio'].median():+.2%}, "
        f"p1 {area['desvio'].quantile(0.01):+.2%}, p99 {area['desvio'].quantile(0.99):+.2%}; "
        f"Matopiba: máx. |desvio| {mat.abs().max():.2%}",
        "Municípios fora da tolerância (pior ano): "
        + "; ".join(
            f"{r.nome} ({r.sigla_uf}, {r.grupo}) {r.desvio:+.1%}"
            for r in fora.merge(universo[["id_municipio", "nome", "sigla_uf"]])
            .sort_values("desvio", key=abs, ascending=False)
            .drop_duplicates("id_municipio").itertuples()
        ),
    ]
    linhas = ["# Etapa 2 — MapBiomas: aceite", ""]
    linhas += [f"- [{'OK' if ok else 'FALHA'}] {t}" for t, ok in testes.items()]
    linhas += ["", "## Informações", ""] + [f"- {i}" for i in info]
    linhas += ["", "## Validação no Earth Engine (soja)", "",
               val.to_markdown(index=False, floatfmt=".4f")]
    texto = "\n".join(linhas) + "\n"
    (path("logs") / "s02_mapbiomas.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(testes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
