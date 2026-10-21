"""Etapa 8.6b: sensibilidade do DiD a violações de tendências paralelas (HonestDiD).

Rambachan e Roth (2023), pacote `honestdid` (port Python do HonestDiD do R, validado contra o
exemplo do Medicaid do README do R). Insumo: event study de Callaway–Sant'Anna com base
universal (e = -1), mesma amostra do s08_did, e a covariância clusterizada por microrregião
obtida das funções de influência.

Restrições:
  Δ^RM(Mbar)  a violação pós-tratamento entre anos consecutivos é no máximo Mbar vezes a maior
              violação pré-tratamento entre anos consecutivos (IC condicional híbrido, C-LF).
  Δ^SD(M)     a tendência diferencial pode mudar de inclinação no máximo M por ano; M = 0 é uma
              tendência linear extrapolada (IC de comprimento fixo, FLCI).
Parâmetros-alvo (settings): média de e = 0…10 e efeito em e = 5.

Requer o ambiente opcional (numpy < 2.4; ver README):
  %USERPROFILE%/.venvs/matopiba_honestdid/Scripts/python -m matopiba.s08_honestdid

Saídas:
  outputs/tabelas/s08_honestdid.{csv,tex}
  outputs/figuras/s08_honestdid.png
"""

import sys
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matopiba.analise import (CFG, DESFECHOS, amostra_did, carregar, cs_did, preparar_desfecho,
                              salvar_tabela)
from matopiba.config import path

AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#8a897f", "#1c1c1a", "#5f5e5a", "#e4e3df"
HD = CFG["honestdid"]


def event_study(s: pd.DataFrame, d) -> tuple[np.ndarray, np.ndarray, int, int, pd.DataFrame]:
    """β e Σ do event study CS (base universal) na janela, sem o e = -1."""
    x = s.assign(y=preparar_desfecho(s, d)).dropna(subset=["y"])
    x = x[x.groupby("unidade")["ano"].transform("nunique") == x["ano"].nunique()]
    cs = cs_did(x, "y", balancear=False, base="universal")
    lo, hi = HD["janela"]
    es = list(range(lo, -1)) + list(range(0, hi + 1))
    falta = [e for e in es if e not in cs["vcov_evento"].index]
    if falta:
        raise ValueError(f"{d.nome}: event study sem os tempos {falta}")
    ev = cs["evento"].set_index("e").loc[es]
    return (ev["att"].to_numpy(), cs["vcov_evento"].loc[es, es].to_numpy(),
            sum(e < -1 for e in es), sum(e >= 0 for e in es), ev.reset_index())


def sensibilidade(b, V, npre, npost) -> pd.DataFrame:
    import honestdid as hd

    alvos = {}
    for a in HD["alvos"]:
        if a == "media":
            alvos[f"média e = 0…{npost - 1}"] = np.full(npost, 1 / npost)
        else:
            alvos[f"e = {a}"] = np.eye(npost)[int(a)]
    out = []
    for alvo, l_vec in alvos.items():
        o = hd.constructOriginalCS(b, V, npre, npost, l_vec=l_vec)
        out.append({"alvo": alvo, "restricao": "original", "parametro": np.nan,
                    "lb": float(o["lb"].iloc[0]), "ub": float(o["ub"].iloc[0])})
        t = time.time()
        rm = hd.createSensitivityResults_relativeMagnitudes(
            b, V, npre, npost, l_vec=l_vec, Mbarvec=HD["mbar"], gridPoints=HD["grade"])
        out += [{"alvo": alvo, "restricao": "RM", "parametro": r.Mbar, "lb": r.lb, "ub": r.ub}
                for r in rm.itertuples()]
        sd = hd.createSensitivityResults(b, V, npre, npost, l_vec=l_vec, Mvec=HD["m"])
        out += [{"alvo": alvo, "restricao": "SD", "parametro": r.M, "lb": r.lb, "ub": r.ub}
                for r in sd.itertuples()]
        print(f"  {alvo}: {time.time() - t:.0f}s", flush=True)
    r = pd.DataFrame(out)
    r["inclui_zero"] = (r["lb"] <= 0) & (r["ub"] >= 0)
    return r


def ruptura(r: pd.DataFrame) -> pd.DataFrame:
    """Menor Mbar / M da grade em que o IC passa a incluir zero (breakdown), por alvo."""
    linhas = []
    for (alvo, rest), g in r[r["restricao"] != "original"].groupby(["alvo", "restricao"]):
        z = g[g["inclui_zero"]]["parametro"]
        linhas.append({"alvo": alvo, "restricao": rest,
                       "ruptura": f"{z.min():g}" if len(z) else f"> {g['parametro'].max():g}"})
    return pd.DataFrame(linhas)


