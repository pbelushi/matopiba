import pandas as pd
from linearmodels.panel import PanelOLS

from matopiba.config import path

pd.set_option("display.width", 200)
inst = pd.read_parquet(path("interim") / "instrumento.parquet")
u = pd.read_parquet(path("processed") / "universo.parquet")
mb = pd.read_parquet(path("interim") / "mapbiomas_mun_ano.parquet",
                     columns=["id_municipio", "ano", "share_soja", "share_agri_temp"])
d = (inst.merge(mb, on=["id_municipio", "ano"])
     .merge(u[["id_municipio", "grupo", "id_microrregiao"]]))
d = d[d.grupo.isin(["matopiba", "cerrado_fora"])].dropna(subset=["share_soja"])
alto, baixo = d["yl_alto_media"] / 1000, d["yl_baixo_media"] / 1000
gap = alto - baixo
t = d["ano"] - 1985
cands = {
    "BCP: (alto-baixo) x pós-2003": gap * (d["ano"] >= 2003),
    "BCP: (alto-baixo) x tendência": gap * t / 10,
    "alto x tendência": alto * t / 10,
    "alto x log preço x tendência": alto * d["log_preco_real"] * t / 10,
    "alto x log preço (só 2000+)": alto * d["log_preco_real"].where(d["ano"] >= 2000),
}
d = d.set_index(["id_municipio", "ano"])
linhas = []
for y in ["share_soja", "share_agri_temp"]:
    for nome, z in cands.items():
        s = pd.DataFrame({"y": d[y].values, "z": z.values, "c": d["id_microrregiao"].values},
                         index=d.index).dropna()
        m = PanelOLS(s["y"], s[["z"]], entity_effects=True, time_effects=True).fit(
            cov_type="clustered", clusters=s["c"].astype(str))
        linhas.append({"y": y, "instrumento": nome, "coef": m.params["z"],
                       "t": m.tstats["z"], "F": m.tstats["z"] ** 2, "n": m.nobs})
print(pd.DataFrame(linhas).round(4).to_string(index=False))
