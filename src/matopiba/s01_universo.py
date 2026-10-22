"""Etapa 1: universo de análise (municípios, grupos, Cerrado e AMC).

Saídas:
  data/processed/universo.parquet           atributos por município (sem geometria)
  data/processed/crosswalk_mun_amc.parquet  município -> AMC 1991–presente
  data/interim/malha_mun.parquet            malha municipal (GeoParquet, SIRGAS 2000)
  outputs/figuras/universo.png              mapa de conferência
  outputs/logs/s01_universo.md              resultado dos testes de aceite

Uso: python -m matopiba.s01_universo
"""

import sys
import urllib.request

import geobr
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

from matopiba.config import path, settings
from matopiba.gcp import bq_query

CFG = settings()["universo"]
CRS_AREA = settings()["crs_area"]

CORES = {"matopiba": "#2a78d6", "cerrado_fora": "#eb6834", "outros": "#e4e3df"}
ROTULOS = {
    "matopiba": "Matopiba",
    "cerrado_fora": "Cerrado fora do Matopiba",
    "outros": "Outros",
}


def lista_matopiba() -> set[str]:
    arq = path("raw") / CFG["matopiba_arquivo"]
    if not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(CFG["matopiba_url"], arq)
    df = pd.read_excel(arq, dtype={"CD_MUN": str})
    return set(df["CD_MUN"].str.strip())


def malha_municipal() -> gpd.GeoDataFrame:
    mun = geobr.read_municipality(year=CFG["ano_malha"], simplified=False, show_progress=False)
    mun["id_municipio"] = mun["code_muni"].astype("int64").astype(str)
    # a malha 2024 tem polígonos inválidos que quebram dissolve/union
    mun["geometry"] = mun.geometry.make_valid()
    return mun[["id_municipio", "name_muni", "abbrev_state", "geometry"]]


def cerrado_share(mun_alb: gpd.GeoDataFrame) -> pd.Series:
    bio = geobr.read_biomes(year=CFG["ano_biomas"], simplified=False, show_progress=False)
    cerrado = bio[bio["name_biome"] == "Cerrado"].to_crs(CRS_AREA)[["geometry"]]
    cerrado["geometry"] = cerrado.geometry.make_valid()
    inter = gpd.overlay(mun_alb[["id_municipio", "geometry"]], cerrado, how="intersection")
    area_cerrado = inter.assign(a=inter.area).groupby("id_municipio")["a"].sum()
    area = mun_alb.set_index("id_municipio").area
    return (area_cerrado.reindex(area.index, fill_value=0) / area).clip(upper=1.0)


def divisoes_regionais() -> pd.DataFrame:
    sql = """
    SELECT id_municipio, nome, sigla_uf, id_microrregiao, nome_microrregiao,
           id_regiao_imediata, nome_regiao_imediata
    FROM `basedosdados.br_bd_diretorios_brasil.municipio`
    """
    return bq_query(sql, max_gb=0.1)


