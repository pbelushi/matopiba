# Agro no Matopiba e qualidade de vida

Pipeline de dados e análise sobre os efeitos da expansão agrícola no Matopiba (MA, TO, PI, BA)
sobre renda, emprego, saúde, educação e desigualdade, de 1985 a 2025, com municípios do Cerrado
fora do Matopiba como controles.

- Etapas, entradas e critérios de aceite: [`CLAUDE.md`](CLAUDE.md)
- Status e scripts de cada etapa: [`docs/PIPELINE.md`](docs/PIPELINE.md)
- Decisões metodológicas (e por quê): [`docs/DECISOES.md`](docs/DECISOES.md)
- Fontes, versões e datas de acesso: [`data/SOURCES.md`](data/SOURCES.md)
- Variáveis dos painéis: [`docs/DICIONARIO.md`](docs/DICIONARIO.md)

## Estrutura

```
config/settings.yaml      todos os parâmetros (projetos GCP, anos, classes, limiares, fontes)
src/matopiba/             s00_…s08_* (uma etapa por script), analise.py, tarefas.py (executor)
data/raw/                 downloads (fora do git)
data/interim/             saídas intermediárias por etapa (fora do git)
data/processed/           universo e painéis finais
outputs/{figuras,tabelas,logs}/
tests/                    testes dos painéis e do estimador de Callaway–Sant'Anna
```

## Reproduzir do zero

### 1. Passos manuais (uma vez)

1. **Projeto no Google Cloud** com as APIs do **Earth Engine** e do **BigQuery** habilitadas.
2. **Registrar o projeto no Earth Engine** (uso não comercial):
   `https://console.cloud.google.com/earth-engine/configuration?project=<ID>`.
3. **Inicializar os assets do projeto no Earth Engine:** abra
   `https://code.earthengine.google.com/?project=<ID>`, aba **Assets → NEW → Folder**, e crie a pasta
   `matopiba`. A Etapa 4 guarda ali a malha municipal e os resultados dos tasks batch.
4. **Preencher o ID do projeto** (o ID, não o nome nem uma chave de API) em
   `config/settings.yaml` → `gcp.gee_project` e `gcp.billing_project`, ou nas variáveis de
   ambiente `MATOPIBA_GEE_PROJECT` / `MATOPIBA_BILLING_PROJECT`.
5. **Autenticar** (abre o navegador; as credenciais servem também para o BigQuery):
   ```
   python -c "import ee; ee.Authenticate()"
   ```
6. **Opcional — conflitos no campo (CPT):** os dados por município e ano são obtidos com a
   Comissão Pastoral da Terra (CEDOC). Salve como `data/raw/cpt/conflitos_municipio_ano.csv`
   (colunas mínimas `id_municipio`, `ano`). Sem o arquivo, o bloco fica marcado como pendente.

Todos os demais dados (IBGE, MapBiomas, GAEZ, Pink Sheet, INEP, Base dos Dados, Earth Engine)
são baixados ou consultados pelos próprios scripts.

### 2. Ambiente

Python 3.11+ (testado em 3.13). Com `uv`:

```
uv venv .venv && uv pip install -r requirements.lock && uv pip install --no-deps -e .
```

ou com o `venv` padrão:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m pip install --no-deps -e .
```

> Máquina do Banco Mundial (OneDrive + Application Control): crie o venv fora do OneDrive
> (`%USERPROFILE%\.venvs\matopiba`) a partir de `C:\WBG\Python313\python.exe`; o `uv` serve só
> como instalador (`python -m uv pip install --python <venv>\Scripts\python.exe …`). Executáveis
> como `ruff.exe` e `earthengine.exe` são bloqueados — use os comandos via `python -m` / `-c`.

### 3. Rodar

```
python -m matopiba.tarefas lista        # alvos disponíveis
python -m matopiba.tarefas etapa0       # confere as autenticações
python -m matopiba.tarefas all testes   # pipeline completo + testes
python -m matopiba.tarefas analise      # só a análise (Etapa 8), a partir dos painéis
```

Com `make`: `make all`, `make etapa3`, `make analise` etc. (o Makefile chama o mesmo executor).
O tempo de cada etapa vai para `outputs/logs/tempos.csv`; o aceite de cada etapa, para
`outputs/logs/`.

### Opcional: HonestDiD (sensibilidade a tendências paralelas)

`s08_honestdid` usa o pacote `honestdid` (port Python do HonestDiD do R), que exige
`numpy < 2.4` e PyTorch. Por isso roda em um ambiente separado, fora do `all`:

```
python -m venv %USERPROFILE%\.venvs\matopiba_honestdid
python -m uv pip install --native-tls --python %USERPROFILE%\.venvs\matopiba_honestdid\Scripts\python.exe ^
    -r requirements.lock honestdid==0.1.1 --override overrides_honestdid.txt ^
    --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu
python -m uv pip install --python %USERPROFILE%\.venvs\matopiba_honestdid\Scripts\python.exe --no-deps -e .
make honestdid PY_HD=%USERPROFILE%\.venvs\matopiba_honestdid\Scripts\python.exe
```

Cerca de 40 minutos para as 7 especificações de `analise.honestdid` (8 processos em paralelo, ~1 GB de RAM cada; o teste condicional de Δ^RM domina). Validação do port contra o README do pacote R em
`docs/DECISOES.md`.

### Custos e tempos

- **BigQuery (Base dos Dados):** cerca de 200 GB processados na Etapa 5 (dentro da franquia
  gratuita de 1 TB/mês). Toda consulta passa por um dry run com limite de GB.
- **Earth Engine:**
  - Etapa 3 (luzes): cálculo interativo, cerca de 15 minutos por produto. Os resultados ficam em
    cache em `data/interim/_cache_luzes_*.parquet`; use `--refazer` para recalcular.
  - Etapa 4 (Open Buildings): 8 tasks batch, cerca de 60 EECU-horas. Os resultados ficam como
    assets em `projects/<ID>/assets/matopiba/construido_<ano>`; se existirem, não são
    recalculados (use `python -m matopiba.s04_construido --refazer` para forçar).
- **Execução completa em ambiente limpo (20/10/2026): 57 min**, mais 4 min de instalação do venv.
  As luzes (32 min) dominam o tempo. Por etapa: 0: 22 s · 1: 4,6 min · 2: 1,3 min · 3: 32 min ·
  4: 2 min (assets já existentes) · 5: 6,8 min · 6: 3,7 min · 7: 11 s · testes: 45 s ·
  8: 4,5 min. Detalhes em `outputs/logs/etapa9_reproducao.md`; os tempos de cada execução
  vão para `outputs/logs/tempos.csv`.

## Resultados principais

Ver `outputs/tabelas/` e `outputs/figuras/`, e o resumo e as ressalvas em `docs/DECISOES.md`.