def rotulo(nome: str) -> str:
    return next(d.rotulo for d in DESFECHOS if d.nome == nome)


def figura(res: dict[str, pd.DataFrame], eventos: dict[str, pd.DataFrame]) -> None:
    nomes = list(res)
    fig, axes = plt.subplots(len(nomes), 3, figsize=(15, 4.2 * len(nomes)), squeeze=False)
    for i, nome in enumerate(nomes):
        ev, r = eventos[nome], res[nome]
        alvos = [a for a in r["alvo"].unique()]
        ax = axes[i, 0]
        ax.errorbar(ev["e"], ev["att"], yerr=1.96 * ev["ep"], fmt="o", color=AZUL,
                    markersize=3.5, elinewidth=1, capsize=0)
        ax.scatter([-1], [0], color=CINZA, s=14, zorder=3)
        ax.axvline(-0.5, color="#a8a79f", linewidth=0.8, linestyle="--")
        ax.set_title(f"{rotulo(nome)}: event study (CS, base universal)", fontsize=10,
                     color=TINTA, loc="left")
        ax.set_xlabel("anos desde o tratamento", fontsize=8, color=TINTA2)
        for j, (rest, xlab) in enumerate([("RM", "Mbar (Δ^RM)"), ("SD", "M (Δ^SD)")], start=1):
            ax = axes[i, j]
            # posições igualmente espaçadas; "orig." = IC convencional
            vals = sorted(r.loc[r["restricao"] == rest, "parametro"].unique())
            pos = {v: k + 1 for k, v in enumerate(vals)}
            for k, (alvo, cor) in enumerate(zip(alvos, [AZUL, TINTA2], strict=False)):
                g = r[(r["alvo"] == alvo) & (r["restricao"] == rest)]
                o = r[(r["alvo"] == alvo) & (r["restricao"] == "original")].iloc[0]
                desl = (k - 0.5) * 0.25
                ax.vlines([pos[v] + desl for v in g["parametro"]], g["lb"], g["ub"],
                          color=cor, linewidth=2, label=alvo)
                ax.vlines(desl, o["lb"], o["ub"], color=cor, linewidth=2, linestyle=":")
            ax.set_xticks([0] + list(pos.values()), ["orig."] + [f"{v:g}" for v in vals],
                          fontsize=7)
            ax.set_title(f"IC robusto, Δ^{rest}", fontsize=10, color=TINTA, loc="left")
            ax.set_xlabel(xlab, fontsize=8, color=TINTA2)
            if j == 1:
                ax.legend(frameon=False, fontsize=8, loc="upper left")
        for ax in axes[i]:
            ax.axhline(0, color="#a8a79f", linewidth=0.8)
            ax.grid(axis="y", color=GRADE, linewidth=0.6)
            for lado in ["top", "right"]:
                ax.spines[lado].set_visible(False)
            ax.tick_params(colors=TINTA2, labelsize=8)
    fig.suptitle("HonestDiD: sensibilidade a violações de tendências paralelas (IC 95%)",
                 x=0.01, ha="left", fontsize=12, color=TINTA)
    fig.text(0.01, -0.02, "Δ^RM: violação pós ≤ Mbar × maior violação pré (entre anos "
             "consecutivos). Δ^SD: inclinação da tendência diferencial muda no máximo M por ano "
             "(M = 0: tendência linear extrapolada). Cluster por microrregião.",
             fontsize=8, color=TINTA2)
    fig.tight_layout()
    fig.savefig(path("figuras") / "s08_honestdid.png", dpi=200, facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    s = amostra_did(carregar())
    res, eventos, rupt = {}, {}, []
    for d in DESFECHOS:
        if d.nome not in HD["desfechos"]:
            continue
        print(f"[{d.nome}]", flush=True)
        b, V, npre, npost, ev = event_study(s, d)
        eventos[d.nome] = ev
        res[d.nome] = sensibilidade(b, V, npre, npost).assign(desfecho=d.rotulo)
        rupt.append(ruptura(res[d.nome]).assign(desfecho=d.rotulo))
    tab = pd.concat(res.values(), ignore_index=True)
    tab = tab[["desfecho", "alvo", "restricao", "parametro", "lb", "ub", "inclui_zero"]]
    salvar_tabela(tab, "s08_honestdid", "HonestDiD: IC 95% robustos a violações de tendências "
                  "paralelas (Δ^RM e Δ^SD), event study CS com base universal", casas=4)
    rupt = pd.concat(rupt, ignore_index=True)
    rupt.to_csv(path("tabelas") / "s08_honestdid_ruptura.csv", index=False)
    figura(res, eventos)
    print(tab.round(4).to_string(index=False))
    print("\nRuptura (menor valor da grade com IC incluindo zero):")
    print(rupt.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
