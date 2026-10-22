"""Etapa 4b: máscara urbana fixa, luzes dentro e fora dela e edificações urbanas a 4 m.

1. Máscara urbana por município (asset de imagem no EE): pixels a até `buffer_m` de um pixel
   da classe 24 (área urbanizada) do MapBiomas C11, em 2000 e em 2012, calculada a 30 m na
   projeção Albers do projeto (distância isotrópica) e restrita aos grupos de análise. A
   máscara de 2012 também é vetorizada (um polígono por mancha, rotulado pelo município) para
   limitar as leituras do Open Buildings à área urbana.
2. Radiância VIIRS anual (2013–2025, `average_masked`, mesma máscara de água da Etapa 3)
   dentro e fora da máscara de 2012: cada pixel de luz é ponderado pela fração da sua área
   dentro da máscara, de modo que dentro + fora = soma total do município.
3. Open Buildings Temporal a 4 m dentro da máscara de 2012 (anos em `ob.anos_calculo`;
   hoje só 2016 e 2023, para diferenças longas): contagem de
   edificações, área construída (presença > limiar), área "suave" (presença × área) e altura
   média ponderada pela área. Por custo, primeiro roda um piloto com 10 municípios e estima os
   EECU-h; o cálculo completo só roda com `urbano.ob.confirmado: true` no settings.

Todos os cálculos são tasks batch com resultado salvo como asset em
projects/<gee_project>/assets/<pasta_assets>; assets existentes são reaproveitados
(--refazer recalcula as etapas 1 e 2).

Saídas:
  data/interim/urbano_mun_ano.parquet
  outputs/logs/s04b_urbano.md
  outputs/tabelas/s04b_piloto_ob.csv

Uso: python -m matopiba.s04b_urbano [--refazer]
"""

import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj

from matopiba.config import gcp_project, path, settings
from matopiba.gcp import ee_init
from matopiba.s03_luzes import empilhar
from matopiba.s04_construido import PASTA, _esperar, _existe, _tasks_ativos, municipios_asset

CFG = settings()["urbano"]
MB = settings()["mapbiomas"]
# o EE não lê WKT2; WKT1 funciona
ALBERS = pyproj.CRS(settings()["crs_area"]).to_wkt(version="WKT1_GDAL")
PONTO = [0, 0]  # toAsset não aceita geometria nula


def _asset(nome: str) -> str:
    return f"{PASTA}/{nome}"


def _eecu_h(ee, task_id: str) -> float | None:
    """EECU-hora consumidos por um task batch concluído."""
    try:
        op = ee.data.getOperation(f"projects/{gcp_project('gee_project')}/operations/{task_id}")
        s = op.get("metadata", {}).get("batchEecuUsageSeconds")
        return float(s) / 3600 if s is not None else None
    except Exception:  # noqa: BLE001 - informação auxiliar
        return None


def _submeter(ee, nome: str, fazer, refazer: bool = False) -> str | None:
    """Submete o task `nome` se o asset não existe (ou se refazer); devolve o id ou None."""
    asset = _asset(nome)
    ativos = _tasks_ativos(ee)
    if nome in ativos and not refazer:
        return ativos[nome]
    if _existe(ee, asset):
        if not refazer:
            return None
        ee.data.deleteAsset(asset)
    t = fazer(asset)
    t.start()
    print(f"  task {nome} submetido ({t.id})", flush=True)
    return t.id


def _rodar(ee, nome: str, fazer, refazer: bool, eecu: dict) -> None:
    tid = _submeter(ee, nome, fazer, refazer)
    if tid:
        _esperar(ee, {nome: tid}, 30)
        eecu[nome] = _eecu_h(ee, tid)
        print(f"  {nome}: {eecu[nome] or float('nan'):.2f} EECU-h", flush=True)


def _ler_fc(ee, nome: str, cols: list[str]) -> pd.DataFrame:
    feats = ee.FeatureCollection(_asset(nome)).select(cols, None, False).getInfo()["features"]
    return pd.DataFrame([f["properties"] for f in feats])


# ---------------------------------------------------------------- 1. máscara

def regiao(ee, malha: gpd.GeoDataFrame):
    x0, y0, x1, y1 = malha.total_bounds
    return ee.Geometry.Rectangle([float(x0), float(y0), float(x1), float(y1)], None, False)


