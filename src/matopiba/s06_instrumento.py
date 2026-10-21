"""Etapa 6: instrumento shift-share (potencial agronômico × preço internacional da soja).

Potencial: FAO-GAEZ v4, rendimento atingível de soja de sequeiro (alto e baixo insumo,
clima 1981–2010), média por município e fração da área acima de um limiar.
Preço: World Bank Pink Sheet, soja (US$/t), anual, em US$ reais de 2010 (deflator MUV).
Instrumento: z_it = potencial_i (t/ha) × log(preço real_t), contemporâneo e defasado.

Saídas:
  data/interim/instrumento.parquet
  outputs/tabelas/s06_primeiro_estagio.csv
  outputs/logs/s06_instrumento.md

Uso: python -m matopiba.s06_instrumento
"""

import sys
import urllib.request

import geopandas as gpd
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
from rasterstats import zonal_stats

from matopiba.config import path, settings

CFG = settings()["instrumento"]


def _baixar(url: str, destino):
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, destino)
    return destino


def _frac_acima(lim: float):
    """Fração de pixels válidos com valor >= lim (rasterstats passa (array, propriedades))."""
    def f(a, *_):
        return float((a >= lim).mean()) if a.count() else np.nan
    return f


def gaez(malha: gpd.GeoDataFrame) -> pd.DataFrame:
    g = malha[["id_municipio", "geometry"]].to_crs(4326)
    out = pd.DataFrame({"id_municipio": g["id_municipio"]})
    for nome, info in CFG["gaez"]["rasters"].items():
        arq = _baixar(f"{CFG['gaez']['url_base']}/{info['caminho']}",
                      path("raw") / "gaez_v4" / info["caminho"].split("/")[-1])
        lim = info.get("limiar")
        stats = ["mean", "count"]
        kw = {"nodata": CFG["gaez"]["nodata"], "stats": stats}
        if lim is not None:
            kw["add_stats"] = {"frac": _frac_acima(lim)}
        z = pd.DataFrame(zonal_stats(g.geometry, str(arq), all_touched=False, **kw))
        # municípios menores que um pixel (~9 km): usa os pixels tocados
        vazio = z["count"].fillna(0) == 0
        if vazio.any():
            z2 = pd.DataFrame(zonal_stats(g.geometry[vazio.values], str(arq), all_touched=True,
                                          **kw))
            z.loc[vazio.values, z2.columns] = z2.values
        esc = info.get("escala", 1.0)
        out[f"{nome}_media"] = z["mean"].values * esc
        if lim is not None:
            out[f"{nome}_frac_acima"] = z["frac"].values
        out[f"{nome}_n_pixels"] = z["count"].values
        print(f"  {nome}: {int(vazio.sum())} municípios com fallback all_touched", flush=True)
    return out


def preco() -> pd.DataFrame:
    p = CFG["preco"]
    arq = _baixar(p["url"], path("raw") / p["arquivo"])
    out = {}
    for aba, col in [("Annual Prices (Nominal)", "preco_soja_nominal_usd"),
                     ("Annual Prices (Real)", "preco_soja_real_usd2010")]:
        x = pd.read_excel(arq, aba, header=None, engine="calamine")
        hdr = x.iloc[6:8].fillna("").astype(str).agg(" ".join).str.strip()
        c = next(i for i, h in hdr.items() if h.lower().startswith(p["coluna"].lower()))
        s = x.iloc[8:, [0, c]].set_axis(["ano", "v"], axis=1)
        s = s[pd.to_numeric(s["ano"], errors="coerce").notna()]
        out[col] = pd.to_numeric(s["v"], errors="coerce").set_axis(s["ano"].astype(int))
    df = pd.DataFrame(out).rename_axis("ano").reset_index()
    df["log_preco_real"] = np.log(df["preco_soja_real_usd2010"])
    df["log_preco_real_l1"] = df["log_preco_real"].shift(1)
    return df


def instrumento(pot: pd.DataFrame, pr: pd.DataFrame, universo: pd.DataFrame) -> pd.DataFrame:
    a0, a1 = settings()["mapbiomas"]["anos"]
    pr = pr[pr["ano"].between(a0, a1)]
    df = pot.merge(pr, how="cross")
    base = CFG["potencial_principal"]
    for v in [base, CFG["potencial_alternativo"]]:
        pot_t = df[f"{v}_media"] / 1000  # t/ha
        df[f"z_{v}"] = pot_t * df["log_preco_real"]
        df[f"z_{v}_l1"] = pot_t * df["log_preco_real_l1"]
    # Ganho tecnológico à la Bustos, Caprettini e Ponticelli (2016): (alto − baixo insumo),
    # em t/ha, × pós-liberação da soja transgênica, ou × tendência (décadas desde o início)
    df["ganho_tecnologico"] = (df["yl_alto_media"] - df["yl_baixo_media"]) / 1000
    df["z_bcp_pos"] = df["ganho_tecnologico"] * (df["ano"] >= CFG["bcp"]["ano_pos"])
    df["z_bcp_tend"] = df["ganho_tecnologico"] * (df["ano"] - a0) / 10
    return df.merge(universo[["id_municipio"]], on="id_municipio")


