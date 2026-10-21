# Etapa 9 — execução do pipeline em ambiente limpo (20/10/2026)

**Ambiente:** venv novo (`%USERPROFILE%\.venvs\matopiba_limpo`, Python 3.13), instalado a partir
de `requirements.lock` em 4 min. Antes de rodar, `data/raw`, `data/interim`, `data/processed` e
`outputs/` foram movidos para `data/_backup_pre_etapa9/`. Todos os downloads (IBGE, geobr,
MapBiomas, INEP, GAEZ, Pink Sheet) e as consultas (Base dos Dados, Earth Engine) foram refeitos.
Os assets da Etapa 4 no Earth Engine (resultado dos tasks batch) foram reaproveitados.

**Comando:** `python -m matopiba.tarefas all testes` (log completo em `etapa9_execucao_limpa.txt`).

| Etapa | Script | Tempo |
|---|---|---:|
| 0 Setup | s00_check_auth | 22 s |
| 1 Universo | s01_universo | 4,6 min |
| 2 Uso da terra | s02_mapbiomas | 1,3 min |
| 3 Luzes | s03_luzes | 32,0 min |
| 4 Área construída | s04_construido (assets já existentes) | 2,0 min |
| 5 Socioeconômicos | s05_socio | 6,8 min |
| 6 Instrumento | s06_instrumento | 3,7 min |
| 7 Painéis | s07_paineis | 11 s |
| — Testes (após a Etapa 7) | pytest, 15 testes | 45 s |
| 8 Análise | s08_descritiva, did, iv, censos, heterogeneidade, robustez | 4,5 min |
| — Testes (final) | pytest, 15 testes | 44 s |
| **Total** | | **57 min** |

Se os assets da Etapa 4 não existirem, somam-se 8 tasks batch no Earth Engine (cerca de
60 EECU-horas; algumas horas de fila).

**Incidente:** na primeira tentativa, o servidor do INEP derrubou a conexão no download do IDEB
(`WinError 10054`). O download passou a ter até 5 tentativas com espera crescente. A execução foi
retomada da Etapa 5 em diante (a 2ª tentativa de download passou). O tempo da Etapa 5 é o da
retomada.

**Comparação com a execução anterior:** os 20 parquets (`data/processed`, `data/interim`) e as
13 tabelas CSV de `outputs/tabelas` são idênticos aos do backup (diferença máxima 0, mesmos NaN).
Todas as figuras foram regeneradas.

**Pendente:** conflitos no campo (CPT), que dependem de download manual.
