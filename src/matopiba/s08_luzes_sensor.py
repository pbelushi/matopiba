"""Etapa 8.6c: efeito de longo prazo nas luzes dentro de um único sensor.

A série principal encadeia Li-DMSP (até 2013) e VIIRS (2013+). Em log, o fator de
encadeamento é constante por município e some no efeito fixo: antes de 2013 a série principal
equivale ao Li-DMSP, e depois ao VIIRS. A emenda só pesa nas comparações que atravessam 2013
(coortes antigas observadas no período VIIRS), justamente as que formam o efeito de longo
prazo. Aqui o DiD é refeito com cada produto isolado:

  Li-DMSP    1992–2013  DMSP intercalibrado (Li et al. 2020), coortes até 2013
  DMSP bruto 1992–2013  sem intercalibração (o efeito fixo de ano absorve o satélite)
  VIIRS      2013–2025  VIIRS anual oficial, coortes 2014+
  Chen       2000–2024  VIIRS-like (Chen et al. 2021); quebra de nível 2011–2013 maior no
                        Matopiba do que no Cerrado fora (ver DECISOES), viés a favor de efeito

Mesma amostra, tratamento e estimador do s08_did (CS, controles nunca tratados, painel
balanceado na janela, cluster por microrregião).

Saídas:
  outputs/tabelas/s08_luzes_sensor.{csv,tex}
  outputs/figuras/s08_luzes_sensor.png
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from matopiba.analise import (amostra_did, carregar, com_luzes_por_produto, cs_did, desfecho,
                              estrelas, preparar_desfecho, salvar_tabela)
from matopiba.config import path

AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#8a897f", "#1c1c1a", "#5f5e5a", "#e4e3df"
SERIES = [("log_luz_pc", "Encadeada (principal)"), ("log_luz_li_pc", "Li-DMSP"),
          ("log_luz_dmsp_pc", "DMSP bruto"), ("log_luz_viirs_pc", "VIIRS"),
          ("log_luz_chen_pc", "Chen (VIIRS-like)")]
JANELA = (-5, 20)
HORIZONTES = [(0, 5), (6, 10), (11, 20)]


def media_horizonte(ev: pd.DataFrame, V: pd.DataFrame, a: int, b: int) -> tuple[float, float]:
    es = [e for e in range(a, b + 1) if e in V.index]
    if not es:
        return np.nan, np.nan
    w = np.full(len(es), 1 / len(es))
    att = float(w @ ev.set_index("e").loc[es, "att"].to_numpy())
    return att, float(np.sqrt(w @ V.loc[es, es].to_numpy() @ w))


def estimar(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = amostra_did(p)
    linhas, eventos = [], []
    for nome, rot in SERIES:
        d = desfecho(nome)
        x = s.assign(y=preparar_desfecho(s, d)).dropna(subset=["y"])
        x = x[x.groupby("unidade")["ano"].transform("nunique") == x["ano"].nunique()]
        cs = cs_did(x, "y", balancear=False)
        csu = cs_did(x, "y", balancear=False, base="universal")
        sm = cs["simples"]
        ev, V = csu["evento"], csu["vcov_evento"]
        pre = [e for e in range(-5, -1) if e in V.index]
        bp = ev.set_index("e").loc[pre, "att"].to_numpy()
        wald = float(bp @ np.linalg.solve(V.loc[pre, pre].to_numpy(), bp))
        linha = {"série": rot, "anos": sm["anos"], "ATT": sm["att"], "ep": sm["ep"],
                 "p": sm["p"], "tratados": sm["n_unidades_tratadas"],
                 "controles": sm["n_controles"], "coortes": sm["n_coortes"],
                 "pré Wald p (e=-5…-2)": float(stats.chi2.sf(wald, len(pre)))}
        for a, b in HORIZONTES:
            att, ep = media_horizonte(ev, V, a, b)
            linha[f"média e={a}…{b}"] = att
            linha[f"ep e={a}…{b}"] = ep
        linhas.append(linha)
        eventos.append(ev[ev["e"].between(*JANELA)].assign(serie=rot))
        print(f"  {rot}: ATT {sm['att']:.4f}{estrelas(sm['p'])} ({sm['ep']:.4f}), "
              f"{sm['n_unidades_tratadas']} tratados", flush=True)
    return pd.DataFrame(linhas), pd.concat(eventos, ignore_index=True)


def figura(ev: pd.DataFrame) -> None:
    series = [r for _, r in SERIES]
    fig, axes = plt.subplots(1, len(series), figsize=(18, 4.2), sharey=True)
    for ax, rot in zip(axes, series, strict=True):
        e = ev[ev["serie"] == rot]
        ax.errorbar(e["e"], e["att"], yerr=1.96 * e["ep"], fmt="o", color=AZUL,
                    markersize=3, elinewidth=1, capsize=0)
        ax.scatter([-1], [0], color=CINZA, s=12, zorder=3)
        ax.axhline(0, color="#a8a79f", linewidth=0.8)
        ax.axvline(-0.5, color="#a8a79f", linewidth=0.8, linestyle="--")
        ax.set_title(rot, fontsize=10, color=TINTA, loc="left")
        ax.set_xlabel("anos desde o tratamento", fontsize=8, color=TINTA2)
        ax.grid(axis="y", color=GRADE, linewidth=0.6)
        for lado in ["top", "right"]:
            ax.spines[lado].set_visible(False)
        ax.tick_params(colors=TINTA2, labelsize=8)
    fig.suptitle("Luzes per capita por sensor: event study CS (base universal, e = -1)",
                 x=0.01, ha="left", fontsize=12, color=TINTA)
    fig.text(0.01, -0.03, "IC 95%, cluster por microrregião. Cada painel usa um único produto "
             "e só as coortes tratadas dentro do seu período; horizontes longos vêm de poucas "
             "coortes. Chen tem quebra de nível em 2011–2013.", fontsize=8, color=TINTA2)
    fig.tight_layout()
    fig.savefig(path("figuras") / "s08_luzes_sensor.png", dpi=200, facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    tab, ev = estimar(com_luzes_por_produto(carregar()))
    salvar_tabela(tab, "s08_luzes_sensor", "Luzes per capita por sensor: ATT de "
                  "Callaway–Sant'Anna e médias do event study por horizonte", casas=4)
    figura(ev)
    with pd.option_context("display.width", 250):
        print(tab.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
