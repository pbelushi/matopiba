# Pipeline — Agro no Matopiba e qualidade de vida

Execute as etapas na ordem. Cada etapa tem entradas, saídas e critérios de aceite.
Ao terminar uma etapa, pare e reporte antes de seguir para a próxima.

---

## Etapa 0 — Setup

**Fazer**
- Estrutura de pastas:
  ```
  config/settings.yaml
  data/{raw,interim,processed}/  data/SOURCES.md
  docs/{PIPELINE.md,DECISOES.md}
  src/matopiba/
  notebooks/
  outputs/{figuras,tabelas,logs}/
  tests/
  ```
- `pyproject.toml` com `uv`. Pacotes base: `pandas`, `pyarrow`, `geopandas`, `geobr`,
  `earthengine-api`, `geemap`, `basedosdados`, `rasterio`, `rasterstats`, `pyyaml`,
  `linearmodels`, `statsmodels`, `differences`, `matplotlib`, `pytest`, `ruff`.
- Script `src/matopiba/s00_check_auth.py` que testa:
  - autenticação no Earth Engine (`ee.Initialize(project=...)`), com o ID do projeto vindo do
    `settings.yaml`;
  - acesso ao Base dos Dados com o billing project do Google Cloud, via um dry run pequeno.
- `.gitignore` excluindo `data/raw`, `data/interim` e credenciais.

**Eu preciso fazer manualmente** (me avise se faltar):
- `earthengine authenticate` e um projeto no Google Cloud com Earth Engine habilitado;
- billing project configurado para o Base dos Dados.

**Aceite**: `python -m matopiba.s00_check_auth` passa nos dois testes.

---

## Etapa 1 — Universo de análise

**Fazer**
- Obter a lista oficial de municípios do Matopiba (delimitação Embrapa/GITE, 337 municípios).
  Se não houver arquivo baixável, me diga onde está a lista e eu forneço.
- Malha municipal via `geobr` (ano mais recente disponível) e bioma via `geobr.read_biomes`.
- Montar `data/processed/universo.parquet` com: `id_municipio`, nome, UF, microrregião, região
  imediata, área (ha), `matopiba` (bool), `cerrado_share` (fração da área no Cerrado) e
  `grupo` (`matopiba` | `cerrado_fora` | `outros`).
- Crosswalk município → AMC 1991–2022. Proponha a fonte e me pergunte antes de fixar.

**Aceite**
- 337 municípios com `matopiba=True`, distribuídos entre as 4 UFs.
- A soma das áreas bate com a área oficial do Matopiba (tolerância de 1%).
- Todo município do universo tem AMC atribuída.
- Mapa de conferência em `outputs/figuras/universo.png`.

---

## Etapa 2 — Uso e cobertura da terra (tratamento)

**Fazer**
- Fonte preferencial: estatísticas municipais da coleção mais recente do MapBiomas (área por
  classe, município e ano, 1985 até o último ano). Confirme a coleção vigente e a legenda.
- Classes de interesse (confirme os códigos na legenda da coleção usada): soja, outras lavouras
  temporárias, algodão, cana, lavouras perenes, pastagem, mosaico de usos, formações florestal,
  savânica e campestre.
- Derivar por município e ano: `area_soja_ha`, `area_agri_temp_ha` (soja + temporárias +
  algodão), `area_pasto_ha`, `area_nativa_ha`, as participações de cada uma na área municipal e
  o desmatamento anual (perda de vegetação nativa).
- Validação cruzada: para uma amostra de 10 municípios e 3 anos, recalcular a área de soja no
  Earth Engine (asset de integração do MapBiomas, `reduceRegion` com `ee.Image.pixelArea()`) e
  comparar com a tabela.

**Saída**: `data/interim/mapbiomas_mun_ano.parquet`

**Aceite**
- Painel balanceado (todos os municípios × todos os anos).
- Soma das classes ≈ área do município (tolerância de 2%).
- Divergência entre tabela e Earth Engine < 3% na amostra.
- Figura: evolução da área de soja no Matopiba versus no Cerrado fora do Matopiba.

---

## Etapa 3 — Luzes noturnas

**Fazer**
- DMSP-OLS anual (1992–2013) e VIIRS anual (2012+) no catálogo do Earth Engine. Confirme os IDs
  atuais dos datasets.
- Para cada município e ano: soma de radiância, média e radiância per capita (a população vem da
  Etapa 5).
- Harmonização: proponha duas opções, por exemplo (a) usar um produto já harmonizado
  DMSP-VIIRS publicado na literatura, baixado manualmente, ou (b) séries separadas com
  calibração no período de sobreposição. Me pergunte antes de escolher.
- Máscara para queimadas/gás e para pixels de corpos d'água, se o produto não tratar.

**Saída**: `data/interim/luzes_mun_ano.parquet`

**Aceite**
- Sem municípios faltando nos anos cobertos.
- Correlação positiva entre luzes e PIB municipal no corte transversal (sanity check).
- Figura comparando DMSP e VIIRS na sobreposição.

---

## Etapa 4 — Área construída

**Fazer**
- Verifique se o Open Buildings Temporal do Google (Earth Engine) cobre o Brasil. Se cobrir,
  calcule a área construída e a altura média por município e ano.
- Alternativa ou complemento: classe de área urbanizada do MapBiomas (já disponível na Etapa 2).

**Saída**: `data/interim/construido_mun_ano.parquet`

**Aceite**: cobertura documentada em `data/SOURCES.md`; série sem saltos espúrios (apontar anos
com variação > 50%).

---

## Etapa 5 — Indicadores socioeconômicos