def imagem_mascara(ee, fc):
    """Bandas m<ano> (1 = a até buffer_m de área urbana) e mun (código do município)."""
    mb = ee.Image(MB["ee_asset"])
    proj = ee.Projection(ALBERS).atScale(CFG["escala_mascara_m"])
    viz = int(np.ceil(CFG["buffer_m"] / CFG["escala_mascara_m"])) + 2
    mun = (fc.map(lambda f: f.set("cod", ee.Number.parse(f.get("id_municipio"))))
           .reduceToImage(["cod"], ee.Reducer.first()).reproject(proj).toInt32().rename("mun"))
    bandas = []
    for a in CFG["anos_mascara"]:
        urb = (mb.select(f"classification_{a}").remap(CFG["classes"], [1] * len(CFG["classes"]), 0)
               .reproject(proj))
        # distância (m) ao pixel urbano mais próximo, isotrópica na Albers
        dist = urb.fastDistanceTransform(viz, "pixels", "squared_euclidean").sqrt().multiply(
            CFG["escala_mascara_m"])
        bandas.append(dist.lte(CFG["buffer_m"]).toByte().rename(f"m{a}"))
    return ee.Image.cat([*bandas, mun]).updateMask(mun.mask())


def tarefa_mascara(ee, fc, reg):
    def fazer(asset):
        return ee.batch.Export.image.toAsset(
            imagem_mascara(ee, fc), CFG["asset_mascara"], asset, region=reg, crs=ALBERS,
            scale=CFG["escala_mascara_m"], maxPixels=1e11,
            pyramidingPolicy={"m2000": "mode", "m2012": "mode", "mun": "mode"})
    return fazer


def tarefa_poligonos(ee, reg):
    """Máscara de 2012 vetorizada: um polígono por mancha contígua, com o código do município."""
    def fazer(asset):
        img = ee.Image(_asset(CFG["asset_mascara"]))
        a = CFG["ano_mascara_ref"]
        rot = img.select("mun").updateMask(img.select(f"m{a}").eq(1))
        vet = rot.reduceToVectors(geometry=reg, crs=ALBERS, scale=CFG["escala_mascara_m"],
                                  geometryType="polygon", eightConnected=True,
                                  labelProperty="cod", maxPixels=1e11, tileScale=16)
        return ee.batch.Export.table.toAsset(vet, f"{CFG['asset_mascara']}_{a}_poligonos", asset)
    return fazer


def tarefa_area_mascara(ee, fc):
    def fazer(asset):
        img = ee.Image(_asset(CFG["asset_mascara"]))
        area = ee.Image.pixelArea()
        bandas = [img.select(f"m{a}").multiply(area).rename(f"area_m{a}_m2")
                  for a in CFG["anos_mascara"]]
        res = ee.Image.cat(bandas).reduceRegions(
            fc, ee.Reducer.sum(), crs=ALBERS, scale=CFG["escala_mascara_m"], tileScale=16
        ).map(lambda f: f.setGeometry(ee.Geometry.Point(PONTO)))
        return ee.batch.Export.table.toAsset(res, f"{CFG['asset_mascara']}_area", asset)
    return fazer


# ---------------------------------------------------------------- 2. luzes

def tarefa_viirs(ee, fc):
    """Soma de radiância VIIRS por ano: total, dentro e fora da máscara de 2012."""
    def fazer(asset):
        img, anos, escala = empilhar(ee, "viirs")
        proj = img.projection()
        a = CFG["ano_mascara_ref"]
        frac = (ee.Image(_asset(CFG["asset_mascara"])).select(f"m{a}").unmask(0)
                .reduceResolution(ee.Reducer.mean(), maxPixels=2048).reproject(proj))
        bandas = []
        for ano in anos:
            b = img.select(str(ano))
            bandas += [b.rename(f"t{ano}"), b.multiply(frac).rename(f"d{ano}"),
                       b.multiply(frac.multiply(-1).add(1)).rename(f"f{ano}")]
        res = ee.Image.cat(bandas).reduceRegions(
            fc, ee.Reducer.sum(), scale=escala, tileScale=4
        ).map(lambda f: f.setGeometry(ee.Geometry.Point(PONTO)))
        return ee.batch.Export.table.toAsset(res, "viirs_urbano", asset)
    return fazer


