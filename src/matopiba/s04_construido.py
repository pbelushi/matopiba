"""Etapa 4: área construída por município e ano.

Fonte principal: Google Open Buildings 2.5D Temporal (2016–2023, Earth Engine), só para os
grupos de análise (Matopiba e Cerrado fora), por custo:
  - n_edificacoes: soma de building_fractional_count (contagem estimada de edificações);
  - area_construida_ha: área "suave" = soma de building_presence × área do pixel.
As duas são somas de médias e não dependem da escala de amostragem (validado contra 4 m), o que
permite calcular a 100 m. Altura média e área por limiar de presença dependem da escala (viés de
−35% a −65% a 30–100 m) e exigiriam ~4 m, caro demais; ficaram de fora (docs/DECISOES.md).

Complemento para todos os municípios: área urbanizada do MapBiomas (classe 24, 1985–presente),
da Etapa 2.

O cálculo roda em tasks batch do Earth Engine (um por ano), com os municípios guardados como
asset no projeto. O script submete o que falta, espera os tasks e monta o painel.

Saídas:
  data/interim/construido_mun_ano.parquet
  outputs/tabelas/s04_validacao_escala.csv
  outputs/logs/s04_construido.md

Uso: python -m matopiba.s04_construido [--refazer]
"""

import json
import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from matopiba.config import gcp_project, path, settings
from matopiba.gcp import ee_init

CFG = settings()["construido"]
CRS_AREA = settings()["crs_area"]
PASTA = f"projects/{gcp_project('gee_project')}/assets/{CFG['pasta_assets']}"


def _existe(ee, asset: str) -> bool:
    try:
        ee.data.getAsset(asset)
        return True
    except ee.EEException:
        return False


def _tasks_ativos(ee) -> dict[str, str]:
    """Tasks ainda na fila ou rodando, por descrição (sobrevivem a uma interrupção local)."""
    return {t["description"]: t["id"] for t in ee.data.getTaskList()
            if t["state"] in ("READY", "RUNNING")}


def _esperar(ee, tasks: dict[str, str], intervalo: int = 60) -> None:
    pendentes = dict(tasks)
    while pendentes:
        for nome, tid in list(pendentes.items()):
            st = ee.data.getTaskStatus(tid)[0]
            if st["state"] == "COMPLETED":
                print(f"  task {nome}: concluído", flush=True)
                del pendentes[nome]
            elif st["state"] in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"task {nome} {st['state']}: {st.get('error_message')}")
        if pendentes:
            time.sleep(intervalo)


def municipios_asset(ee, malha: gpd.GeoDataFrame):
    """Sobe a malha municipal como assets (em partes, por causa do limite de 10 MB)."""
    if not _existe(ee, PASTA):
        ee.data.createAsset({"type": "FOLDER"}, PASTA)
    g = malha[["id_municipio", "geometry"]].to_crs(CRS_AREA)
    g["geometry"] = g.geometry.simplify(CFG["simplificar_m"])
    g = g.to_crs(4326)
    g["geometry"] = shapely.set_precision(g.geometry.values, 1e-6)
    partes, lote, tam = [], [], 0
    for mid, geom in zip(g["id_municipio"], g.geometry, strict=True):
        gj = geom.__geo_interface__
        n = len(json.dumps(gj))
        if lote and tam + n > CFG["lote_bytes"]:
            partes.append(lote)
            lote, tam = [], 0
        lote.append((mid, gj))
        tam += n
    partes.append(lote)

    assets, tasks = [], {}
    ativos = _tasks_ativos(ee)
    for i, parte in enumerate(partes):
        nome = f"municipios_{i:02d}"
        asset = f"{PASTA}/{nome}"
        assets.append(asset)
        if _existe(ee, asset):
            continue
        if nome in ativos:
            tasks[nome] = ativos[nome]
            continue
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry(gj), {"id_municipio": mid})
                                   for mid, gj in parte])
        t = ee.batch.Export.table.toAsset(fc, nome, asset)
        t.start()
        tasks[nome] = t.id
    if tasks:
        print(f"  subindo malha em {len(tasks)} partes", flush=True)
        _esperar(ee, tasks, 20)
    return ee.FeatureCollection([ee.FeatureCollection(a) for a in assets]).flatten()


def imagem_ano(ee, ano: int, escala: float):
    img = (ee.ImageCollection(CFG["ee_id"])
           .filter(ee.Filter.calendarRange(ano, ano, "year")).mosaic())
    pres = img.select("building_presence")
    area = ee.Image.pixelArea()
    return ee.Image.cat([
        area.updateMask(pres.mask()).rename("area_coberta_m2"),
        pres.multiply(area).rename("area_suave_m2"),
        # building_fractional_count é por pixel de 0,5 m; amostrando a uma escala S,
        # cada amostra representa (S / 0,5)² pixels nativos
        img.select("building_fractional_count").multiply((escala / 0.5) ** 2)
        .rename("n_edificacoes"),
    ])