def diferencas_longas(inst: pd.DataFrame, universo: pd.DataFrame) -> pd.DataFrame:
    """Primeiro estágio em diferenças longas entre anos censitários, em três níveis.

    Δy = variação da participação (soja ou agricultura temporária) na área; Δz = variação do
    instrumento BCP no período. Agregação para AMC/microrregião: áreas somadas e potencial
    médio ponderado pela área do município (razões recalculadas a partir das somas).
    """
    import statsmodels.formula.api as smf

    mb = pd.read_parquet(path("interim") / "mapbiomas_mun_ano.parquet",
                         columns=["id_municipio", "ano", "area_soja_ha", "area_agri_temp_ha"])
    cw = universo[["id_municipio", "id_amc", "id_microrregiao", "sigla_uf", "grupo",
                   "area_ha"]]
    pot = inst.drop_duplicates("id_municipio")[["id_municipio", "ganho_tecnologico"]]
    anos = CFG["bcp"]["anos_censo"]
    d = mb[mb["ano"].isin(anos)].merge(cw, on="id_municipio").merge(pot, on="id_municipio")
    d = d[d["grupo"].isin(CFG["grupos_primeiro_estagio"])]
    linhas = []
    for nivel, chave in [("municipio", "id_municipio"), ("amc", "id_amc"),
                         ("microrregiao", "id_microrregiao")]:
        g = d.assign(pot_x_area=d["ganho_tecnologico"] * d["area_ha"]).groupby(
            [chave, "ano"]).agg(area_soja_ha=("area_soja_ha", "sum"),
                                area_agri_temp_ha=("area_agri_temp_ha", "sum"),
                                area_ha=("area_ha", "sum"), pot_x_area=("pot_x_area", "sum"),
                                sigla_uf=("sigla_uf", "first"),
                                cluster=("id_microrregiao", "first")).reset_index()
        g["ganho"] = g["pot_x_area"] / g["area_ha"]
        g["share_soja"] = g["area_soja_ha"] / g["area_ha"]
        g["share_agri_temp"] = g["area_agri_temp_ha"] / g["area_ha"]
        w = g.pivot_table(index=[chave, "sigla_uf", "cluster", "ganho"], columns="ano",
                          values=["share_soja", "share_agri_temp"]).reset_index()
        w.columns = ["_".join(map(str, c)).strip("_") for c in w.columns]
        periodos = list(zip(anos[:-1], anos[1:], strict=True))
        empilhado = []
        for a, b in periodos:
            p = w[[chave, "sigla_uf", "cluster", "ganho"]].copy()
            p["periodo"] = f"{a}-{b}"
            for y in ["share_soja", "share_agri_temp"]:
                p[f"d_{y}"] = w[f"{y}_{b}"] - w[f"{y}_{a}"]
            # Δz da versão tendência: ganho × duração do período (décadas). Dentro de um
            # período é só o ganho reescalado; no empilhado, pondera pela duração.
            p["dz_tend"] = p["ganho"] * (b - a) / 10
            empilhado.append(p)
        e = pd.concat(empilhado, ignore_index=True)
        z = "dz_tend"
        for y in ["d_share_soja", "d_share_agri_temp"]:
            specs = [(per, e[e["periodo"] == per]) for per in e["periodo"].unique()]
            specs.append(("empilhado", e))
            for per, s in specs:
                s = s.dropna(subset=[y, z])
                fe = "C(sigla_uf) + C(periodo)" if per == "empilhado" else "C(sigla_uf)"
                # cluster por microrregião; no nível microrregião, erro robusto (HC1)
                if nivel == "microrregiao":
                    m = smf.ols(f"{y} ~ {z} + {fe}", data=s).fit(cov_type="HC1")
                    ncl = np.nan
                else:
                    m = smf.ols(f"{y} ~ {z} + {fe}", data=s).fit(
                        cov_type="cluster", cov_kwds={"groups": s["cluster"].astype(str)})
                    ncl = s["cluster"].nunique()
                linhas.append({"nivel": nivel, "periodo": per, "dependente": y,
                               "coef": m.params[z], "ep": m.bse[z], "t": m.tvalues[z],
                               "F": m.tvalues[z] ** 2, "n": int(m.nobs), "n_clusters": ncl})
    return pd.DataFrame(linhas)


