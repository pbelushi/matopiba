# Pipeline

| Etapa | Script | Saída principal | Status |
|---|---|---|---|
| 0 Setup | `s00_check_auth.py` | — | concluída |
| 1 Universo | `s01_universo.py` | `data/processed/universo.parquet`, `crosswalk_mun_amc.parquet` | concluída (aceite ok) |
| 2 Uso da terra | `s02_mapbiomas.py` | `data/interim/mapbiomas_mun_ano.parquet` | concluída (aceite ok nos grupos de análise) |
| 3 Luzes noturnas | `s03_luzes.py` | `data/interim/luzes_mun_ano.parquet` | concluída (aceite ok; per capita após a Etapa 5) |
| 4 Área construída | `s04_construido.py` | `data/interim/construido_mun_ano.parquet` | concluída (aceite ok) |
| 4b Máscara urbana | `s04b_urbano.py`, `s04b_mapas.py` | `data/interim/urbano_mun_ano.parquet` | concluída (aceite ok; Open Buildings só 2016 e 2023) |
| 5 Socioeconômicos | `s05_socio.py` | `data/interim/socio_*.parquet` | concluída (aceite ok; CPT pendente) |
| 6 Instrumento | `s06_instrumento.py` | `data/interim/instrumento.parquet` | concluída (aceite ok; instrumento BCP, forte em diferenças longas) |
| 7 Painéis | `s07_paineis.py` | `data/processed/painel_*.parquet` | concluída (13 testes ok) |
| 8 Análise | `s08_*.py`, `tarefas.py` | `outputs/tabelas`, `outputs/figuras` | concluída (`python -m matopiba.tarefas analise`; HonestDiD: `make honestdid`, ambiente opcional) |
| 9 Reprodutibilidade | `Makefile`, `tarefas.py`, `README.md` | `outputs/logs/tempos.csv`, `etapa9_reproducao.md` | concluída (execução limpa em 57 min; saídas idênticas) |