Use o Base dos Dados (BigQuery) quando possível; SIDRA/IBGE e fontes oficiais como alternativa.
**Confirme os IDs de tabela via busca do Base dos Dados antes de consultar.** Filtre no SQL pelos
municípios do universo e agregue no servidor. Nunca baixe microdados inteiros.

| Bloco | Variáveis | Fonte provável |
|---|---|---|
| População | população anual, estimativas e censos | IBGE |
| PIB | PIB total, VA agropecuário/indústria/serviços, PIB per capita (deflacionado, IPCA) | PIB dos Municípios/IBGE |
| Emprego formal | vínculos ativos, massa salarial, salário médio, por setor (agro vs. resto) | RAIS (agregada por município-ano) |
| Saúde | nascidos vivos, óbitos < 1 ano → taxa de mortalidade infantil; pré-natal adequado | SINASC, SIM (DATASUS) |
| Educação | IDEB anos iniciais/finais, matrículas | INEP |
| Desenvolvimento | IDHM e componentes, Gini, % pobres, renda per capita | Atlas Brasil (1991, 2000, 2010) |
| Censo 2022 | renda, saneamento, alfabetização (o que estiver disponível no nível municipal) | IBGE |
| Transferências | famílias no Bolsa Família / CadÚnico | MDS |
| Estrutura fundiária | Gini da terra, estabelecimentos por tamanho | Censo Agro 2006 e 2017 (SIDRA) |
| Migração | % de não naturais do município/UF | Censos |
| Conflitos no campo | ocorrências por município-ano | CPT (provável download manual) |

**Saída**: um parquet por bloco em `data/interim/socio_*.parquet`

**Aceite**
- Relatório de cobertura (`outputs/logs/cobertura_socio.md`) mostrando, por variável, o
  intervalo de anos e o % de municípios com dado.
- Mortalidade infantil calculada como óbitos < 1 ano / nascidos vivos × 1000, com sinalização
  de municípios com menos de 50 nascidos vivos (taxa instável).
- Valores monetários em reais constantes, com ano-base documentado.

---

## Etapa 6 — Instrumento (potencial agronômico)

**Fazer**
- FAO-GAEZ v4: rendimento potencial de soja (sequeiro; alto e baixo insumo). Provável download
  manual; me diga exatamente quais rasters baixar.
- Estatística zonal por município: média do rendimento potencial e fração da área com potencial
  acima de um limiar.
- Série de preço internacional da soja (ex.: World Bank Commodity Price Data, "Pink Sheet"),
  deflacionada.
- Instrumento shift-share: potencial agronômico (cross-section) × preço (série temporal).

**Saída**: `data/interim/instrumento.parquet`

**Aceite**: primeiro estágio preliminar (potencial × preço explicando a área de soja) com
estatística F reportada.

---

## Etapa 7 — Montagem dos painéis

**Fazer**
- `data/processed/painel_municipio.parquet`: município × ano, 1985 (ou o primeiro ano
  disponível) até o último ano.
- `data/processed/painel_amc.parquet`: mesmo conteúdo agregado em AMC (somas para áreas e
  contagens; médias ponderadas por população para taxas; recalcular razões a partir dos
  componentes, nunca fazer média de razões).
- `data/processed/painel_censos.parquet`: AMC × {1991, 2000, 2010, 2022}, para IDHM e
  variáveis censitárias.
- Definições de tratamento (todas no `settings.yaml`):
  - contínuo: participação de agricultura temporária na área do município;
  - binário/escalonado: ano em que a participação cruza o limiar X (padrão 10%, com
    sensibilidade para 5% e 20%);
  - intensidade: variação da participação entre 2000 e o último ano.
- Testes em `tests/test_paineis.py`: chaves únicas, ausência de duplicatas, somas preservadas na
  agregação para AMC.

**Aceite**: testes passando e um dicionário de variáveis em `docs/DICIONARIO.md`.

---

## Etapa 8 — Análise

Faça em scripts (`src/matopiba/s08_*.py`), com resultados salvos em `outputs/`.
Notebooks servem só para exploração.

1. **Descritiva**: mapas de expansão agrícola por década; trajetórias dos desfechos para
   municípios tratados vs. controles; tabela de médias pré-tratamento.
2. **DiD escalonado**: Callaway–Sant'Anna, com event study, para PIB per capita, luzes per
   capita, emprego formal, mortalidade infantil e IDEB. Controles: nunca tratados do Cerrado.
   Reportar também o TWFE convencional, para comparação.
3. **IV / shift-share**: 2SLS com `linearmodels`, efeitos fixos de município e ano, erros
   clusterizados por microrregião. Reportar primeiro estágio, F efetivo e forma reduzida.
4. **Censos (long differences)**: Δ IDHM, Gini e pobreza entre 2000 e 2010, e entre 2010 e 2022,
   contra Δ área agrícola, instrumentado.
5. **Heterogeneidade e mecanismos**: efeito sobre Gini e concentração fundiária; agro vs. não
   agro no emprego; municípios-polo vs. vizinhos.
6. **Robustez**: nível AMC e microrregião (transbordamentos); excluir os 5 maiores polos;
   limiares alternativos; controle para migração; placebo com tratamento antecipado.

**Aceite**: tabelas em `outputs/tabelas/` (CSV e LaTeX) e figuras em `outputs/figuras/`, cada uma
gerada por script e reproduzível com `make analise` (ou equivalente).

---

## Etapa 9 — Reprodutibilidade

- `Makefile` (ou `justfile`) com alvos por etapa e um alvo `all`.
- `README.md` explicando como reproduzir do zero, incluindo os passos manuais (autenticações e
  downloads).
- Rodar o pipeline completo em ambiente limpo e registrar o tempo de cada etapa.