def primeiro_estagio(inst: pd.DataFrame, universo: pd.DataFrame) -> pd.DataFrame:
    mb = pd.read_parquet(path("interim") / "mapbiomas_mun_ano.parquet",
                         columns=["id_municipio", "ano", "share_soja", "share_agri_temp"])
    d = (inst.merge(mb, on=["id_municipio", "ano"])
         .merge(universo[["id_municipio", "grupo", "id_microrregiao"]], on="id_municipio"))
    d = d[d["grupo"].isin(CFG["grupos_primeiro_estagio"])].dropna(subset=["share_soja"])
    d = d.set_index(["id_municipio", "ano"])
    linhas = []
    for y in ["share_soja", "share_agri_temp"]:
        for z in ["z_bcp_pos", "z_bcp_tend",
                  f"z_{CFG['potencial_principal']}", f"z_{CFG['potencial_principal']}_l1",
                  f"z_{CFG['potencial_alternativo']}", f"z_{CFG['potencial_alternativo']}_l1"]:
            s = d[[y, z, "id_microrregiao"]].dropna()
            m = PanelOLS(s[y], s[[z]], entity_effects=True, time_effects=True).fit(
                cov_type="clustered", clusters=s["id_microrregiao"].astype(str))
            linhas.append({
                "dependente": y, "instrumento": z, "coef": m.params[z], "ep": m.std_errors[z],
                "t": m.tstats[z], "F_cluster": m.tstats[z] ** 2, "n_obs": m.nobs,
                "n_municipios": s.index.get_level_values(0).nunique(),
                "n_clusters": s["id_microrregiao"].nunique(), "r2_within": m.rsquared_within,
            })
    return pd.DataFrame(linhas)


def main() -> int:
    universo = pd.read_parquet(path("processed") / "universo.parquet")
    malha = gpd.read_parquet(path("interim") / "malha_mun.parquet")
    pot = gaez(malha)
    pr = preco()
    inst = instrumento(pot, pr, universo)
    inst.to_parquet(path("interim") / "instrumento.parquet", index=False)
    fe = primeiro_estagio(inst, universo)
    fe.to_csv(path("tabelas") / "s06_primeiro_estagio.csv", index=False)
    ld = diferencas_longas(inst, universo)
    ld.to_csv(path("tabelas") / "s06_primeiro_estagio_dif_longas.csv", index=False)

    zp, yp = CFG["instrumento_principal"], CFG["tratamento_principal"]
    principal = fe[(fe["dependente"] == yp) & (fe["instrumento"] == zp)].iloc[0]
    sem_pot = pot[f"{CFG['potencial_principal']}_media"].isna().sum()
    grp = (inst.drop_duplicates("id_municipio").merge(universo[["id_municipio", "grupo"]])
           .groupby("grupo")[[f"{CFG['potencial_principal']}_media", "yl_baixo_media",
                              "ganho_tecnologico", f"{CFG['potencial_principal']}_frac_acima"]]
           .median())
    testes = {
        f"Primeiro estágio reportado ({yp} ~ {zp}, EF município e ano, cluster "
        f"microrregião): coef {principal['coef']:.4f}, t {principal['t']:.2f}, "
        f"F {principal['F_cluster']:.1f}": True,
        f"Potencial GAEZ para todos os municípios (sem valor: {sem_pot})": sem_pot == 0,
    }
    linhas = ["# Etapa 6 — instrumento: aceite", ""]
    linhas += [f"- [{'OK' if ok else 'FALHA'}] {t}" for t, ok in testes.items()]
    linhas += ["", "## Primeiro estágio preliminar", "",
               f"Amostra: grupos {CFG['grupos_primeiro_estagio']}, "
               f"{int(principal['n_municipios'])} municípios, {int(principal['n_clusters'])} "
               "microrregiões. F = t² com erro-padrão clusterizado (um instrumento).", "",
               fe.to_markdown(index=False, floatfmt=".4f"), "",
               "## Primeiro estágio em diferenças longas (anos censitários)", "",
               "Δ participação na área ~ ganho tecnológico × duração do período (décadas), "
               "EF de UF (e de período no empilhado); cluster microrregião (nível microrregião: "
               "erro robusto HC1).", "",
               ld.to_markdown(index=False, floatfmt=".4f"), "",
               "## Potencial por grupo (mediana)", "", grp.to_markdown(floatfmt=".3f"), "",
               "## Preço real da soja (US$ de 2010/t)", "",
               pr[pr["ano"] >= 1985][["ano", "preco_soja_nominal_usd", "preco_soja_real_usd2010"]]
               .to_markdown(index=False, floatfmt=".0f")]
    texto = "\n".join(linhas) + "\n"
    (path("logs") / "s06_instrumento.md").write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if all(testes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
