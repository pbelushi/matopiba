# Fontes de dados

Registro de cada fonte: origem, versão/coleção, data de acesso, cobertura e observações.

| Bloco | Fonte | ID / versão | Acesso | Cobertura | Obs. |
|---|---|---|---|---|---|
| Universo | IBGE — lista do MATOPIBA (Portaria MAPA 244/2015) | `MATOPIBA_2021.xls` (lote 10/mar/2021) | 2026-10-20, geoftp.ibge.gov.br | 337 municípios | A delimitação ainda é a da Portaria 244/2015; o Decreto 11.767/2023 recriou o plano sem redelimitar |
| Universo | Embrapa/GITE — Nota Técnica 2 (2014) | área oficial 73.173.484,58 ha | 2026-10-20, Infoteca Embrapa | 31 microrregiões | Usada só como referência de área no aceite |
| Universo | IBGE — malha municipal, via `geobr.read_municipality` | ano 2024, `simplified=False`, `make_valid` | 2026-10-20 | 5.571 municípios | Mesma malha das estatísticas do MapBiomas C11 |
| Universo | IBGE — biomas, via `geobr.read_biomes` | ano 2025, `simplified=False` | 2026-10-20 | Brasil | Usado para `cerrado_share` |
| Universo | Base dos Dados — `br_bd_diretorios_brasil.municipio` | — | 2026-10-20 | 5.571 | Microrregião e região imediata; Boa Esperança do Norte (MT, 2024) sem microrregião |
| Universo | Ehrl (2017), AMC 1991–2010, via `geobr.read_comparable_areas` | 4.298 AMCs | 2026-10-20 | municípios de 2010 | Estendida até 2025, ver DECISOES.md |
| Uso da terra | MapBiomas Brasil — estatísticas de cobertura por bioma/UF/município | Coleção 11, `MAPBIOMAS_BRAZIL-COL.11-BIOME_STATE_MUNICIPALITY.xlsx` (aba COVERAGE_11) | 2026-10-20, brasil.mapbiomas.org/downloads/estatisticas (Google Drive) | 1985–2025; 5.570 municípios + 2 lagoas (RS) | Sem Fernando de Noronha (fora do raster); licença CC BY 4.0 |
| Uso da terra | MapBiomas Brasil — desmatamento anual por município | Coleção 11, `MAPBIOMAS-BRAZIL-DEFORESTATION-ANNUAL-MUNICIPALITY-COLLECTION_11.xlsx`, versão 0-4-14-c84-5-2.1 | 2026-10-20 | 1987–2025 | Perda de vegetação primária (4) e secundária (6) |
| Uso da terra | MapBiomas — legenda | `legend_code_mapbiomas_brazil_collection_11.csv` | 2026-10-20 | — | |
| Uso da terra | MapBiomas — asset no Earth Engine (validação) | `projects/mapbiomas-public/assets/brazil/lulc/collection11/mapbiomas_brazil_collection11_coverage_v3` | 2026-10-20 | 1985–2025, 30 m | `class_remap 13->77` |
| Luzes | NOAA DMSP-OLS V4 (Earth Engine) | `NOAA/DMSP-OLS/NIGHTTIME_LIGHTS`, banda `stable_lights` | 2026-10-20 | 1992–2013 (35 imagens; média entre satélites no ano) | Comparação/robustez |
| Luzes | NOAA VIIRS DNB anual (Earth Engine) | `NOAA/VIIRS/DNB/ANNUAL_V21` (2013–2021) + `ANNUAL_V22` (2022–2025), banda `average_masked` | 2026-10-20 | 2013–2025 | Série principal a partir de 2013; o anual começa em 2013, não em 2012 |
| Luzes | Li et al. (2020), *Sci. Data* 7:168 — DMSP intercalibrado (awesome-gee-community-catalog) | `projects/sat-io/open-datasets/Harmonized_NTL/dmsp`, banda `b1` | 2026-10-20 | 1992–2013 | Série principal antes de 2013, encadeada; a parte simVIIRS (2014–2021) não foi usada por ser ruidosa |
| Luzes | Chen et al. (2021), *ESSD* 13:889–906 — NPP-VIIRS-like (awesome-gee-community-catalog) | `projects/sat-io/open-datasets/npp-viirs-ntl`, banda `b1` | 2026-10-20 | 2000–2024 | Só robustez: quebra de nível em 2011–2013 |
| Luzes | Base dos Dados — `br_ibge_pib.municipio` | — | 2026-10-20 | até 2023 | Usado só no sanity check luzes × PIB |
| Área construída | Google Open Buildings 2.5D Temporal (Earth Engine) | `GOOGLE/Research/open-buildings-temporal/v1`, bandas `building_presence` e `building_fractional_count` | 2026-10-20 | **Cobre o Brasil** (América Latina): 2016–2023, anual, resolução efetiva de 4 m (servido em 0,5 m), derivado do Sentinel-2. Cobertura por município ≥ 94% em 2016 e ≥ 99,6% de 2017 em diante (mediana 100%) | Calculado só para Matopiba + Cerrado fora (1.163 municípios), a 100 m; `building_height` não usada |
| Área construída | MapBiomas C11 — área urbanizada (classe 24) | ver Etapa 2 | 2026-10-20 | 1985–2025, todos os municípios | Complemento; saltos > 50% concentrados em 1986–1995 |
| Socio — população | BD `br_ibge_populacao.municipio` (estimativas e censos IBGE) | — | 2026-10-20 | 1991–2025 | |
| Socio — PIB | BD `br_ibge_pib.municipio` (PIB dos Municípios/IBGE) + `br_ibge_ipca.mes_brasil` | — | 2026-10-20 | 2002–2023 (VA agro até 2021) | Reais de 2023 |
| Socio — emprego formal | BD `br_me_rais.microdados_vinculos` (agregado no servidor) | — | 2026-10-20 | 1985–2025 | R$ só desde 1999; agro por CNAE 2.0/1.0/subsetor IBGE |
| Socio — saúde | BD `br_ms_sinasc.microdados` (agregado) e `br_ms_sim.municipio_causa_idade` | — | 2026-10-20 | 1996–2025 (2025 preliminar) | Município de residência |
| Socio — educação | BD `br_inep_ideb.municipio` + planilhas do INEP (`divulgacao_anos_*_municipios_2023`, só p/ 2015) + BD `br_inep_sinopse_estatistica_educacao_basica.etapa_ensino_serie` | — | 2026-10-20 | IDEB 2005–2025 (bienal), matrículas 2007–2025 | O BD não tem IDEB 2015 |
| Socio — desenvolvimento | BD `mundo_onu_adh.municipio` (Atlas Brasil, PNUD/IPEA/FJP) | — | 2026-10-20 | 1991, 2000, 2010 | Renda em R$ de ago/2010 |
| Socio — Censo 2022 | BD `br_ibge_censo_2022` (municipio, características do domicílio) + SIDRA 10295 (rendimento domiciliar per capita) | — | 2026-10-20 | 2022 | |
| Socio — transferências | BD `br_cgu_beneficios_cidadao` (bolsa_familia_pagamento, auxilio_brasil, novo_bolsa_familia) | — | 2026-10-20 | 2013–2025 completos (2012 e 2026 parciais) | NIS distintos por mês |
| Socio — estrutura fundiária | SIDRA 837 (Censo Agro 2006) e 6754 (Censo Agro 2017), grupos de área total | — | 2026-10-20 | 2006, 2017 | Área suprimida ("X") imputada pelo ponto médio da classe |
| Socio — migração | BD `br_ibge_censo_demografico.microdados_pessoa_{1991,2000,2010}` (agregado, ponderado) | v0314, v0415, v0618/v0619 | 2026-10-20 | 1991, 2000, 2010 | % não naturais da UF só em 2010 |
| Socio — conflitos no campo | CPT | — | pendente | — | Download manual pelo usuário |
| Instrumento | FAO-GAEZ v4, Tema 4 — rendimento atingível e índice de aptidão, soja de sequeiro, alto (H) e baixo (L) insumo, CRU TS 3.2, 1981–2010 | `8110H/ylHr_soy.tif`, `8110L/ylLr_soy.tif`, `8110H/suHr_soy.tif` (+ `suLr`, `sxHr` baixados) | 2026-10-20, bucket público `data.gaezdev.aws.fao.org/res05/CRUTS32/Hist` (download direto, sem passo manual) | global, 5' (~9 km); kg/ha de peso seco | 129 municípios menores que um pixel usam `all_touched` |
| Instrumento | World Bank Commodity Price Data (Pink Sheet), `CMO-Historical-Data-Annual.xlsx` (atualizado em 02/set/2026) | Soybeans ($/mt), nominal e real (US$ de 2010, deflator MUV) | 2026-10-20, thedocs.worldbank.org (link muda todo mês) | 1960–2025 | A capa do arquivo traz um texto de "comparação" atípico; conferido contra a média anual do arquivo mensal (diferença máx. 0,5%) |