def ler_viirs(ee) -> pd.DataFrame:
    v = settings()["luzes"]["produtos"]["viirs"]
    anos = range(v["anos"][0], v["anos"][1] + 1)
    cols = ["id_municipio"] + [f"{k}{a}" for a in anos for k in "tdf"]
    d = _ler_fc(ee, "viirs_urbano", cols)
    out = []
    for a in anos:
        out.append(pd.DataFrame({"id_municipio": d["id_municipio"], "ano": a,
                                 "viirs_total_check": d[f"t{a}"],
                                 "viirs_urbano_soma": d[f"d{a}"],
                                 "viirs_fora_soma": d[f"f{a}"]}))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- 3. Open Buildings

def imagem_ob(ee, ano: int):
    ob = CFG["ob"]
    img = (ee.ImageCollection(settings()["construido"]["ee_id"])
           .filter(ee.Filter.calendarRange(ano, ano, "year")).mosaic())
    pres = img.select("building_presence")
    area = ee.Image.pixelArea()
    constr = pres.gt(ob["limiar_presenca"])
    return ee.Image.cat([
        # building_fractional_count é por pixel de 0,5 m (ver Etapa 4)
        img.select("building_fractional_count").multiply((ob["escala_m"] / 0.5) ** 2)
        .rename("n_edificacoes"),
        area.updateMask(constr).rename("area_limiar_m2"),
        pres.multiply(area).rename("area_suave_m2"),
        img.select("building_height").multiply(area).updateMask(constr).rename("volume_m3"),
        area.updateMask(pres.mask()).rename("area_coberta_m2"),
    ])


def tarefa_ob(ee, ano: int, cods: list[int] | None, nome: str):
    def fazer(asset):
        a = CFG["ano_mascara_ref"]
        pol = ee.FeatureCollection(_asset(f"{CFG['asset_mascara']}_{a}_poligonos"))
        if cods is not None:
            pol = pol.filter(ee.Filter.inList("cod", cods))
        msk = ee.Image(_asset(CFG["asset_mascara"])).select(f"m{a}").eq(1)
        res = imagem_ob(ee, ano).updateMask(msk).reduceRegions(
            pol, ee.Reducer.sum(), scale=CFG["ob"]["escala_m"], tileScale=16
        ).map(lambda f: f.setGeometry(ee.Geometry.Point(PONTO)))
        return ee.batch.Export.table.toAsset(res, nome, asset)
    return fazer


OB_COLS = ["cod", "n_edificacoes", "area_limiar_m2", "area_suave_m2", "volume_m3",
           "area_coberta_m2"]


def ler_ob(ee, nome: str) -> pd.DataFrame:
    """Soma os polígonos de cada município no servidor (o asset tem > 5000 feições, limite
    de uma consulta getInfo)."""
    met = OB_COLS[1:]
    g = ee.FeatureCollection(_asset(nome)).reduceColumns(
        ee.Reducer.sum().repeat(len(met)).group(groupField=0, groupName="cod"),
        ["cod", *met]).getInfo()["groups"]
    d = pd.DataFrame([{"cod": x["cod"], **dict(zip(met, x["sum"], strict=True))} for x in g])
    return pd.DataFrame({
        "id_municipio": d["cod"].astype("int64").astype(str),
        "n_edificacoes_urb": d["n_edificacoes"],
        "area_construida_urb_ha": d["area_limiar_m2"] / 1e4,
        "area_suave_urb_ha": d["area_suave_m2"] / 1e4,
        "volume_urb_m3": d["volume_m3"],
        "altura_media_urb_m": d["volume_m3"] / d["area_limiar_m2"].where(d["area_limiar_m2"] > 0),
        "area_coberta_ob_urb_ha": d["area_coberta_m2"] / 1e4,
    })


def amostra_piloto(area: pd.DataFrame) -> list[str]:
    """Um município por faixa de tamanho da máscara (decis), para a extrapolação por área."""
    p = CFG["ob"]["piloto"]
    a = area[area["area_mascara_ref_ha"] > 0].copy()
    a["faixa"] = pd.qcut(a["area_mascara_ref_ha"], p["n_municipios"], labels=False)
    return (a.groupby("faixa").sample(1, random_state=p["semente"])["id_municipio"].tolist())


