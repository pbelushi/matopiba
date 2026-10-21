"""Etapa 3: luzes noturnas por município e ano (Earth Engine).

Série principal (`luz_soma`, `luz_media`): VIIRS anual oficial a partir de 2013 e, antes, o
Li-DMSP intercalibrado (Li et al., 2020) encadeado pela taxa de crescimento em 2013. As séries
DMSP-OLS V4, VIIRS, Li-DMSP e VIIRS-like de Chen et al. (2021) também são salvas, para
comparação e robustez. Resultados zonais ficam em cache; use --refazer para recalcular.

Saídas:
  data/interim/luzes_mun_ano.parquet      painel município × ano
  outputs/figuras/s03_dmsp_viirs.png      DMSP vs. VIIRS na sobreposição
  outputs/logs/s03_luzes.md               resultado dos testes de aceite

Uso: python -m matopiba.s03_luzes
"""

import json
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely

from matopiba.config import path, settings
from matopiba.gcp import bq_query, ee_init

CFG = settings()["luzes"]
CRS_AREA = settings()["crs_area"]


def feicoes(ee, malha: gpd.GeoDataFrame, max_bytes: int):
    """Municípios simplificados (as luzes têm pixels de 0,5–1 km) em lotes de FeatureCollection.

    Os lotes são fechados pelo tamanho do GeoJSON, porque o EE limita cada requisição a 10 MB.
    """
    g = malha[["id_municipio", "geometry"]].to_crs(CRS_AREA)
    g["geometry"] = g.geometry.simplify(CFG["simplificar_m"])
    g = g.to_crs(4326)
    g["geometry"] = shapely.set_precision(g.geometry.values, 1e-5)
    lote, tamanho = [], 0
    for mid, geom in zip(g["id_municipio"], g.geometry, strict=True):
        gj = geom.__geo_interface__
        n = len(json.dumps(gj))
        if lote and tamanho + n > max_bytes:
            yield ee.FeatureCollection(lote)
            lote, tamanho = [], 0
        lote.append(ee.Feature(ee.Geometry(gj), {"id_municipio": mid}))
        tamanho += n
    if lote:
        yield ee.FeatureCollection(lote)


def mascara_agua(ee):
    """1 onde o pixel de 30 m não é água no MapBiomas (classe 33) do ano de referência."""
    mb = ee.Image(settings()["mapbiomas"]["ee_asset"])
    return mb.select(f"classification_{CFG['ano_mascara_agua']}").neq(33)


def empilhar(ee, produto: str):
    """Imagem multibanda com uma banda por ano (nome = ano) e a escala nativa do produto."""
    p = CFG["produtos"][produto]
    ic = ee.ImageCollection(p["id"])
    if p.get("ids_extra"):
        for extra in p["ids_extra"]:
            ic = ic.merge(ee.ImageCollection(extra))
    anos = list(range(p["anos"][0], p["anos"][1] + 1))
    bandas = []
    for a in anos:
        img = (
            ic.filterDate(f"{a}-01-01", f"{a + 1}-01-01")
            .select(p["banda"])
            .mean()  # DMSP: média entre satélites no mesmo ano
            .max(0)
            .rename(str(a))
        )
        bandas.append(img)
    escala = ic.first().projection().nominalScale().getInfo()
    proj = ic.first().projection().atScale(escala)
    # fração de água no pixel de luz; descarta pixels com mais de metade de água
    agua_ok = (
        mascara_agua(ee).reduceResolution(ee.Reducer.mean(), maxPixels=2048)
        .reproject(proj).gte(0.5)
    )
    return ee.Image.cat(bandas).updateMask(agua_ok).setDefaultProjection(proj), anos, escala


def zonal(ee, malha, produto: str, refazer: bool) -> pd.DataFrame:
    cache = path("interim") / f"_cache_luzes_{produto}.parquet"
    if cache.exists() and not refazer:
        print(f"  {produto}: lido do cache {cache.name}")
        return pd.read_parquet(cache)
    img, anos, escala = empilhar(ee, produto)
    reducer = ee.Reducer.sum().combine(ee.Reducer.mean(), sharedInputs=True)
    linhas = []
    for fc in feicoes(ee, malha, CFG["lote_bytes"]):
        res = img.reduceRegions(fc, reducer, scale=escala, tileScale=4).getInfo()
        for f in res["features"]:
            pr = f["properties"]
            for a in anos:
                linhas.append((pr["id_municipio"], a, pr.get(f"{a}_sum"), pr.get(f"{a}_mean")))
    df = pd.DataFrame(linhas, columns=["id_municipio", "ano", f"{produto}_soma",
                                       f"{produto}_media"])
    print(f"  {produto}: {df['id_municipio'].nunique()} municípios, anos {anos[0]}–{anos[-1]}")
    df.to_parquet(cache, index=False)
    return df


