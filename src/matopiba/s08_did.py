"""Etapa 8.2: DiD escalonado (Callaway–Sant'Anna) com event study, e TWFE para comparação.

Tratamento: primeiro ano em que a agricultura temporária passa de 10% da área do município.
Amostra: Matopiba + Cerrado fora, sem municípios já tratados em 1985; controles = nunca
tratados; painel balanceado na janela de cada desfecho; cluster por microrregião.

Saídas:
  outputs/tabelas/s08_did_resumo.{csv,tex}      ATT agregado (CS) e coeficiente TWFE
  outputs/tabelas/s08_did_evento.csv            event study CS e TWFE, por desfecho
  outputs/figuras/s08_did_event_study.png

Uso: python -m matopiba.s08_did
"""

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from matopiba.analise import (CFG, DESFECHOS, amostra_did, carregar, cs_did, estrelas,
                              preparar_desfecho, salvar_tabela, twfe, twfe_evento)
from matopiba.config import path

AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#8a897f", "#1c1c1a", "#5f5e5a", "#e4e3df"


def estimar(s: pd.DataFrame, rotulo_amostra: str = "principal") -> tuple[pd.DataFrame,
                                                                          pd.DataFrame]:
    resumo, eventos = [], []
    jan = tuple(CFG["janela_evento"])
    for d in DESFECHOS:
        x = s.assign(y=preparar_desfecho(s, d))
        # mesma amostra balanceada para CS e TWFE
        x = x.dropna(subset=["y"])
        x = x[x.groupby("unidade")["ano"].transform("nunique") == x["ano"].nunique()]
        cs = cs_did(x, "y", balancear=False)
        tw = twfe(x, "y", "tratado")
        ev_tw = twfe_evento(x, "y", janela=jan).assign(estimador="TWFE")
        ev_cs = cs["evento"].rename(columns={"att": "coef"})[["e", "coef", "ep"]]
        ev_cs = ev_cs[ev_cs["e"].between(*jan)].assign(estimador="CS")
        csu = cs_did(x, "y", balancear=False, base="universal")["evento"]
        ev_csu = csu.rename(columns={"att": "coef"})[["e", "coef", "ep"]]
        ev_csu = ev_csu[ev_csu["e"].between(*jan)].assign(estimador="CS universal")
        eventos.append(pd.concat([ev_cs, ev_csu, ev_tw]).assign(desfecho=d.nome,
                                                                amostra=rotulo_amostra))
        sm = cs["simples"]
        resumo.append({
            "desfecho": d.rotulo, "anos": sm["anos"],
            "CS ATT": sm["att"], "CS ep": sm["ep"], "CS p": sm["p"],
            "TWFE": tw["coef"], "TWFE ep": tw["ep"], "TWFE p": tw["p"],
            "pré-tendência (média ATT e<0)": sm["pre_media"],
            "tratados": sm["n_unidades_tratadas"], "controles": sm["n_controles"],
            "coortes": sm["n_coortes"], "amostra": rotulo_amostra,
        })
        print(f"  {d.nome}: CS {sm['att']:.4f}{estrelas(sm['p'])} ({sm['ep']:.4f}) | "
              f"TWFE {tw['coef']:.4f}{estrelas(tw['p'])} ({tw['ep']:.4f})", flush=True)
    return pd.DataFrame(resumo), pd.concat(eventos, ignore_index=True)


ROT_EST = {"CS": "Callaway–Sant'Anna (base varying)", "TWFE": "TWFE",
           "CS universal": "Callaway–Sant'Anna (base universal, e = -1)"}


def figura(ev: pd.DataFrame, series: list[tuple[str, str, float]], arquivo: str,
           titulo: str, nota: str) -> None:
    fig, axes = plt.subplots(1, len(DESFECHOS), figsize=(3.4 * len(DESFECHOS), 4.2), sharex=True)
    for ax, d in zip(axes, DESFECHOS, strict=True):
        for est, cor, desl in series:
            e = ev[(ev["desfecho"] == d.nome) & (ev["estimador"] == est)].sort_values("e")
            ax.errorbar(e["e"] + desl, e["coef"], yerr=1.96 * e["ep"], fmt="o", color=cor,
                        markersize=3.5, elinewidth=1, capsize=0, label=ROT_EST[est])
        ax.axhline(0, color="#a8a79f", linewidth=0.8)
        ax.axvline(-0.5, color="#a8a79f", linewidth=0.8, linestyle="--")
        ax.set_title(d.rotulo, fontsize=10, color=TINTA, loc="left")
        ax.set_xlabel("anos desde o tratamento", fontsize=8, color=TINTA2)
        ax.grid(axis="y", color=GRADE, linewidth=0.6)
        for lado in ["top", "right"]:
            ax.spines[lado].set_visible(False)
        ax.tick_params(colors=TINTA2, labelsize=8)
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=12, color=TINTA)
    fig.text(0.01, -0.03, nota, fontsize=8, color=TINTA2)
    fig.tight_layout()
    fig.savefig(path("figuras") / arquivo, dpi=200, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    s = amostra_did(carregar())
    resumo, ev = estimar(s)
    salvar_tabela(resumo.drop(columns="amostra"), "s08_did_resumo",
                  "DiD escalonado: ATT agregado de Callaway–Sant'Anna e TWFE convencional "
                  "(tratamento: agricultura temporária >= 10% da área)", casas=4)
    ev.to_csv(path("tabelas") / "s08_did_evento.csv", index=False)
    base = ("Controles: municípios nunca tratados do Matopiba e do Cerrado fora; IC 95%, "
            "cluster por microrregião. ")
    figura(ev, [("TWFE", CINZA, 0.15), ("CS", AZUL, -0.15)], "s08_did_event_study.png",
           "Event study: agricultura temporária >= 10% da área",
           base + "TWFE com leads/lags agrupados nas pontas e referência e = -1; CS com base "
           "'varying' (pré-períodos comparam t com t-1).")
    figura(ev, [("CS universal", AZUL, 0.0)], "s08_did_event_study_universal.png",
           "Event study (CS, base universal): pré-tendências acumuladas em relação a e = -1",
           base + "Todos os períodos comparados com o ano anterior ao tratamento.")
    print(resumo.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
