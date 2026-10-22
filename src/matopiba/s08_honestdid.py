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

Especificações (desfecho, limiar, janela, parâmetros-alvo) em settings: analise.honestdid.
Também reporta, por especificação, o teste de Wald de pré-coeficientes nulos e a inclinação
linear da pré-tendência (e = -5…-1, com e = -1 fixado em zero).

Cada (especificação, alvo, Mbar) roda em um processo; o Δ^RM domina o tempo.

Requer o ambiente opcional (numpy < 2.4; ver README):
  %USERPROFILE%/.venvs/matopiba_honestdid/Scripts/python -m matopiba.s08_honestdid [nomes]

Saídas:
  outputs/tabelas/s08_honestdid.{csv,tex}          ICs robustos
  outputs/tabelas/s08_honestdid_ruptura.csv        menor Mbar / M com IC incluindo zero
  outputs/tabelas/s08_honestdid_pretendencia.csv   Wald e inclinação pré
  outputs/figuras/s08_honestdid_<nome>.png
"""

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from matopiba.analise import (CFG, amostra_did, carregar, com_luzes_por_produto, cs_did,
                              desfecho, preparar_desfecho, salvar_tabela)
from matopiba.config import path, settings

AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#8a897f", "#1c1c1a", "#5f5e5a", "#e4e3df"
HD = CFG["honestdid"]


@dataclass(frozen=True)
class Spec:
    nome: str
    desfecho: str
    limiar: float
    janela: tuple[int, int]
    alvos: tuple


def especificacoes(nomes: list[str] | None = None) -> list[Spec]:
    lim = settings()["tratamento"]["limiar_padrao"]
    out = [Spec(e["nome"], e["desfecho"], e.get("limiar", lim),
                tuple(e.get("janela", HD["janela"])), tuple(e.get("alvos", HD["alvos"])))
           for e in HD["especificacoes"]]
    if nomes:
        desconhecidas = set(nomes) - {s.nome for s in out}
        if desconhecidas:
            raise SystemExit(f"especificações desconhecidas: {sorted(desconhecidas)}")
        out = [s for s in out if s.nome in nomes]
    return out


def event_study(p: pd.DataFrame, sp: Spec) -> dict:
    """β e Σ do event study CS (base universal) na janela, sem o e = -1."""
    d = desfecho(sp.desfecho)
    s = amostra_did(p, limiar=sp.limiar)
    x = s.assign(y=preparar_desfecho(s, d)).dropna(subset=["y"])
    x = x[x.groupby("unidade")["ano"].transform("nunique") == x["ano"].nunique()]
    cs = cs_did(x, "y", balancear=False, base="universal")
    lo, hi = sp.janela
    es = list(range(lo, -1)) + list(range(0, hi + 1))
    falta = [e for e in es if e not in cs["vcov_evento"].index]
    if falta:
        raise ValueError(f"{sp.nome}: event study sem os tempos {falta}")
    ev = cs["evento"].set_index("e").loc[es].reset_index()
    b, V = ev["att"].to_numpy(), cs["vcov_evento"].loc[es, es].to_numpy()
    npre = sum(e < -1 for e in es)
    return {"b": b, "V": V, "npre": npre, "npost": len(es) - npre, "ev": ev,
            "rotulo": d.rotulo, "pre": pre_tendencia(b[:npre], V[:npre, :npre], es[:npre]),
            "n_tratados": cs["simples"]["n_unidades_tratadas"],
            "n_controles": cs["simples"]["n_controles"]}


def pre_tendencia(b: np.ndarray, V: np.ndarray, es: list[int]) -> dict:
    """Wald (pré = 0) e inclinação de MQO nos pré-períodos, com o e = -1 (= 0) incluído."""
    wald = float(b @ np.linalg.solve(V, b))
    t = np.array([*es, -1], dtype=float)
    c = (t - t.mean()) / ((t - t.mean()) ** 2).sum()   # inclinação = c' [b; 0]
    c = c[:-1]
    incl, ep = float(c @ b), float(np.sqrt(c @ V @ c))
    return {"wald": wald, "wald_gl": len(b), "wald_p": float(stats.chi2.sf(wald, len(b))),
            "inclinacao": incl, "inclinacao_ep": ep,
            "inclinacao_p": float(2 * stats.norm.sf(abs(incl / ep)))}


def l_vec(alvo, npost: int) -> tuple[str, np.ndarray]:
    if alvo == "media":
        return f"média e = 0…{npost - 1}", np.full(npost, 1 / npost)
    return f"e = {alvo}", np.eye(npost)[int(alvo)]


def _tarefa(args) -> list[dict]:
    """Uma unidade de trabalho: Δ^RM para um Mbar, ou Δ^SD para toda a grade de M."""
    import honestdid as hd
    import torch

    torch.set_num_threads(1)
    nome, alvo, lv, rest, mbar, b, V, npre, npost = args
    if rest == "RM":
        r = hd.createSensitivityResults_relativeMagnitudes(
            b, V, npre, npost, l_vec=lv, Mbarvec=[mbar], gridPoints=HD["grade"])
        return [{"spec": nome, "alvo": alvo, "restricao": "RM", "parametro": x.Mbar,
                 "lb": x.lb, "ub": x.ub} for x in r.itertuples()]
    r = hd.createSensitivityResults(b, V, npre, npost, l_vec=lv, Mvec=HD["m"])
    return [{"spec": nome, "alvo": alvo, "restricao": "SD", "parametro": x.M, "lb": x.lb,
             "ub": x.ub} for x in r.itertuples()]


def ruptura(r: pd.DataFrame) -> pd.DataFrame:
    """Menor Mbar / M da grade em que o IC passa a incluir zero (breakdown)."""
    linhas = []
    for (sp, alvo, rest), g in r.groupby(["spec", "alvo", "restricao"], sort=False):
        if rest == "original":
            continue
        z = g[g["inclui_zero"]]["parametro"]
        linhas.append({"spec": sp, "alvo": alvo, "restricao": rest,
                       "ruptura": f"{z.min():g}" if len(z) else f"> {g['parametro'].max():g}"})
    return pd.DataFrame(linhas)


def _juntar(novo: pd.DataFrame, arquivo: str) -> pd.DataFrame:
    """Novas linhas no lugar das antigas das mesmas especificações, na ordem do settings."""
    arq = path("tabelas") / arquivo
    if not arq.exists():
        return novo
    antigo = pd.read_csv(arq)
    out = pd.concat([antigo[~antigo["spec"].isin(novo["spec"])], novo], ignore_index=True)
    ordem = {e["nome"]: i for i, e in enumerate(HD["especificacoes"])}
    return out.sort_values("spec", key=lambda x: x.map(ordem), kind="stable")


def figura(sp: Spec, es: dict, r: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    ev = es["ev"]
    ax = axes[0]
    ax.errorbar(ev["e"], ev["att"], yerr=1.96 * ev["ep"], fmt="o", color=AZUL,
                markersize=3.5, elinewidth=1, capsize=0)
    ax.scatter([-1], [0], color=CINZA, s=14, zorder=3)
    ax.axvline(-0.5, color="#a8a79f", linewidth=0.8, linestyle="--")
    pre = es["pre"]
    ax.set_title(f"{es['rotulo']} (limiar {sp.limiar:.0%}): event study CS, base universal",
                 fontsize=10, color=TINTA, loc="left")
    ax.set_xlabel(f"anos desde o tratamento — pré: Wald p = {pre['wald_p']:.2f}; inclinação "
                  f"{pre['inclinacao']:+.4f}/ano (ep {pre['inclinacao_ep']:.4f})",
                  fontsize=8, color=TINTA2)
    alvos = list(dict.fromkeys(r["alvo"]))
    for j, (rest, xlab) in enumerate([("RM", "Mbar (Δ^RM)"), ("SD", "M (Δ^SD)")], start=1):
        ax = axes[j]
        vals = sorted(r.loc[r["restricao"] == rest, "parametro"].unique())
        pos = {v: k + 1 for k, v in enumerate(vals)}
        for k, (alvo, cor) in enumerate(zip(alvos, [AZUL, TINTA2], strict=False)):
            g = r[(r["alvo"] == alvo) & (r["restricao"] == rest)]
            o = r[(r["alvo"] == alvo) & (r["restricao"] == "original")].iloc[0]
            desl = (k - 0.5) * 0.25
            ax.vlines([pos[v] + desl for v in g["parametro"]], g["lb"], g["ub"], color=cor,
                      linewidth=2, label=alvo)
            ax.vlines(desl, o["lb"], o["ub"], color=cor, linewidth=2, linestyle=":")
        ax.set_xticks([0, *pos.values()], ["orig.", *[f"{v:g}" for v in vals]], fontsize=7)
        ax.set_title(f"IC robusto, Δ^{rest}", fontsize=10, color=TINTA, loc="left")
        ax.set_xlabel(xlab, fontsize=8, color=TINTA2)
        if j == 1:
            ax.legend(frameon=False, fontsize=8, loc="upper left")
    for ax in axes:
        ax.axhline(0, color="#a8a79f", linewidth=0.8)
        ax.grid(axis="y", color=GRADE, linewidth=0.6)
        for lado in ["top", "right"]:
            ax.spines[lado].set_visible(False)
        ax.tick_params(colors=TINTA2, labelsize=8)
    fig.text(0.01, -0.03, "IC 95%. Δ^RM: violação pós ≤ Mbar × maior violação pré (entre anos "
             "consecutivos). Δ^SD: inclinação da tendência diferencial muda no máximo M por ano "
             "(M = 0: tendência linear extrapolada). Pontilhado: IC convencional. Cluster por "
             "microrregião.", fontsize=8, color=TINTA2)
    fig.tight_layout()
    fig.savefig(path("figuras") / f"s08_honestdid_{sp.nome}.png", dpi=200, facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    import honestdid as hd

    nomes = [a for a in sys.argv[1:] if not a.startswith("-")]
    specs, parcial = especificacoes(nomes), bool(nomes)
    p = com_luzes_por_produto(carregar())
    estudos, linhas, tarefas, pre = {}, [], [], []
    for sp in specs:
        es = estudos[sp.nome] = event_study(p, sp)
        pre.append({"spec": sp.nome, "desfecho": es["rotulo"], "limiar": sp.limiar,
                    "tratados": es["n_tratados"], "controles": es["n_controles"], **es["pre"]})
        for a in sp.alvos:
            alvo, lv = l_vec(a, es["npost"])
            o = hd.constructOriginalCS(es["b"], es["V"], es["npre"], es["npost"], l_vec=lv)
            linhas.append({"spec": sp.nome, "alvo": alvo, "restricao": "original",
                           "parametro": np.nan, "lb": float(o["lb"].iloc[0]),
                           "ub": float(o["ub"].iloc[0])})
            base = (es["b"], es["V"], es["npre"], es["npost"])
            tarefas += [(sp.nome, alvo, lv, "RM", m, *base) for m in HD["mbar"]]
            tarefas.append((sp.nome, alvo, lv, "SD", None, *base))
        print(f"[{sp.nome}] {es['rotulo']}, limiar {sp.limiar:.0%}: {es['n_tratados']} tratados,"
              f" {es['n_controles']} controles; pré Wald p = {es['pre']['wald_p']:.3f}, "
              f"inclinação {es['pre']['inclinacao']:+.4f} ({es['pre']['inclinacao_ep']:.4f})",
              flush=True)
    t = time.time()
    n_proc = max(1, min(len(tarefas), HD["processos"], (os.cpu_count() or 2) - 2))
    # um thread de BLAS por processo: com o padrão (um por núcleo em cada processo) o OpenBLAS
    # esgota a memória; os processos filhos herdam o ambiente
    for v in ["OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[v] = "1"
    print(f"{len(tarefas)} tarefas em {n_proc} processos", flush=True)
    with ProcessPoolExecutor(n_proc) as ex:
        for res in ex.map(_tarefa, tarefas):
            linhas += res
    print(f"  {time.time() - t:.0f}s", flush=True)

    ordem = {(sp.nome): i for i, sp in enumerate(specs)}
    r = pd.DataFrame(linhas)
    r["inclui_zero"] = (r["lb"] <= 0) & (r["ub"] >= 0)
    r["_o"] = r["spec"].map(ordem)
    r["_r"] = r["restricao"].map({"original": 0, "RM": 1, "SD": 2})
    r = r.sort_values(["_o", "alvo", "_r", "parametro"], kind="stable").drop(columns=["_o", "_r"])
    r.insert(1, "desfecho", r["spec"].map({k: v["rotulo"] for k, v in estudos.items()}))
    r.insert(2, "limiar", r["spec"].map({sp.nome: sp.limiar for sp in specs}))
    rup, pre = ruptura(r), pd.DataFrame(pre)
    if parcial:   # rodada só de algumas especificações: preserva as demais nas tabelas
        r, rup, pre = (_juntar(x, arq) for x, arq in [
            (r, "s08_honestdid.csv"), (rup, "s08_honestdid_ruptura.csv"),
            (pre, "s08_honestdid_pretendencia.csv")])
    salvar_tabela(r, "s08_honestdid", "HonestDiD: IC 95% robustos a violações de tendências "
                  "paralelas (Δ^RM e Δ^SD), event study CS com base universal", casas=4)
    rup.to_csv(path("tabelas") / "s08_honestdid_ruptura.csv", index=False)
    pre.to_csv(path("tabelas") / "s08_honestdid_pretendencia.csv", index=False)
    for sp in specs:
        figura(sp, estudos[sp.nome], r[r["spec"] == sp.nome])
    with pd.option_context("display.width", 200):
        print(r.round(4).to_string(index=False))
        print("\nRuptura (menor valor da grade com IC incluindo zero):")
        print(rup.to_string(index=False))
        print("\nPré-tendência:")
        print(pre.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
