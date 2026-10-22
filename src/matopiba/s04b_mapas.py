"""Etapa 4b (figuras): mapas comparativos da mancha urbana.

1. Cidades: janela em torno da sede de cada polo do Matopiba (maiores áreas de soja em 2025,
   como em s08_heterogeneidade) e de Luís Eduardo Magalhães, com a classe 24 do MapBiomas C11
   colorida pelo período em que o pixel aparece como urbano pela primeira vez entre os anos de
   corte, e o contorno da máscara urbana de 2012 (classe 24 + buffer). Recortes por consulta
   interativa ao EE (computePixels), a 30 m.
2. Região: crescimento da área urbanizada 2000→2025 por município (Matopiba e Cerrado fora).

Saídas:
  outputs/figuras/s04b_mancha_urbana_cidades.png
  outputs/figuras/s04b_mancha_urbana_regiao.png

Uso: python -m matopiba.s04b_mapas
"""

import sys

import geobr
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

from matopiba.config import path, settings
from matopiba.gcp import ee_init
from matopiba.s04_construido import PASTA

CFG = settings()["urbano"]
MB = settings()["mapbiomas"]
CORTES = [1985, 2000, 2012, 2025]
EXTRA = {"2919553": "Luís Eduardo Magalhães"}   # cidade-símbolo do agro no oeste baiano
MEIA_JANELA_KM = 10
ESCALA_M = 30
# sequencial de um só tom: mais antigo = mais escuro
CORES = ["#0b3a75", "#2a78d6", "#7fb0ea", "#c9ddf6"]
TINTA, TINTA2, GRADE, FUNDO = "#1c1c1a", "#5f5e5a", "#e4e3df", "#f4f3ef"


def cidades() -> pd.DataFrame:
    p = pd.read_parquet(path("processed") / "painel_municipio.parquet",
                        columns=["id_municipio", "ano", "area_soja_ha", "grupo", "nome"])
    ult = p["ano"].max()
    polos = (p[(p["ano"] == ult) & (p["grupo"] == "matopiba")]
             .nlargest(settings()["analise"]["n_polos"], "area_soja_ha")[["id_municipio",
                                                                          "nome"]])
    polos = pd.concat([polos, pd.DataFrame({"id_municipio": list(EXTRA),
                                            "nome": list(EXTRA.values())})])
    sedes = geobr.read_municipal_seat(year=2010, show_progress=False)
    sedes["id_municipio"] = sedes["code_muni"].astype("int64").astype(str)
    sedes["lon"], sedes["lat"] = sedes.geometry.x, sedes.geometry.y
    return polos.merge(pd.DataFrame(sedes[["id_municipio", "lon", "lat"]]), on="id_municipio")


def recorte(ee, lon: float, lat: float) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """Período da primeira aparição urbana (0 = nunca; 1..4 = corte) e máscara de 2012."""
    mb = ee.Image(MB["ee_asset"])
    periodo = ee.Image(0)
    for i, a in reversed(list(enumerate(CORTES, start=1))):
        urb = mb.select(f"classification_{a}").remap(CFG["classes"], [1] * len(CFG["classes"]),
                                                    0)
        periodo = periodo.where(urb.eq(1), i)
    msk = ee.Image(f"{PASTA}/{CFG['asset_mascara']}").select(f"m{CFG['ano_mascara_ref']}")
    img = ee.Image.cat([periodo.rename("p").toByte(), msk.unmask(0).rename("m").toByte()])
    dlat = ESCALA_M / 111_320
    dlon = dlat / np.cos(np.radians(lat))
    n = int(2 * MEIA_JANELA_KM * 1000 / ESCALA_M)
    x0, y0 = lon - n / 2 * dlon, lat + n / 2 * dlat
    arr = ee.data.computePixels({
        "expression": img, "fileFormat": "NUMPY_NDARRAY",
        "grid": {"dimensions": {"width": n, "height": n},
                 "affineTransform": {"scaleX": dlon, "shearX": 0, "translateX": x0,
                                     "shearY": 0, "scaleY": -dlat, "translateY": y0},
                 "crsCode": "EPSG:4326"}})
    return arr["p"], arr["m"], [x0, x0 + n * dlon, y0 - n * dlat, y0]


