"""Ferramentas comuns da Etapa 8: amostras, desfechos, estimadores e exportação de tabelas.

Estimadores:
  cs_did      Callaway e Sant'Anna (2021), tendências paralelas incondicionais, controles
              nunca tratados, período-base "varying"; erros-padrão pela função de influência,
              clusterizados. (O pacote `differences` 0.3 não aceita cluster com o pandas atual;
              as estimativas pontuais conferem com ele — ver tests/test_analise.py.)
  twfe        TWFE estático e event study com efeitos fixos de unidade e ano.
  iv_fe       2SLS com efeitos fixos absorvidos (pyhdfe), cluster, F do primeiro estágio,
              forma reduzida e intervalo de Anderson-Rubin.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyhdfe
import statsmodels.api as sm
from linearmodels.iv import IV2SLS
from linearmodels.panel import PanelOLS
from scipy import stats

from matopiba.config import path, settings

CFG = settings()["analise"]


@dataclass(frozen=True)
class Desfecho:
    nome: str
    coluna: str
    rotulo: str
    anos: tuple[int, int]
    log: bool = False
    so_anos_impares: bool = False


DESFECHOS = [Desfecho(**d) for d in CFG["desfechos"]]


# ---------------------------------------------------------------- dados

def carregar(nivel: str = "municipio") -> pd.DataFrame:
    p = pd.read_parquet(path("processed") / f"painel_{nivel}.parquet")
    p["unidade"] = p["id_municipio" if nivel == "municipio" else "id_amc"]
    p["cluster"] = p["id_microrregiao"].astype(str)
    return p


def preparar_desfecho(p: pd.DataFrame, d: Desfecho) -> pd.Series:
    y = p[d.coluna].astype(float)
    if d.log:
        y = np.log(y.where(y > 0))
    fora = ~p["ano"].between(*d.anos)
    if d.so_anos_impares:
        fora |= p["ano"] % 2 == 0
    return y.mask(fora)


def amostra_did(p: pd.DataFrame, var: str = "agri_temp", limiar: float | None = None):
    """Grupos de análise, sem unidades já tratadas no início; coorte NaN = nunca tratada."""
    lim = limiar if limiar is not None else settings()["tratamento"]["limiar_padrao"]
    suf = f"{var}_{int(round(lim * 100)):02d}"
    s = p[p["grupo"].isin(CFG["grupos"]) & ~p[f"ja_tratado_inicio_{suf}"].astype(bool)].copy()
    s["coorte"] = s[f"ano_trat_{suf}"]
    s["tratado"] = s[f"trat_{suf}"].astype(float)
    return s


# ---------------------------------------------------------------- Callaway–Sant'Anna

def cs_did(df: pd.DataFrame, y: str, coorte: str = "coorte", unidade: str = "unidade",
           cluster: str = "cluster", balancear: bool = True, base: str = "varying") -> dict:
    """ATT(g,t) com controles nunca tratados.

    base="varying": pré-períodos comparam t com t-1 (padrão do CS); pós comparam com g-1.
    base="universal": todos os períodos comparam com g-1 (pré-tendências acumuladas visíveis).
    balancear=True mantém só unidades observadas em todos os anos da janela (como o `did` do
    R com panel=TRUE); municípios criados no meio da janela saem — o nível AMC os cobre.
    """
    d = df[[unidade, "ano", coorte, cluster, y]].dropna(subset=[y]).copy()
    anos = sorted(d["ano"].unique())
    if balancear:
        d = d[d.groupby(unidade)["ano"].transform("nunique") == len(anos)]
    # tratadas só depois do fim da janela do desfecho contam como nunca tratadas
    d[coorte] = d[coorte].where(d[coorte] <= anos[-1])
    # coortes sem período anterior observado na janela do desfecho não são identificadas
    d = d[d[coorte].isna() | (d[coorte] > anos[0])]
    w = d.pivot_table(index=unidade, columns="ano", values=y)
    info = d.drop_duplicates(unidade).set_index(unidade)[[coorte, cluster]].loc[w.index]
    g_all = info[coorte]
    nunca = g_all.isna()
    clusters = info[cluster].to_numpy()
    n = len(w)
    linhas, ifs = [], {}
    for g in sorted(g_all.dropna().unique()):
        trat = (g_all == g).to_numpy()
        for t in anos:
            if t == anos[0] and base == "varying":
                continue
            if not any(a < g for a in anos):
                continue
            g_1 = max(a for a in anos if a < g)
            if base == "universal":
                if t == g_1:
                    continue
                b0 = g_1
            else:
                b0 = g_1 if t >= g else max(a for a in anos if a < t)
            dy = (w[t] - w[b0]).to_numpy()
            ok = ~np.isnan(dy)
            tt, cc = trat & ok, nunca.to_numpy() & ok
            if tt.sum() == 0 or cc.sum() < 2:
                continue
            a, b = dy[tt].mean(), dy[cc].mean()
            inf = np.zeros(n)
            inf[tt] = n * (dy[tt] - a) / tt.sum()
            inf[cc] = -n * (dy[cc] - b) / cc.sum()
            linhas.append({"coorte": int(g), "ano": int(t), "e": int(t - g), "att": a - b,
                           "n_tratados": int(tt.sum()), "n_controles": int(cc.sum())})
            ifs[(int(g), int(t))] = inf
    gt = pd.DataFrame(linhas)
    if gt.empty:
        return {"gt": gt, "evento": pd.DataFrame(), "simples": {}}
    gt["ep"] = [_ep_cluster(ifs[(r.coorte, r.ano)], clusters, n) for r in gt.itertuples()]

    def agrega(sel: pd.DataFrame, com_if: bool = False):
        pesos = sel["n_tratados"] / sel["n_tratados"].sum()
        inf = sum(pw * ifs[(r.coorte, r.ano)] for pw, r in zip(pesos, sel.itertuples(),
                                                                 strict=True))
        res = float((pesos * sel["att"]).sum()), _ep_cluster(inf, clusters, n)
        return (*res, inf) if com_if else res

    ev, ifs_e = [], {}
    for e, sel in gt.groupby("e"):
        att, ep, ifs_e[int(e)] = agrega(sel, com_if=True)
        ev.append({"e": int(e), "att": att, "ep": ep, "n_coortes": len(sel)})
    evento = pd.DataFrame(ev)
    att, ep = agrega(gt[gt["e"] >= 0])
    pre = gt[gt["e"] < 0]
    simples = {"att": att, "ep": ep, "p": 2 * stats.norm.sf(abs(att / ep)),
               "n_unidades_tratadas": int((~nunca).sum()), "n_controles": int(nunca.sum()),
               "n_coortes": int(g_all.nunique()), "anos": f"{anos[0]}–{anos[-1]}",
               "pre_media": float(pre["att"].mean()) if len(pre) else np.nan}
    # covariância clusterizada entre os coeficientes do event study (para o HonestDiD)
    vcov = pd.DataFrame(_vcov_cluster(np.column_stack(list(ifs_e.values())), clusters, n),
                        index=list(ifs_e), columns=list(ifs_e))
    return {"gt": gt, "evento": evento, "simples": simples, "vcov_evento": vcov}


def _vcov_cluster(infs: np.ndarray, clusters: np.ndarray, n: int) -> np.ndarray:
    s = pd.DataFrame(infs).groupby(clusters).sum().to_numpy()
    g = len(s)
    return s.T @ s * g / (g - 1) / n ** 2


def _ep_cluster(inf: np.ndarray, clusters: np.ndarray, n: int) -> float:
    s = pd.Series(inf).groupby(clusters).sum().to_numpy()
    g = len(s)
    return float(np.sqrt((s ** 2).sum() * g / (g - 1)) / n)


# ---------------------------------------------------------------- TWFE

def twfe(df: pd.DataFrame, y: str, x: str, controles: list[str] | None = None) -> dict:
    s = df[["unidade", "ano", "cluster", y, x, *(controles or [])]].dropna()
    s = s.set_index(["unidade", "ano"])
    m = PanelOLS(s[y], s[[x, *(controles or [])]], entity_effects=True, time_effects=True,
                 drop_absorbed=True).fit(cov_type="clustered", clusters=s["cluster"])
    return {"coef": float(m.params[x]), "ep": float(m.std_errors[x]),
            "p": float(m.pvalues[x]), "n": int(m.nobs),
            "n_unidades": int(s.index.get_level_values(0).nunique())}


def twfe_evento(df: pd.DataFrame, y: str, coorte: str = "coorte",
                janela: tuple[int, int] = (-10, 10)) -> pd.DataFrame:
    """Event study TWFE com leads/lags binned nas pontas; referência e = -1."""
    s = df[["unidade", "ano", "cluster", y, coorte]].dropna(subset=[y]).copy()
    e = (s["ano"] - s[coorte]).clip(*janela)
    dummies = []
    for k in range(janela[0], janela[1] + 1):
        if k == -1:
            continue
        c = f"e_{k}".replace("-", "m")
        s[c] = (e == k).astype(float).fillna(0.0)
        dummies.append((k, c))
    s = s.set_index(["unidade", "ano"])
    cols = [c for _, c in dummies if s[c].sum() > 0]
    m = PanelOLS(s[y], s[cols], entity_effects=True, time_effects=True,
                 drop_absorbed=True).fit(cov_type="clustered", clusters=s["cluster"])
    return pd.DataFrame([{"e": k, "coef": float(m.params[c]), "ep": float(m.std_errors[c])}
                         for k, c in dummies if c in m.params.index])


# ---------------------------------------------------------------- IV com efeitos fixos

def _residualizar(s: pd.DataFrame, cols: list[str], fe: list[str]) -> pd.DataFrame:
    alg = pyhdfe.create(s[fe].apply(lambda c: pd.factorize(c)[0]).to_numpy(),
                        drop_singletons=False)
    r = alg.residualize(s[cols].to_numpy())
    return pd.DataFrame(r, columns=cols, index=s.index)


def iv_fe(df: pd.DataFrame, y: str, x: str, z: str, fe: list[str] | None = None,
          controles: list[str] | None = None, ar_grade: int = 401) -> dict:
    """2SLS de y em x instrumentado por z, absorvendo `fe`, cluster em `cluster`."""
    fe = fe or ["unidade", "ano"]
    cols = [y, x, z, *(controles or [])]
    s = df[[*dict.fromkeys(fe + ["cluster"]), *cols]].dropna().copy()
    s[cols] = s[cols].astype(float)  # tipos nulos do pandas (Float64) quebram o statsmodels
    r = _residualizar(s, cols, fe)
    cl = s["cluster"].to_numpy()
    exog = r[controles] if controles else None
    fs = sm.OLS(r[x], pd.concat([r[[z]], exog], axis=1) if controles else r[[z]]).fit(
        cov_type="cluster", cov_kwds={"groups": cl})
    rf = sm.OLS(r[y], pd.concat([r[[z]], exog], axis=1) if controles else r[[z]]).fit(
        cov_type="cluster", cov_kwds={"groups": cl})
    iv = IV2SLS(r[y], exog, r[x], r[z]).fit(cov_type="clustered", clusters=cl)
    ols = sm.OLS(r[y], pd.concat([r[[x]], exog], axis=1) if controles else r[[x]]).fit(
        cov_type="cluster", cov_kwds={"groups": cl})
    ar = _anderson_rubin(r, y, x, z, controles, cl, float(iv.params[x]),
                         float(iv.std_errors[x]), ar_grade)
    return {
        "iv_coef": float(iv.params[x]), "iv_ep": float(iv.std_errors[x]),
        "iv_p": float(iv.pvalues[x]),
        "fs_coef": float(fs.params[z]), "fs_ep": float(fs.bse[z]),
        "F_efetivo": float(fs.tvalues[z] ** 2),
        "rf_coef": float(rf.params[z]), "rf_ep": float(rf.bse[z]), "rf_p": float(rf.pvalues[z]),
        "ols_coef": float(ols.params[x]), "ols_ep": float(ols.bse[x]),
        "ar_ic_inf": ar[0], "ar_ic_sup": ar[1], "n": int(len(s)),
        "n_unidades": int(s[fe[0]].nunique()), "n_clusters": int(len(np.unique(cl))),
    }


def _anderson_rubin(r, y, x, z, controles, cl, b_iv, ep_iv, grade, alpha=0.05):
    """IC de Anderson-Rubin por inversão do teste (grade em torno do 2SLS, ±10 ep)."""
    largura = 10 * ep_iv if np.isfinite(ep_iv) and ep_iv > 0 else 1.0
    bs = np.linspace(b_iv - largura, b_iv + largura, grade)
    X = pd.concat([r[[z]], r[controles]], axis=1) if controles else r[[z]]
    aceitos = []
    for b in bs:
        m = sm.OLS(r[y] - b * r[x], X).fit(cov_type="cluster", cov_kwds={"groups": cl})
        if m.pvalues[z] > alpha:
            aceitos.append(b)
    if not aceitos:
        return (np.nan, np.nan)
    inf, sup = min(aceitos), max(aceitos)
    # IC tocando a borda da grade = ilimitado naquele lado
    return (-np.inf if inf == bs[0] else inf, np.inf if sup == bs[-1] else sup)


# ---------------------------------------------------------------- exportação

def salvar_tabela(df: pd.DataFrame, nome: str, legenda: str, casas: int = 3) -> None:
    df.to_csv(path("tabelas") / f"{nome}.csv", index=False)
    tex = df.to_latex(index=False, float_format=f"%.{casas}f", caption=legenda,
                      label=f"tab:{nome}", escape=True, na_rep="—")
    (path("tabelas") / f"{nome}.tex").write_text(tex, encoding="utf-8")


def estrelas(p: float) -> str:
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
