"""Etapa 8.1: descritiva.

Saídas:
  outputs/figuras/s08_mapas_expansao.png        participação da agricultura temporária por década
  outputs/figuras/s08_trajetorias.png           desfechos: tratados vs. nunca tratados
  outputs/tabelas/s08_medias_pre_tratamento.{csv,tex}

Uso: python -m matopiba.s08_descritiva
"""

import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from scipy import stats

from matopiba.analise import DESFECHOS, amostra_did, carregar, preparar_desfecho, salvar_tabela
from matopiba.config import path, settings

CRS = settings()["crs_area"]
ANO_REF = 2000
# rampa sequencial azul (paleta de referência), do mais claro ao mais escuro
RAMPA = ["#e9f2fd", "#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
CORES = {"matopiba_tratado": "#2a78d6", "cerrado_tratado": "#eb6834",
         "nunca_tratado": "#8a897f"}
ROTULOS = {"matopiba_tratado": "Matopiba, tratados", "cerrado_tratado": "Cerrado fora, tratados",
           "nunca_tratado": "Nunca tratados (Matopiba + Cerrado fora)"}
TINTA, TINTA2, GRADE = "#1c1c1a", "#5f5e5a", "#e4e3df"


def _estilo(ax):
    ax.grid(axis="y", color=GRADE, linewidth=0.6)
    for lado in ["top", "right"]:
        ax.spines[lado].set_visible(False)
    for lado in ["left", "bottom"]:
        ax.spines[lado].set_color("#a8a79f")
    ax.tick_params(colors=TINTA2, labelsize=8)


def mapas(p: pd.DataFrame) -> None:
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet").to_crs(CRS)
    mat = malha[malha["grupo"] == "matopiba"]
    contorno = mat.union_all()
    xmin, ymin, xmax, ymax = contorno.bounds
    pad = 0.12 * max(xmax - xmin, ymax - ymin)
    caixa = (xmin - pad, ymin - pad, xmax + pad, ymax + pad)
    viz = malha.cx[caixa[0]:caixa[2], caixa[1]:caixa[3]].copy()
    viz["geometry"] = viz.geometry.simplify(800)
    ufs = malha.dissolve("abbrev_state").geometry.simplify(800)
    anos = [1985, 1995, 2005, 2015, 2025]
    limites = [0, 0.01, 0.025, 0.05, 0.10, 0.20, 0.35, 1.0]
    cmap = ListedColormap(RAMPA)
    norm = BoundaryNorm(limites, cmap.N)
    fig, axes = plt.subplots(1, len(anos), figsize=(16, 5.2))
    for ax, a in zip(axes, anos, strict=True):
        v = viz.merge(p.loc[p["ano"] == a, ["id_municipio", "share_agri_temp"]],
                      on="id_municipio", how="left")
        v.plot(ax=ax, column="share_agri_temp", cmap=cmap, norm=norm, linewidth=0,
               missing_kwds={"color": "#f2f1ee"})
        ufs.boundary.plot(ax=ax, color="#a8a79f", linewidth=0.4)
        gpd.GeoSeries([contorno.simplify(800)], crs=CRS).boundary.plot(ax=ax, color=TINTA,
                                                                      linewidth=0.9)
        ax.set_xlim(caixa[0], caixa[2])
        ax.set_ylim(caixa[1], caixa[3])
        ax.set_axis_off()
        media = v.loc[v["grupo"] == "matopiba", "share_agri_temp"].mean()
        ax.set_title(f"{a}\nmédia no Matopiba: {media:.1%}", fontsize=10, color=TINTA,
                     loc="left")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=axes, orientation="horizontal", fraction=0.05, pad=0.04,
                      aspect=60, ticks=limites[:-1])
    cb.ax.set_xticklabels(["0", "1%", "2,5%", "5%", "10%", "20%", "35%+"])
    cb.ax.tick_params(labelsize=8, colors=TINTA2)
    cb.set_label("Participação da agricultura temporária na área do município "
                 "(soja, arroz, algodão e outras)", fontsize=9, color=TINTA2)
    fig.suptitle("Expansão da agricultura temporária no Matopiba (contorno preto), 1985–2025",
                 x=0.01, ha="left", fontsize=13, color=TINTA)
    fig.text(0.01, 0.01, "Fonte: MapBiomas Coleção 11.", fontsize=8, color=TINTA2)
    fig.savefig(path("figuras") / "s08_mapas_expansao.png", dpi=200, facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def _categoria(s: pd.DataFrame) -> pd.Series:
    trat = s["coorte"].notna()
    return np.select([trat & (s["grupo"] == "matopiba"), trat, ~trat],
                     ["matopiba_tratado", "cerrado_tratado", "nunca_tratado"], default="")


def trajetorias(s: pd.DataFrame) -> None:
    s = s.assign(cat=_categoria(s))
    fig, axes = plt.subplots(1, len(DESFECHOS), figsize=(3.4 * len(DESFECHOS), 4.2))
    for ax, d in zip(axes, DESFECHOS, strict=True):
        y = preparar_desfecho(s, d)
        m = s.assign(y=y).dropna(subset=["y"]).groupby(["cat", "ano"])["y"].mean()
        for c in ["nunca_tratado", "cerrado_tratado", "matopiba_tratado"]:
            if c in m.index.get_level_values(0):
                serie = m.loc[c]
                ax.plot(serie.index, serie.values, color=CORES[c], linewidth=2,
                        marker="o" if d.so_anos_impares else None, markersize=3,
                        label=ROTULOS[c])
        ax.set_title(d.rotulo, fontsize=10, color=TINTA, loc="left")
        _estilo(ax)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    n = s.drop_duplicates("unidade").assign(cat=lambda x: _categoria(x))["cat"].value_counts()
    fig.suptitle("Trajetórias médias dos desfechos por grupo de tratamento "
                 f"(agricultura temporária >= {settings()['tratamento']['limiar_padrao']:.0%})",
                 x=0.01, ha="left", fontsize=12, color=TINTA)
    fig.text(0.01, -0.02, "Municípios: " + "; ".join(f"{ROTULOS[k]} = {v}"
                                                      for k, v in n.items())
             + ". Médias simples entre municípios.", fontsize=8, color=TINTA2)
    fig.tight_layout()
    fig.savefig(path("figuras") / "s08_trajetorias.png", dpi=200, facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def medias_pre(s: pd.DataFrame) -> pd.DataFrame:
    """Médias em 2000 (PIB em 2002): coortes tratadas depois de 2000 vs. nunca tratados."""
    at = pd.read_parquet(path("interim") / "socio_atlas.parquet").query("ano == 2000")
    base = s.drop_duplicates("unidade")[["unidade", "coorte", "grupo"]]
    # só coortes que entram depois do ano de referência, para que 2000 seja pré-tratamento
    base = base[base["coorte"].isna() | (base["coorte"] > ANO_REF)]
    base["tratado"] = base["coorte"].notna()
    vars_ = [("share_agri_temp", 2000, "Agricultura temporária (% área)", 100),
             ("share_soja", 2000, "Soja (% área)", 100),
             ("share_nativa", 2000, "Vegetação nativa (% área)", 100),
             ("share_pasto", 2000, "Pastagem (% área)", 100),
             ("populacao", 2000, "População", 1),
             ("pib_pc_real", 2002, "PIB per capita (R$ de 2023, 2002)", 1),
             ("luz_pc", 2000, "Luzes per capita", 1),
             ("vinculos_pc", 2000, "Emprego formal por habitante", 1),
             ("tmi", 2000, "Mortalidade infantil (por mil)", 1),
             ("ganho_tecnologico", 2000, "Ganho tecnológico GAEZ (t/ha)", 1)]
    linhas = []
    for col, ano, rot, esc in vars_:
        v = s.loc[s["ano"] == ano, ["unidade", col]].merge(base, on="unidade")
        linhas.append(_comparar(v, col, rot, esc))
    for col, rot, esc in [("idhm", "IDHM (2000)", 1), ("renda_pc", "Renda per capita (Atlas, "
                                                                     "2000)", 1),
                          ("prop_pobreza", "% de pobres (Atlas, 2000)", 1),
                          ("indice_gini", "Gini da renda (Atlas, 2000)", 1)]:
        v = at[["id_municipio", col]].rename(columns={"id_municipio": "unidade"}).merge(
            base, on="unidade")
        linhas.append(_comparar(v, col, rot, esc))
    return pd.DataFrame(linhas)


def _comparar(v: pd.DataFrame, col: str, rot: str, esc: float) -> dict:
    t, c = v.loc[v["tratado"], col].dropna() * esc, v.loc[~v["tratado"], col].dropna() * esc
    tt = stats.ttest_ind(t, c, equal_var=False)
    return {"variável": rot, "tratados": t.mean(), "nunca tratados": c.mean(),
            "diferença": t.mean() - c.mean(), "p (Welch)": tt.pvalue,
            "n tratados": len(t), "n controles": len(c)}


def main() -> int:
    p = carregar()
    mapas(p)
    s = amostra_did(p)
    trajetorias(s)
    tab = medias_pre(s)
    salvar_tabela(tab, "s08_medias_pre_tratamento",
                  "Médias pré-tratamento (2000; PIB em 2002): municípios que cruzam 10% de "
                  "agricultura temporária depois de 2000 vs. nunca tratados "
                  "(Matopiba + Cerrado fora)")
    print(tab.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