def figura_cidades(ee) -> pd.DataFrame:
    c = cidades()
    ncol = 3
    nlin = int(np.ceil(len(c) / ncol))
    fig, axes = plt.subplots(nlin, ncol, figsize=(4.6 * ncol, 4.9 * nlin))
    cmap = ListedColormap([FUNDO, *CORES])
    norm = BoundaryNorm(np.arange(-0.5, len(CORTES) + 1), cmap.N)
    linhas = []
    for ax, r in zip(axes.flat, c.itertuples(), strict=False):
        p, m, ext = recorte(ee, r.lon, r.lat)
        ax.imshow(p, cmap=cmap, norm=norm, extent=ext, interpolation="nearest")
        ax.contour(m, levels=[0.5], colors=[TINTA2], linewidths=0.8, extent=ext,
                   origin="upper")
        ax.set_aspect(1 / np.cos(np.radians(r.lat)))
        px_km2 = (ESCALA_M / 1000) ** 2
        # p == i ⇔ urbano pela 1ª vez no corte i; urbano em CORTES[k] ⇔ 1 <= p <= k+1
        areas = [((p >= 1) & (p <= k + 1)).sum() * px_km2 for k in range(len(CORTES))]
        linhas.append({"id_municipio": r.id_municipio, "nome": r.nome,
                       **{f"urbano_{a}_km2": v for a, v in zip(CORTES, areas, strict=True)}})
        ax.set_title(r.nome, fontsize=11, color=TINTA, loc="left")
        ax.text(0.01, 0.01, f"urbano: {areas[0]:.1f} km² (1985) → {areas[-1]:.1f} km² (2025)",
                transform=ax.transAxes, fontsize=8, color=TINTA2, va="bottom",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 2})
        ax.set_xticks([])
        ax.set_yticks([])
        for lado in ax.spines.values():
            lado.set_color(GRADE)
    for ax in axes.flat[len(c):]:
        ax.axis("off")
    rot = [f"até {CORTES[0]}"] + [f"{a + 1}–{b}" for a, b in zip(CORTES[:-1], CORTES[1:],
                                                                    strict=True)]
    leg = [Patch(facecolor=cor, label=t) for cor, t in zip(CORES, rot, strict=True)]
    leg.append(plt.Line2D([], [], color=TINTA2, linewidth=0.8,
                          label=f"máscara {CFG['ano_mascara_ref']} (+{CFG['buffer_m']} m)"))
    fig.legend(handles=leg, loc="lower center", ncol=len(leg), frameon=False, fontsize=9,
               title="área urbanizada pela primeira vez (MapBiomas C11, classe 24)",
               title_fontsize=9, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(f"Mancha urbana dos polos do Matopiba, 1985–2025 (janelas de "
                 f"{2 * MEIA_JANELA_KM} km em torno da sede)", x=0.01, ha="left", fontsize=13,
                 color=TINTA)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97), h_pad=3.5)
    fig.savefig(path("figuras") / "s04b_mancha_urbana_cidades.png", dpi=200,
                facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return pd.DataFrame(linhas)


def figura_regiao() -> None:
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")
    p = pd.read_parquet(path("processed") / "painel_municipio.parquet",
                        columns=["id_municipio", "ano", "area_urbano_ha"])
    w = p[p["ano"].isin([2000, 2025])].pivot_table(index="id_municipio", columns="ano",
                                                     values="area_urbano_ha")
    g = malha[malha["grupo"].isin(CFG["grupos"])].merge(
        (w[2025] / w[2000]).rename("razao").reset_index(), how="left")
    g = g.to_crs(settings()["crs_area"])
    faixas = [0, 1.25, 1.5, 2, 3, np.inf]
    rot = ["< 1,25×", "1,25–1,5×", "1,5–2×", "2–3×", "≥ 3×"]
    cores = ["#dbe8f8", "#a9c9ef", "#6ea3e3", "#2a78d6", "#0b3a75"]
    g["faixa"] = pd.cut(g["razao"], faixas, labels=False, right=False)
    fig, ax = plt.subplots(figsize=(9, 10))
    for i, cor in enumerate(cores):
        g[g["faixa"] == i].plot(ax=ax, color=cor, edgecolor="white", linewidth=0.15)
    g[g["faixa"].isna()].plot(ax=ax, color=FUNDO, edgecolor="white", linewidth=0.15)
    g[g["grupo"] == "matopiba"].dissolve().boundary.plot(ax=ax, color=TINTA, linewidth=1.1)
    ax.set_axis_off()
    leg = [Patch(facecolor=c, label=t) for c, t in zip(cores, rot, strict=True)]
    leg.append(plt.Line2D([], [], color=TINTA, linewidth=1.1, label="limite do Matopiba"))
    ax.legend(handles=leg, loc="lower left", frameon=False, fontsize=9,
              title="área urbanizada 2025 ÷ 2000", title_fontsize=9)
    ax.set_title("Crescimento da área urbanizada, 2000→2025 (MapBiomas C11): Matopiba e "
                 "Cerrado fora", loc="left", fontsize=12, color=TINTA)
    fig.savefig(path("figuras") / "s04b_mancha_urbana_regiao.png", dpi=200,
                facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ee = ee_init()
    t = figura_cidades(ee)
    figura_regiao()
    print(t.round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