def encadear(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Série principal: VIIRS oficial a partir do ano de encadeamento; antes dele, o nível do
    VIIRS no ano de encadeamento vezes o crescimento do Li-DMSP em cada município.

    Encadear pela taxa de crescimento evita a quebra de nível entre sensores.
    """
    t0 = CFG["ano_encadeamento"]
    base = df[df["ano"] == t0].set_index("id_municipio")
    df["luz_soma"] = df["viirs_soma"].where(df["ano"] >= t0)
    df["luz_media"] = df["viirs_media"].where(df["ano"] >= t0)
    df["fonte_luz"] = np.where(df["ano"] >= t0, "viirs", None)
    antes = df["ano"] < t0
    # Municípios muito escuros: o DMSP oscila em torno do limiar e pode zerar no ano-base.
    # Nesse caso a base do Li passa a ser a média de 5 anos até t0 e, se ainda zero, a média
    # de toda a série; se o Li é zero em todos os anos, a razão é zero.
    li = df.pivot_table(index="id_municipio", columns="ano", values="li_dmsp_soma")
    base_li = li[t0].where(li[t0] > 0, li.loc[:, t0 - 4:t0].mean(axis=1))
    base_li = base_li.where(base_li > 0, li.mean(axis=1))
    li_t0 = df.loc[antes, "id_municipio"].map(base_li)
    viirs_t0 = df.loc[antes, "id_municipio"].map(base["viirs_soma"])
    viirs_med_t0 = df.loc[antes, "id_municipio"].map(base["viirs_media"])
    razao = (df.loc[antes, "li_dmsp_soma"] / li_t0).where(li_t0 > 0, 0.0)
    df.loc[antes, "luz_soma"] = viirs_t0 * razao
    df.loc[antes, "luz_media"] = viirs_med_t0 * razao
    df.loc[antes, "fonte_luz"] = "li_dmsp_encadeado"
    sem_base = base.index[(base["li_dmsp_soma"] == 0) | (base["viirs_soma"] == 0)]
    df["flag_luz_base_zero"] = df["id_municipio"].isin(sem_base)
    return df, {"ano": t0, "n_sem_base": len(sem_base),
                "n_nan": int(df.loc[antes, "luz_soma"].isna().sum())}


def pib_corte(ano: int) -> pd.DataFrame:
    sql = f"""
    SELECT id_municipio, pib
    FROM `basedosdados.br_ibge_pib.municipio`
    WHERE ano = {ano}
    """
    return bq_query(sql, max_gb=0.1)


def ultimo_ano_pib() -> int:
    sql = "SELECT MAX(ano) AS ano FROM `basedosdados.br_ibge_pib.municipio`"
    return int(bq_query(sql, max_gb=0.1)["ano"].iloc[0])


def figura(df: pd.DataFrame, universo: pd.DataFrame, saida) -> None:
    ano = CFG["ano_sobreposicao"]
    d = df[df["ano"] == ano].merge(universo[["id_municipio", "grupo"]])
    d = d[(d["dmsp_soma"] > 0) & (d["viirs_soma"] > 0)]
    cores = {"outros": "#c3c2b7", "cerrado_fora": "#eb6834", "matopiba": "#2a78d6"}
    rot = {"outros": "Outros", "cerrado_fora": "Cerrado fora do Matopiba",
           "matopiba": "Matopiba"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    for g in ["outros", "cerrado_fora", "matopiba"]:
        s = d[d["grupo"] == g]
        axes[0].scatter(s["dmsp_soma"], s["viirs_soma"], s=8, color=cores[g], alpha=0.7,
                        linewidths=0, label=rot[g])
    axes[0].set_xscale("log")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("DMSP-OLS: soma de DN (stable_lights)")
    axes[0].set_ylabel("VIIRS: soma de radiância (nW/cm²/sr)")
    rho = np.corrcoef(np.log(d["dmsp_soma"]), np.log(d["viirs_soma"]))[0, 1]
    axes[0].set_title(f"Municípios em {ano} (correlação log-log {rho:.2f})", loc="left",
                      fontsize=11)
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")

    agg = df.merge(universo[["id_municipio", "grupo"]]).query("grupo == 'matopiba'")
    series = {"dmsp_soma": ("DMSP-OLS V4", "#6250d6"),
              "li_dmsp_soma": ("Li-DMSP intercalibrado", "#eda100"),
              "viirs_soma": ("VIIRS anual", "#1baf7a"),
              "chen_soma": ("VIIRS-like (Chen), robustez", "#2a78d6")}
    agg = agg.groupby("ano")[list(series)].sum(min_count=1)
    for col, (nome, cor) in series.items():
        s = agg[col].dropna()
        s = s / s.loc[ano] * 100
        axes[1].plot(s.index, s.values, color=cor, linewidth=2, label=nome)
    axes[1].axvline(ano, color="#a8a79f", linewidth=0.8, linestyle="--")
    axes[1].set_ylabel(f"Soma no Matopiba (índice, {ano} = 100)")
    axes[1].set_title("Séries agregadas no Matopiba", loc="left", fontsize=11)
    axes[1].legend(frameon=False, fontsize=9, loc="upper left")
    for ax in axes:
        ax.grid(color="#e4e3df", linewidth=0.6)
        for lado in ["top", "right"]:
            ax.spines[lado].set_visible(False)
    fig.suptitle("Luzes noturnas: DMSP-OLS vs. VIIRS na sobreposição", x=0.01, ha="left",
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(saida, dpi=200, facecolor="white")
    plt.close(fig)


def main() -> int:
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")
    ee = ee_init()

    refazer = "--refazer" in sys.argv
    partes = [zonal(ee, malha, p, refazer) for p in CFG["produtos"]]
    df = partes[0]
    for p in partes[1:]:
        df = df.merge(p, on=["id_municipio", "ano"], how="outer")
    df, enc = encadear(df)
    df = df.sort_values(["id_municipio", "ano"]).reset_index(drop=True)
    df.to_parquet(path("interim") / "luzes_mun_ano.parquet", index=False)
    figura(df, universo, path("figuras") / "s03_dmsp_viirs.png")

    # --- aceite ---
    ids = set(universo["id_municipio"])
    faltas = {}
    for col in ["luz_soma", "li_dmsp_soma", "dmsp_soma", "viirs_soma", "chen_soma"]:
        d = df.dropna(subset=[col])
        anos = sorted(d["ano"].unique())
        por_ano = d.groupby("ano")["id_municipio"].nunique()
        faltas[col] = (anos[0], anos[-1], int((len(ids) - por_ano).max()),
                       sorted(ids - set(d["id_municipio"])))
    ano_pib = ultimo_ano_pib()
    pib = pib_corte(ano_pib)
    c = df[df["ano"] == ano_pib].merge(pib, on="id_municipio")
    c = c[(c["luz_soma"] > 0) & (c["pib"] > 0)]
    rho = np.corrcoef(np.log(c["luz_soma"]), np.log(c["pib"]))[0, 1]
    sem_falta = all(v[2] == 0 for v in faltas.values())
    testes = {
        "Sem municípios faltando nos anos cobertos: " + "; ".join(
            f"{k} {v[0]}–{v[1]} (máx. faltando num ano: {v[2]}, sempre ausentes: {v[3]})"
            for k, v in faltas.items()
        ): sem_falta,
        f"Correlação positiva luzes × PIB municipal em {ano_pib} (log-log, n={len(c)}): "
        f"{rho:.3f}": rho > 0,
    }
    info = [
        f"Série principal encadeada em {enc['ano']}: VIIRS oficial a partir de {enc['ano']}; "
        f"antes, VIIRS({enc['ano']}) × Li-DMSP(t)/Li-DMSP({enc['ano']}) por município",
        f"Municípios com Li-DMSP ou VIIRS zerado no ano-base (flag_luz_base_zero): "
        f"{enc['n_sem_base']}; valores pré-{enc['ano']} indefinidos (NaN): {enc['n_nan']}",
        "Chen (VIIRS-like) mantido só como robustez: quebra de nível de ~3,5× entre 2010 e "
        "2013, maior no Matopiba (ver docs/DECISOES.md)",
        f"Fonte da série principal por ano: "
        f"{df.groupby('fonte_luz')['ano'].agg(['min', 'max']).to_dict('index')}",
        f"Máscara de água: pixels com >= 50% de água (MapBiomas classe 33, "
        f"{CFG['ano_mascara_agua']}) descartados",
    ]
    linhas = ["# Etapa 3 — luzes noturnas: aceite", ""]
    linhas += [f"- [{'OK' if ok else 'FALHA'}] {t}" for t, ok in testes.items()]
    linhas += ["", "## Informações", ""] + [f"- {i}" for i in info]
    texto = "\n".join(linhas) + "\n"
    (path("logs") / "s03_luzes.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(testes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