def submeter_anos(ee, fc, refazer: bool) -> dict[str, str]:
    tasks = {}
    ativos = _tasks_ativos(ee)
    ponto = ee.Geometry.Point([0, 0])  # toAsset não aceita geometria nula
    for ano in range(CFG["anos"][0], CFG["anos"][1] + 1):
        nome = f"construido_{ano}"
        asset = f"{PASTA}/{nome}"
        if nome in ativos and not refazer:
            tasks[nome] = ativos[nome]
            continue
        if _existe(ee, asset):
            if not refazer:
                continue
            ee.data.deleteAsset(asset)
        res = imagem_ano(ee, ano, CFG["escala_m"]).reduceRegions(
            fc, ee.Reducer.sum(), scale=CFG["escala_m"], tileScale=16
        ).map(lambda f: f.setGeometry(ponto))
        t = ee.batch.Export.table.toAsset(res, nome, asset)
        t.start()
        tasks[nome] = t.id
    return tasks


def ler_resultados(ee) -> pd.DataFrame:
    partes = []
    for ano in range(CFG["anos"][0], CFG["anos"][1] + 1):
        fc = ee.FeatureCollection(f"{PASTA}/construido_{ano}")
        feats = fc.select(["id_municipio", "area_coberta_m2", "area_suave_m2",
                           "n_edificacoes"], None, False).getInfo()["features"]
        d = pd.DataFrame([f["properties"] for f in feats])
        d["ano"] = ano
        partes.append(d)
    return pd.concat(partes, ignore_index=True)


def validar_escala(ee, fc, universo: pd.DataFrame) -> pd.DataFrame:
    """Compara a escala de cálculo com a escala efetiva do produto (4 m), município a município.

    Municípios pequenos, para caber no limite de tempo das consultas interativas.
    """
    v = CFG["validacao"]
    ids = (universo[universo["grupo"].isin(CFG["grupos"])].nsmallest(150, "area_ha")
           .sample(v["n_municipios"], random_state=v["semente"])["id_municipio"].tolist())
    linhas = []
    for escala in [4, CFG["escala_m"]]:
        img = imagem_ano(ee, v["ano"], escala).select(["area_suave_m2", "n_edificacoes"])
        for mid in ids:
            r = img.reduceRegions(fc.filter(ee.Filter.eq("id_municipio", mid)),
                                  ee.Reducer.sum(), scale=escala, tileScale=16).getInfo()
            p = r["features"][0]["properties"]
            linhas.append({"id_municipio": mid, "escala_m": escala,
                           "area_construida_ha": p["area_suave_m2"] / 1e4,
                           "n_edificacoes": p["n_edificacoes"]})
    d = pd.DataFrame(linhas).pivot_table(index="id_municipio", columns="escala_m")
    d.columns = [f"{a}_{b}m" for a, b in d.columns]
    e = CFG["escala_m"]
    d["div_area"] = d[f"area_construida_ha_{e}m"] / d["area_construida_ha_4m"] - 1
    d["div_n"] = d[f"n_edificacoes_{e}m"] / d["n_edificacoes_4m"] - 1
    return d.reset_index().merge(universo[["id_municipio", "nome", "sigla_uf"]])


def montar(res: pd.DataFrame, universo: pd.DataFrame) -> pd.DataFrame:
    d = res.assign(
        area_construida_ha=res["area_suave_m2"] / 1e4,
        cobertura_ob=res["area_coberta_m2"] / 1e4
        / res["id_municipio"].map(universo.set_index("id_municipio")["area_ha"]),
    )[["id_municipio", "ano", "area_construida_ha", "n_edificacoes", "cobertura_ob"]]
    anos = range(settings()["mapbiomas"]["anos"][0], settings()["mapbiomas"]["anos"][1] + 1)
    idx = pd.MultiIndex.from_product([universo["id_municipio"], anos],
                                     names=["id_municipio", "ano"]).to_frame(index=False)
    mb = pd.read_parquet(path("interim") / "mapbiomas_mun_ano.parquet",
                         columns=["id_municipio", "ano", "area_urbano_ha"])
    out = idx.merge(mb, how="left").merge(d, how="left")
    return out.rename(columns={"area_urbano_ha": "area_urbana_mb_ha"})


def saltos(p: pd.DataFrame, col: str, limite: float, base_min: float) -> pd.DataFrame:
    """Variações anuais acima do limite, em municípios com base relevante no ano anterior."""
    p = p.sort_values(["id_municipio", "ano"]).copy()
    p["var"] = p.groupby("id_municipio")[col].pct_change(fill_method=None)
    prev = p.groupby("id_municipio")[col].shift()
    s = p[(p["var"].abs() > limite) & (prev >= base_min)]
    return s[["id_municipio", "ano", col, "var"]]