def crosswalk_amc(mun_alb: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """AMC de Ehrl (2017) estendida aos municípios criados depois do último ano da AMC.

    Um município novo herda a AMC de onde saiu. Se saiu de mais de uma AMC, essas AMCs são
    fundidas (fusão estrita) e a AMC resultante recebe o menor código do grupo.
    """
    amc = geobr.read_comparable_areas(
        start_year=CFG["amc_ano_inicio"], end_year=CFG["amc_ano_fim"], show_progress=False
    )
    amc["code_amc"] = amc["code_amc"].astype("int64")
    base = (
        amc.drop(columns="geometry")
        .assign(id_municipio=amc["list_code_muni_2010"].str.split(","))
        .explode("id_municipio")[["id_municipio", "code_amc"]]
    )
    base["id_municipio"] = base["id_municipio"].str.strip()

    novos = mun_alb[~mun_alb["id_municipio"].isin(base["id_municipio"])]
    ov = gpd.overlay(
        novos[["id_municipio", "geometry"]],
        amc.to_crs(CRS_AREA)[["code_amc", "geometry"]],
        how="intersection",
    )
    ov["a"] = ov.area
    ov["share"] = ov["a"] / ov.groupby("id_municipio")["a"].transform("sum")
    ov = ov[ov["share"] >= CFG["amc_overlap_min"]]

    # union-find sobre os códigos de AMC ligados por um mesmo município novo
    pai: dict[int, int] = {}

    def raiz(x: int) -> int:
        while pai.setdefault(x, x) != x:
            x = pai[x]
        return x

    for _, g in ov.groupby("id_municipio"):
        codes = sorted(g["code_amc"])
        for c in codes[1:]:
            ra, rb = raiz(codes[0]), raiz(c)
            pai[max(ra, rb)] = min(ra, rb)

    novos_map = ov.sort_values("share", ascending=False).drop_duplicates("id_municipio")
    cw = pd.concat(
        [
            base.assign(fonte="ehrl"),
            novos_map[["id_municipio", "code_amc"]].assign(fonte="extensao"),
        ],
        ignore_index=True,
    )
    cw = cw.rename(columns={"code_amc": "id_amc_ehrl"})
    cw["id_amc"] = cw["id_amc_ehrl"].map(raiz)
    return cw[["id_municipio", "id_amc", "id_amc_ehrl", "fonte"]], ov.drop(columns="geometry")


def mapa(mun: gpd.GeoDataFrame, saida) -> None:
    # dissolver antes de simplificar: simplificar cada município abre frestas entre vizinhos
    completo = mun.to_crs(CRS_AREA)
    ufs = completo.dissolve("abbrev_state")
    ufs["geometry"] = ufs.geometry.simplify(500)
    contorno = completo[completo["grupo"] == "matopiba"].union_all().simplify(500)
    g = completo.assign(geometry=completo.geometry.simplify(500))
    mat = g[g["grupo"] == "matopiba"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5))
    for ax in axes:
        g.plot(ax=ax, color=g["grupo"].map(CORES), linewidth=0)
        ufs.boundary.plot(ax=ax, color="#5f5e5a", linewidth=0.4)
        ax.set_axis_off()
    xmin, ymin, xmax, ymax = mat.total_bounds
    pad = 0.08 * max(xmax - xmin, ymax - ymin)
    axes[1].set_xlim(xmin - pad, xmax + pad)
    axes[1].set_ylim(ymin - pad, ymax + pad)
    gpd.GeoSeries([contorno], crs=g.crs).boundary.plot(
        ax=axes[1], color="#1c1c1a", linewidth=0.8
    )
    for uf in ["MA", "TO", "PI", "BA"]:
        p = ufs.loc[uf].geometry.intersection(contorno).representative_point()
        axes[1].annotate(
            uf, (p.x, p.y), ha="center", fontsize=10, color="#1c1c1a", weight="bold"
        )
    axes[0].set_title("Brasil", fontsize=11, loc="left", color="#1c1c1a")
    axes[1].set_title(
        f"Matopiba ({len(mat)} municípios)", fontsize=11, loc="left", color="#1c1c1a"
    )
    n = g["grupo"].value_counts()
    handles = [
        Patch(
            facecolor=CORES[k],
            edgecolor="#5f5e5a",
            linewidth=0.4,
            label=f"{ROTULOS[k]} ({n.get(k, 0):,})".replace(",", "."),
        )
        for k in CORES
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=10)
    fig.suptitle(
        "Universo de análise: grupos de municípios",
        fontsize=13, x=0.02, ha="left", color="#1c1c1a",
    )
    fig.text(
        0.02, 0.005,
        f"Malha municipal IBGE {CFG['ano_malha']} (geobr); cerrado_fora: fora do Matopiba "
        f"e cerrado_share >= {CFG['cerrado_share_min']:.0%}",
        fontsize=8, color="#5f5e5a",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(saida, dpi=200, facecolor="white")
    plt.close(fig)


def main() -> int:
    ids_mat = lista_matopiba()
    mun = malha_municipal()
    mun_alb = mun.to_crs(CRS_AREA)

    df = pd.DataFrame({"id_municipio": mun["id_municipio"], "area_ha": mun_alb.area / 1e4})
    df["matopiba"] = df["id_municipio"].isin(ids_mat)
    df["cerrado_share"] = df["id_municipio"].map(cerrado_share(mun_alb))
    df["grupo"] = "outros"
    fora = ~df["matopiba"] & (df["cerrado_share"] >= CFG["cerrado_share_min"])
    df.loc[fora, "grupo"] = "cerrado_fora"
    df.loc[df["matopiba"], "grupo"] = "matopiba"

    df = df.merge(divisoes_regionais(), on="id_municipio", how="left")
    falta = df["nome"].isna()
    geo = mun.set_index("id_municipio")
    df.loc[falta, "nome"] = df.loc[falta, "id_municipio"].map(geo["name_muni"])
    df.loc[falta, "sigla_uf"] = df.loc[falta, "id_municipio"].map(geo["abbrev_state"])

    cw, ov_novos = crosswalk_amc(mun_alb)
    df = df.merge(cw[["id_municipio", "id_amc"]], on="id_municipio", how="left")

    # microrregiões não são atualizadas desde 2017: município criado depois (ex.: Boa
    # Esperança do Norte, MT) herda a mais frequente da sua região imediata
    sem_micro = df.loc[df["id_microrregiao"].isna(), "nome"].tolist()
    sem = df["id_microrregiao"].isna()
    moda = (df[~sem].groupby("id_regiao_imediata")[["id_microrregiao", "nome_microrregiao"]]
            .agg(lambda x: x.mode().iat[0]))
    for c in ["id_microrregiao", "nome_microrregiao"]:
        df.loc[sem, c] = df.loc[sem, "id_regiao_imediata"].map(moda[c])

    cols = [
        "id_municipio", "nome", "sigla_uf", "id_microrregiao", "nome_microrregiao",
        "id_regiao_imediata", "nome_regiao_imediata", "area_ha", "matopiba",
        "cerrado_share", "grupo", "id_amc",
    ]
    df = df[cols].sort_values("id_municipio").reset_index(drop=True)
    df.to_parquet(path("processed") / "universo.parquet", index=False)
    cw.to_parquet(path("processed") / "crosswalk_mun_amc.parquet", index=False)
    malha = mun.merge(df[["id_municipio", "grupo"]])
    malha.to_parquet(path("interim") / "malha_mun.parquet")
    mapa(malha, path("figuras") / "universo.png")

    # --- aceite ---
    mat = df[df["matopiba"]]
    area_mat = mat["area_ha"].sum()
    area_ofi = CFG["matopiba_area_oficial_ha"]
    desvio = area_mat / area_ofi - 1
    por_uf = mat["sigla_uf"].value_counts().to_dict()
    nao_encontrados = sorted(ids_mat - set(df["id_municipio"]))
    n_mat = CFG["matopiba_n_municipios"]
    testes = {
        f"{n_mat} municípios com matopiba=True (obtido: {len(mat)})": len(mat) == n_mat,
        f"Matopiba distribuído nas 4 UFs {por_uf}": set(por_uf) == {"MA", "TO", "PI", "BA"},
        f"Lista oficial toda encontrada na malha (faltando: {nao_encontrados})":
            not nao_encontrados,
        f"Área Matopiba {area_mat:,.0f} ha vs. oficial {area_ofi:,.0f} ha "
        f"(desvio {desvio:+.2%}, tolerância 1%)": abs(desvio) <= 0.01,
        f"Todo município com AMC (sem AMC: {df['id_amc'].isna().sum()})":
            bool(df["id_amc"].notna().all()),
        "id_municipio único": df["id_municipio"].is_unique,
    }
    info = [
        f"Municípios na malha {CFG['ano_malha']}: {len(df)}",
        f"Grupos: {df['grupo'].value_counts().to_dict()}",
        f"AMCs: {df['id_amc'].nunique()} (Ehrl original: {cw['id_amc_ehrl'].nunique()})",
        f"Municípios sem microrregião no BD (imputada pela região imediata): "
        f"{len(sem_micro)} {sem_micro}",
        f"Microrregiões no Matopiba: {mat['id_microrregiao'].nunique()}",
        f"cerrado_share médio no Matopiba: {mat['cerrado_share'].mean():.2f}",
        "Municípios criados após a AMC e AMCs de origem "
        f"(share >= {CFG['amc_overlap_min']:.0%}):",
    ]
    info += [
        f"  - {r.id_municipio}: AMC {r.code_amc} ({r.share:.1%})"
        for r in ov_novos.sort_values(["id_municipio", "share"]).itertuples()
    ]
    linhas = ["# Etapa 1 — universo: aceite", ""]
    linhas += [f"- [{'OK' if ok else 'FALHA'}] {t}" for t, ok in testes.items()]
    linhas += ["", "## Informações", ""]
    linhas += [i if i.startswith("  ") else f"- {i}" for i in info]
    texto = "\n".join(linhas) + "\n"
    (path("logs") / "s01_universo.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(testes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
