"""Etapa 8.3: IV / shift-share no painel anual.

2SLS de cada desfecho na participação da soja na área, instrumentada pelo ganho tecnológico
GAEZ × pós-2003 (Bustos, Caprettini e Ponticelli, 2016); alternativa: × tendência e o
instrumento de preço do CLAUDE.md. Efeitos fixos de município e ano; cluster por microrregião.
Com um instrumento, o F efetivo de Montiel Olea–Pflueger coincide com o F robusto (t²) do
primeiro estágio. Intervalo de Anderson-Rubin (robusto a instrumento fraco) por inversão.

Saídas:
  outputs/tabelas/s08_iv_painel.{csv,tex}

Uso: python -m matopiba.s08_iv
"""

import sys

import pandas as pd

from matopiba.analise import CFG, DESFECHOS, carregar, estrelas, iv_fe, preparar_desfecho, salvar_tabela
from matopiba.config import settings

INSTRUMENTOS = {
    "z_bcp_pos": "ganho tecnológico × pós-2003",
    "z_bcp_tend": "ganho tecnológico × tendência",
    "z_yl_alto_l1": "potencial × log preço (t-1)",
}


def amostra_iv(p: pd.DataFrame) -> pd.DataFrame:
    return p[p["grupo"].isin(CFG["grupos"])].copy()


def estimar(s: pd.DataFrame, instrumentos=None, rotulo: str = "principal",
            x: str | None = None, controles: list[str] | None = None) -> pd.DataFrame:
    x = x or settings()["instrumento"]["tratamento_principal"]
    linhas = []
    for d in DESFECHOS:
        sd = s.assign(y=preparar_desfecho(s, d))
        for z in instrumentos or INSTRUMENTOS:
            r = iv_fe(sd, "y", x, z, controles=controles)
            linhas.append({"desfecho": d.rotulo, "instrumento": INSTRUMENTOS.get(z, z),
                           "amostra": rotulo, **r})
            print(f"  {d.nome} | {z}: 2SLS {r['iv_coef']:.3f}{estrelas(r['iv_p'])} "
                  f"(ep {r['iv_ep']:.3f}), F {r['F_efetivo']:.1f}, AR [{r['ar_ic_inf']:.2f}, "
                  f"{r['ar_ic_sup']:.2f}]", flush=True)
    return pd.DataFrame(linhas)


def formatar(t: pd.DataFrame) -> pd.DataFrame:
    cols = ["desfecho", "instrumento", "ols_coef", "ols_ep", "fs_coef", "fs_ep", "F_efetivo",
            "rf_coef", "rf_ep", "iv_coef", "iv_ep", "iv_p", "ar_ic_inf", "ar_ic_sup", "n",
            "n_unidades", "n_clusters"]
    return t[cols].rename(columns={
        "ols_coef": "OLS", "ols_ep": "OLS ep", "fs_coef": "1º estágio", "fs_ep": "1º ep",
        "F_efetivo": "F efetivo", "rf_coef": "forma reduzida", "rf_ep": "FR ep",
        "iv_coef": "2SLS", "iv_ep": "2SLS ep", "iv_p": "2SLS p", "ar_ic_inf": "AR 95% inf",
        "ar_ic_sup": "AR 95% sup"})


def main() -> int:
    s = amostra_iv(carregar())
    t = estimar(s)
    salvar_tabela(formatar(t), "s08_iv_painel",
                  "IV no painel anual: participação da soja na área instrumentada (EF de "
                  "município e ano; cluster por microrregião; IC de Anderson-Rubin)", casas=3)
    print(formatar(t).round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