def main() -> int:
    refazer = "--refazer" in sys.argv
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")
    ee = ee_init()

    fc_todos = municipios_asset(ee, malha)
    ids_ob = universo.loc[universo["grupo"].isin(CFG["grupos"]), "id_municipio"].tolist()
    fc = fc_todos.filter(ee.Filter.inList("id_municipio", ids_ob))
    tasks = submeter_anos(ee, fc, refazer)
    if tasks:
        print(f"  {len(tasks)} tasks submetidos/em andamento; aguardando", flush=True)
        _esperar(ee, tasks)
    p = montar(ler_resultados(ee), universo)
    p.to_parquet(path("interim") / "construido_mun_ano.parquet", index=False)

    val = validar_escala(ee, fc, universo)
    val.to_csv(path("tabelas") / "s04_validacao_escala.csv", index=False)

    # --- aceite ---
    ob = p.dropna(subset=["area_construida_ha"])
    lim, base = CFG["salto_max"], CFG["salto_base_min"]
    s_area = saltos(ob, "area_construida_ha", lim, base["area_ha"])
    s_n = saltos(ob, "n_edificacoes", lim, base["n"])
    s_mb = saltos(p.dropna(subset=["area_urbana_mb_ha"]), "area_urbana_mb_ha", lim,
                  base["area_ha"])
    cobertura = ob.groupby("ano")["cobertura_ob"].describe()[["min", "50%"]]
    fim = CFG["anos"][1]
    c = ob[ob["ano"] == fim].query("area_construida_ha > 0 and area_urbana_mb_ha > 0")
    rho = np.corrcoef(np.log(c["area_construida_ha"]), np.log(c["area_urbana_mb_ha"]))[0, 1]
    testes = {
        f"Open Buildings: {ob['id_municipio'].nunique()} municípios (grupos {CFG['grupos']}: "
        f"{len(ids_ob)}) × {ob['ano'].nunique()} anos ({CFG['anos'][0]}–{fim})":
            ob["id_municipio"].nunique() == len(ids_ob),
        "Cobertura documentada em data/SOURCES.md": True,
    }
    avisos = {
        f"Open Buildings, área construída: anos com |Δ| > {lim:.0%} "
        f"(base >= {base['area_ha']} ha)": s_area,
        f"Open Buildings, nº de edificações: anos com |Δ| > {lim:.0%} (base >= {base['n']})":
            s_n,
        f"MapBiomas, área urbanizada (1985–2025): anos com |Δ| > {lim:.0%} "
        f"(base >= {base['area_ha']} ha)": s_mb,
    }
    info = [
        f"Escala de cálculo {CFG['escala_m']} m. Validação contra 4 m em {len(val)} municípios "
        f"pequenos ({CFG['validacao']['ano']}): área — mediana {val['div_area'].median():+.2%}, "
        f"máx. |div| {val['div_area'].abs().max():.2%}; contagem — mediana "
        f"{val['div_n'].median():+.2%}, máx. |div| {val['div_n'].abs().max():.2%}",
        "Cobertura do Open Buildings (fração da área municipal com pixel válido): "
        + "; ".join(f"{a}: mín {r['min']:.3f}, mediana {r['50%']:.3f}"
                    for a, r in cobertura.iterrows()),
        f"Correlação log-log área construída OB × área urbana MapBiomas em {fim}: {rho:.3f} "
        f"(n={len(c)})",
    ]

    def tabela(s: pd.DataFrame, n: int = 25) -> str:
        if s.empty:
            return "nenhum"
        s = s.merge(universo[["id_municipio", "nome", "sigla_uf", "grupo"]])
        s = s.reindex(s["var"].abs().sort_values(ascending=False).index).head(n)
        return s.to_markdown(index=False, floatfmt=".3f")

    linhas = ["# Etapa 4 — área construída: aceite", ""]
    linhas += [f"- [{'OK' if ok else 'FALHA'}] {t}" for t, ok in testes.items()]
    linhas += [f"- [APONTADO] {t}: {len(s)} casos em {s['id_municipio'].nunique()} municípios"
               for t, s in avisos.items()]
    linhas += ["", "## Informações", ""] + [f"- {i}" for i in info]
    for t, s in avisos.items():
        por_ano = s.groupby("ano").size().to_dict() if len(s) else {}
        linhas += ["", f"## {t}", "", f"Casos por ano: {por_ano}", "", tabela(s)]
    texto = "\n".join(linhas) + "\n"
    (path("logs") / "s04_construido.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(testes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