def piloto(ee, area: pd.DataFrame, eecu: dict) -> dict:
    p = CFG["ob"]["piloto"]
    ids = amostra_piloto(area)
    nome = "ob_urbano_piloto"
    _rodar(ee, nome, tarefa_ob(ee, p["ano"], [int(i) for i in ids], nome), False, eecu)
    if eecu.get(nome) is None:   # asset de uma execução anterior: EECU registrado no CSV
        prev = path("tabelas") / "s04b_piloto_ob.csv"
        if prev.exists():
            eecu[nome] = pd.read_csv(prev)["eecu_h_piloto"].iloc[0]
    res = ler_ob(ee, nome).merge(area, on="id_municipio")
    area_pil = res["area_mascara_ref_ha"].sum()
    area_tot = area["area_mascara_ref_ha"].sum()
    n_anos = len(CFG["ob"]["anos_calculo"])
    est = eecu[nome] * area_tot / area_pil * n_anos if eecu.get(nome) else None
    res.assign(eecu_h_piloto=eecu.get(nome), area_mascara_piloto_ha=area_pil,
               area_mascara_total_ha=area_tot, eecu_h_estimado_total=est).to_csv(
        path("tabelas") / "s04b_piloto_ob.csv", index=False)
    return {"ids": ids, "eecu_h": eecu.get(nome), "area_piloto_ha": area_pil,
            "area_total_ha": area_tot, "n_anos": n_anos, "eecu_h_total": est}


# ---------------------------------------------------------------- painel e aceite

def main() -> int:
    refazer = "--refazer" in sys.argv
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")
    ids = universo.loc[universo["grupo"].isin(CFG["grupos"]), "id_municipio"].tolist()
    ee = ee_init()
    fc = municipios_asset(ee, malha).filter(ee.Filter.inList("id_municipio", ids))
    reg = regiao(ee, malha[malha["id_municipio"].isin(ids)])
    eecu: dict[str, float | None] = {}

    # 1. máscara (imagem), polígonos e área por município
    _rodar(ee, CFG["asset_mascara"], tarefa_mascara(ee, fc, reg), refazer, eecu)
    a = CFG["ano_mascara_ref"]
    _rodar(ee, f"{CFG['asset_mascara']}_{a}_poligonos", tarefa_poligonos(ee, reg), refazer,
           eecu)
    _rodar(ee, f"{CFG['asset_mascara']}_area", tarefa_area_mascara(ee, fc), refazer, eecu)
    area = _ler_fc(ee, f"{CFG['asset_mascara']}_area",
                   ["id_municipio"] + [f"area_m{x}_m2" for x in CFG["anos_mascara"]])
    for x in CFG["anos_mascara"]:
        area[f"area_mascara_{x}_ha"] = area.pop(f"area_m{x}_m2") / 1e4
    area["area_mascara_ref_ha"] = area[f"area_mascara_{a}_ha"]

    # 2. luzes dentro e fora
    _rodar(ee, "viirs_urbano", tarefa_viirs(ee, fc), refazer, eecu)
    vi = ler_viirs(ee)

    # 3. Open Buildings: completo se confirmado; senão, piloto e estimativa
    ob_cfg = CFG["ob"]
    anos_ob = ob_cfg["anos_calculo"]
    pil = piloto(ee, area, eecu)
    ob = None
    if ob_cfg["confirmado"]:
        tarefas = {}
        for ano in anos_ob:
            nome = f"ob_urbano_{ano}"
            tid = _submeter(ee, nome, tarefa_ob(ee, ano, None, nome))
            if tid:
                tarefas[nome] = tid
        if tarefas:
            _esperar(ee, tarefas)
            for nome, tid in tarefas.items():
                eecu[nome] = _eecu_h(ee, tid)
        ob = pd.concat([ler_ob(ee, f"ob_urbano_{ano}").assign(ano=ano) for ano in anos_ob],
                       ignore_index=True)

    # EECU de todos os assets da etapa, inclusive os de execuções anteriores
    feitos = {t["description"]: t["id"] for t in reversed(ee.data.getTaskList())
              if t["state"] == "COMPLETED"}
    nomes = [CFG["asset_mascara"], f"{CFG['asset_mascara']}_{a}_poligonos",
             f"{CFG['asset_mascara']}_area", "viirs_urbano", "ob_urbano_piloto",
             *[f"ob_urbano_{x}" for x in anos_ob]] if ob is not None else []
    for n in nomes:
        if eecu.get(n) is None and n in feitos:
            eecu[n] = _eecu_h(ee, feitos[n])

    # painel município × ano (grupos de análise)
    anos = range(MB["anos"][0], MB["anos"][1] + 1)
    out = pd.MultiIndex.from_product([ids, anos], names=["id_municipio", "ano"]).to_frame(
        index=False)
    out = out.merge(area.drop(columns="area_mascara_ref_ha"), how="left")
    out = out.merge(vi, how="left")
    if ob is not None:
        out = out.merge(ob, how="left")
    out.to_parquet(path("interim") / "urbano_mun_ano.parquet", index=False)

    # --- aceite ---
    lz = pd.read_parquet(path("interim") / "luzes_mun_ano.parquet",
                         columns=["id_municipio", "ano", "viirs_soma"])
    c = vi.merge(lz, how="left")
    c["soma_df"] = c["viirs_urbano_soma"] + c["viirs_fora_soma"]
    div_int = (c["soma_df"] / c["viirs_total_check"] - 1).abs().max()
    div_s03 = (c["viirs_total_check"] / c["viirs_soma"] - 1).abs()
    mb = pd.read_parquet(path("interim") / "mapbiomas_mun_ano.parquet",
                         columns=["id_municipio", "ano", "area_urbano_ha"])
    cobre = area.merge(mb[mb["ano"] == a], on="id_municipio")
    cobre_ok = (cobre[f"area_mascara_{a}_ha"] >= cobre["area_urbano_ha"] * 0.99).mean()
    share_d = (c.groupby("ano")[["viirs_urbano_soma", "viirs_total_check"]].sum()
               .pipe(lambda x: x["viirs_urbano_soma"] / x["viirs_total_check"]))
    testes = {
        f"Máscara com área > 0 em todos os {len(ids)} municípios ({a})":
            (area[f"area_mascara_{a}_ha"] > 0).sum() == len(ids),
        "Máscara cobre a área urbana do MapBiomas (≥ 99% da classe 24) em todos os municípios":
            cobre_ok == 1,
        f"Luzes: dentro + fora = total no EE (máx. |div| {div_int:.2e})": div_int < 1e-6,
        f"Luzes: total ≈ viirs_soma da Etapa 3 (mediana |div| {div_s03.median():.2%}, "
        f"p99 {div_s03.quantile(0.99):.2%})": div_s03.median() < 0.01,
        f"Luzes: {vi['id_municipio'].nunique()} municípios × {vi['ano'].nunique()} anos":
            vi["id_municipio"].nunique() == len(ids),
    }
    info = [
        f"Máscara: classe {CFG['classes']} do MapBiomas C11, buffer {CFG['buffer_m']} m, "
        f"{CFG['escala_mascara_m']} m na Albers. Área total: "
        + "; ".join(f"{x}: {area[f'area_mascara_{x}_ha'].sum() / 100:,.0f} km²"
                    for x in CFG["anos_mascara"])
        + f" (classe 24 em {a}: {cobre['area_urbano_ha'].sum() / 100:,.0f} km²).",
        "Fração da radiância VIIRS dentro da máscara de "
        f"{a}: " + "; ".join(f"{k}: {v:.1%}" for k, v in share_d.items() if k in (2013, 2019,
                                                                             2025)),
        "EECU-h por task: "
        + ("; ".join(f"{k}: {v:.2f}" for k, v in eecu.items() if v is not None) or "nenhum")
        + f" (total {sum(v for v in eecu.values() if v):.1f})",
        f"Piloto Open Buildings ({ob_cfg['piloto']['ano']}, 4 m, {len(pil['ids'])} municípios, "
        f"{pil['area_piloto_ha'] / 100:,.0f} km² de máscara): "
        f"{pil['eecu_h'] or float('nan'):.2f} EECU-h. Estimativa para "
        f"{pil['area_total_ha'] / 100:,.0f} km² × {pil['n_anos']} anos: "
        f"{pil['eecu_h_total'] or float('nan'):,.0f} EECU-h.",
        "Open Buildings completo: " + ("calculado" if ob is not None else
                                        "pendente (urbano.ob.confirmado: false)"),
    ]
    linhas = ["# Etapa 4b — máscara urbana: aceite", ""]
    linhas += [f"- [{'OK' if ok else 'FALHA'}] {t}" for t, ok in testes.items()]
    linhas += ["", "## Informações", ""] + [f"- {i}" for i in info]
    texto = "\n".join(linhas) + "\n"
    (path("logs") / "s04b_urbano.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(testes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
