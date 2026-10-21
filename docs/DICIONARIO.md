# Dicionário de variáveis

Gerado por `src/matopiba/s07_paineis.py` a partir da tabela `VARS`. Valores monetários em R$ constantes de 2023 (IPCA médio anual), exceto onde indicado.
Agregação para AMC: `soma`; `razao` (recalculada a partir dos componentes agregados); `media_pop` / `media_area` / `media_pond` (médias ponderadas); `max` (flags).

## painel_municipio

228,411 linhas × 146 colunas. Chave: `id_municipio`, `ano`

| variável | descrição | unidade | fonte | agregação AMC |
|---|---|---|---|---|
| `id_municipio` | Código IBGE do município (7 dígitos) | | | |
| `ano` | Ano | | | |
| `nome` | Nome do município | | | |
| `sigla_uf` | UF | | | |
| `id_microrregiao` | Microrregião IBGE | | | |
| `nome_microrregiao` | Nome da microrregião | | | |
| `id_regiao_imediata` | Região imediata | | | |
| `nome_regiao_imediata` | Nome da região imediata | | | |
| `area_ha` | Área do município | ha | universo (IBGE 2024) | soma |
| `matopiba` | Município do Matopiba (Portaria MAPA 244/2015) | | | |
| `cerrado_share` | Fração da área no bioma Cerrado | 0–1 | universo (IBGE biomas 2025) | media_area |
| `grupo` | matopiba | cerrado_fora | outros (na AMC: grupo de maior área) | | | |
| `id_amc` | Área mínima comparável (Ehrl 2017 estendida, ver DECISOES.md) | | | |
| `area_soja_ha` | Área de soja (39) | ha | MapBiomas C11 | soma |
| `area_outras_temp_ha` | Área de outras lavouras temporárias (41) | ha | MapBiomas C11 | soma |
| `area_algodao_ha` | Área de algodão (62) | ha | MapBiomas C11 | soma |
| `area_arroz_ha` | Área de arroz (40) | ha | MapBiomas C11 | soma |
| `area_cana_ha` | Área de cana (20) | ha | MapBiomas C11 | soma |
| `area_perenes_ha` | Área de lavouras perenes (35, 46, 47, 48) | ha | MapBiomas C11 | soma |
| `area_pasto_ha` | Área de pastagem (15) | ha | MapBiomas C11 | soma |
| `area_mosaico_ha` | Área de mosaico de usos (21) | ha | MapBiomas C11 | soma |
| `area_silvicultura_ha` | Área de silvicultura (9) | ha | MapBiomas C11 | soma |
| `area_florestal_ha` | Área de formação florestal (3) | ha | MapBiomas C11 | soma |
| `area_savanica_ha` | Área de formação savânica (4) | ha | MapBiomas C11 | soma |
| `area_campestre_ha` | Área de formação campestre (12) | ha | MapBiomas C11 | soma |
| `area_urbano_ha` | Área de área urbanizada (24) | ha | MapBiomas C11 | soma |
| `area_agua_ha` | Área de rio, lago, oceano e aquicultura (31, 33) | ha | MapBiomas C11 | soma |
| `area_agri_temp_ha` | Área de agricultura temporária: soja + arroz + outras temporárias + algodão | ha | MapBiomas C11 | soma |
| `area_nativa_ha` | Área de vegetação nativa (níveis 1 e 2 do MapBiomas: floresta e vegetação herbácea e arbustiva) | ha | MapBiomas C11 | soma |
| `area_total_mb_ha` | Soma de todas as classes do MapBiomas | ha | MapBiomas C11 | soma |
| `flag_area_mb` | Soma das classes difere da área IBGE em > 2% em algum ano (costeiros) |  | MapBiomas C11 | max |
| `share_soja` | Participação de soja (39) na área municipal | 0–1 | MapBiomas C11 | razao (area_soja_ha / area_ha) |
| `share_outras_temp` | Participação de outras lavouras temporárias (41) na área municipal | 0–1 | MapBiomas C11 | razao (area_outras_temp_ha / area_ha) |
| `share_algodao` | Participação de algodão (62) na área municipal | 0–1 | MapBiomas C11 | razao (area_algodao_ha / area_ha) |
| `share_arroz` | Participação de arroz (40) na área municipal | 0–1 | MapBiomas C11 | razao (area_arroz_ha / area_ha) |
| `share_cana` | Participação de cana (20) na área municipal | 0–1 | MapBiomas C11 | razao (area_cana_ha / area_ha) |
| `share_perenes` | Participação de lavouras perenes (35, 46, 47, 48) na área municipal | 0–1 | MapBiomas C11 | razao (area_perenes_ha / area_ha) |
| `share_pasto` | Participação de pastagem (15) na área municipal | 0–1 | MapBiomas C11 | razao (area_pasto_ha / area_ha) |
| `share_mosaico` | Participação de mosaico de usos (21) na área municipal | 0–1 | MapBiomas C11 | razao (area_mosaico_ha / area_ha) |
| `share_silvicultura` | Participação de silvicultura (9) na área municipal | 0–1 | MapBiomas C11 | razao (area_silvicultura_ha / area_ha) |
| `share_florestal` | Participação de formação florestal (3) na área municipal | 0–1 | MapBiomas C11 | razao (area_florestal_ha / area_ha) |
| `share_savanica` | Participação de formação savânica (4) na área municipal | 0–1 | MapBiomas C11 | razao (area_savanica_ha / area_ha) |
| `share_campestre` | Participação de formação campestre (12) na área municipal | 0–1 | MapBiomas C11 | razao (area_campestre_ha / area_ha) |
| `share_urbano` | Participação de área urbanizada (24) na área municipal | 0–1 | MapBiomas C11 | razao (area_urbano_ha / area_ha) |
| `share_agua` | Participação de rio, lago, oceano e aquicultura (31, 33) na área municipal | 0–1 | MapBiomas C11 | razao (area_agua_ha / area_ha) |
| `share_agri_temp` | Participação de agricultura temporária: soja + arroz + outras temporárias + algodão na área municipal | 0–1 | MapBiomas C11 | razao (area_agri_temp_ha / area_ha) |
| `share_nativa` | Participação de vegetação nativa (níveis 1 e 2 do MapBiomas: floresta e vegetação herbácea e arbustiva) na área municipal | 0–1 | MapBiomas C11 | razao (area_nativa_ha / area_ha) |
| `perda_nativa_liq_ha` | Perda líquida de vegetação nativa (nativa t-1 − nativa t) | ha/ano | MapBiomas C11 | soma |
| `desmat_prim_ha` | Perda de vegetação nativa primária | ha/ano | MapBiomas C11 desmatamento | soma |
| `desmat_sec_ha` | Perda de vegetação nativa secundária | ha/ano | MapBiomas C11 desmatamento | soma |
| `desmat_ha` | Desmatamento bruto: perda de vegetação primária + secundária | ha/ano | MapBiomas C11 desmatamento | soma |
| `li_dmsp_soma` | Soma de DN do DMSP intercalibrado | DN | Li et al. (2020) | soma |
| `chen_soma` | Soma de radiância VIIRS-like (robustez; quebra em 2011–2013) | nW/cm²/sr | Chen et al. (2021) | soma |
| `dmsp_soma` | Soma de DN do DMSP (stable_lights) | DN | NOAA DMSP-OLS V4 | soma |
| `viirs_soma` | Soma de radiância VIIRS (average_masked) | nW/cm²/sr | NOAA VIIRS anual | soma |
| `luz_soma` | Soma da radiância noturna (série principal encadeada) | nW/cm²/sr | VIIRS (2013+) e Li-DMSP encadeado (1992–2012) | soma |
| `luz_media` | Radiância média por pixel (série principal) | nW/cm²/sr | idem | media_area |
| `flag_luz_base_zero` | Li-DMSP ou VIIRS zero no ano-base do encadeamento (2013) |  | luzes | max |
| `area_urbana_mb_ha` | Área urbanizada (= area_urbano_ha) | ha | MapBiomas C11 | soma |
| `area_construida_ha` | Área construída 'suave' (presença × área), só Matopiba e Cerrado fora, 2016–2023 | ha | Open Buildings Temporal | soma |
| `n_edificacoes` | Contagem estimada de edificações, só Matopiba e Cerrado fora | nº | Open Buildings Temporal | soma |
| `populacao` | População residente | hab. | IBGE (BD br_ibge_populacao) | soma |
| `pib_real` | PIB | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `impostos_liquidos_real` | Impostos líquidos de subsídios | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_real` | Valor adicionado total | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_agropecuaria_real` | VA da agropecuária | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_industria_real` | VA da indústria | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_servicos_real` | VA dos serviços (exceto adm. pública) | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_adespss_real` | VA da administração, defesa, educação e saúde públicas e seguridade | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `pib_pc_real` | PIB per capita | R$ de 2023/hab. | IBGE | razao (pib_real / populacao) |
| `share_vinculos_agro` | Participação da agropecuária nos vínculos | 0–1 | RAIS | razao (vinculos_agro / vinculos_total) |
| `vinculos_agro` | Vínculos formais ativos em 31/12 — agropecuária | nº | RAIS | soma |
| `vinculos_ignorado` | Vínculos formais ativos em 31/12 — setor ignorado | nº | RAIS | soma |
| `vinculos_nao_agro` | Vínculos formais ativos em 31/12 — demais setores | nº | RAIS | soma |
| `vinculos_total` | Vínculos formais ativos em 31/12 — total | nº | RAIS | soma |
| `massa_salarial_real_total` | Massa salarial anual (12 × remuneração média) — total | R$ de 2023 | RAIS | soma |
| `salario_medio_real_total` | Salário médio mensal — total (1999+) | R$ de 2023 | RAIS | razao (massa_salarial_real_total / vinculos_total) |
| `salario_medio_sm_total` | Salário médio — total | salários mínimos | RAIS | media_pond (peso vinculos_total) |
| `massa_salarial_real_agro` | Massa salarial anual (12 × remuneração média) — agropecuária | R$ de 2023 | RAIS | soma |
| `salario_medio_real_agro` | Salário médio mensal — agropecuária (1999+) | R$ de 2023 | RAIS | razao (massa_salarial_real_agro / vinculos_agro) |
| `salario_medio_sm_agro` | Salário médio — agropecuária | salários mínimos | RAIS | media_pond (peso vinculos_agro) |
| `massa_salarial_real_nao_agro` | Massa salarial anual (12 × remuneração média) — demais | R$ de 2023 | RAIS | soma |
| `salario_medio_real_nao_agro` | Salário médio mensal — demais (1999+) | R$ de 2023 | RAIS | razao (massa_salarial_real_nao_agro / vinculos_nao_agro) |
| `salario_medio_sm_nao_agro` | Salário médio — demais | salários mínimos | RAIS | media_pond (peso vinculos_nao_agro) |
| `ideb_finais` | IDEB, anos finais, rede pública | 0–10 | INEP (BD + planilhas para 2015) | media_pop |
| `ideb_iniciais` | IDEB, anos iniciais, rede pública | 0–10 | INEP (BD + planilhas para 2015) | media_pop |
| `nota_saeb_media_padronizada_finais` | Nota SAEB padronizada, anos finais | 0–10 | INEP | media_pop |
| `nota_saeb_media_padronizada_iniciais` | Nota SAEB padronizada, anos iniciais | 0–10 | INEP | media_pop |
| `matriculas_creche` | Matrículas — creche | nº | INEP Sinopse | soma |
| `matriculas_eja` | Matrículas — EJA | nº | INEP Sinopse | soma |
| `matriculas_fund_finais` | Matrículas — fundamental anos finais | nº | INEP Sinopse | soma |
| `matriculas_fund_iniciais` | Matrículas — fundamental anos iniciais | nº | INEP Sinopse | soma |
| `matriculas_medio` | Matrículas — ensino médio regular | nº | INEP Sinopse | soma |
| `matriculas_pre_escola` | Matrículas — pré-escola | nº | INEP Sinopse | soma |
| `matriculas_profissional` | Matrículas — educação profissional | nº | INEP Sinopse | soma |
| `matriculas_basica_total` | Matrículas — educação básica, total | nº | INEP Sinopse | soma |
| `nascidos_vivos` | Nascidos vivos (residência da mãe) | nº | SINASC | soma |
| `nv_prenatal_7mais` | Nascidos vivos com 7+ consultas de pré-natal | nº | SINASC | soma |
| `nv_prenatal_informado` | Nascidos vivos com nº de consultas informado | nº | SINASC | soma |
| `nv_prenatal_adequado_k` | Nascidos vivos com pré-natal adequado ou mais (Kotelchuck) | nº | SINASC | soma |
| `nv_prenatal_class` | Nascidos vivos com pré-natal classificado | nº | SINASC | soma |
| `obitos_menor_1` | Óbitos de menores de 1 ano (residência) | nº | SIM | soma |
| `tmi` | Taxa de mortalidade infantil | por 1.000 nascidos vivos | SIM/SINASC | razao (obitos_menor_1 / nascidos_vivos) |
| `pct_prenatal_7mais` | Proporção com 7+ consultas de pré-natal | 0–1 | SINASC | razao (nv_prenatal_7mais / nv_prenatal_informado) |
| `pct_prenatal_adequado_kotelchuck` | Proporção com pré-natal adequado ou mais (Kotelchuck, 2014+) | 0–1 | SINASC | razao (nv_prenatal_adequado_k / nv_prenatal_class) |
| `dado_preliminar_saude` | Ano com SIM/SINASC preliminar | | | |
| `familias_media_mensal` | Famílias beneficiárias, média mensal no ano | nº | CGU (BF, Auxílio Brasil, Novo BF) | soma |
| `familias_dezembro` | Famílias beneficiárias em dezembro | nº | CGU | soma |
| `valor_transferencias_real` | Valor total pago no ano | R$ de 2023 | CGU | soma |
| `yl_alto_media` | Rendimento atingível de soja, sequeiro, alto insumo (1981–2010) | kg/ha | FAO-GAEZ v4 | media_area |
| `yl_alto_frac_acima` | Fração da área com rendimento (alto insumo) >= 2.000 kg/ha | 0–1 | FAO-GAEZ v4 | media_area |
| `yl_baixo_media` | Rendimento atingível de soja, sequeiro, baixo insumo (1981–2010) | kg/ha | FAO-GAEZ v4 | media_area |
| `apt_alto_media` | Índice de aptidão (alto insumo) | 0–1 | FAO-GAEZ v4 | media_area |
| `preco_soja_real_usd2010` | Preço internacional da soja | US$ de 2010/t | World Bank Pink Sheet | max |
| `luz_pc` | Radiância por habitante (série principal) | nW/cm²/sr por hab. | luzes + população | razao (luz_soma / populacao) |
| `share_va_agro` | Participação da agropecuária no VA | 0–1 | IBGE | razao (va_agropecuaria_real / va_real) |
| `vinculos_pc` | Vínculos formais por habitante | nº/hab. | RAIS + população | razao (vinculos_total / populacao) |
| `familias_por_mil_hab` | Famílias beneficiárias (média mensal) por 1.000 habitantes |  | CGU + população | razao (familias_media_mensal / populacao) |
| `flag_tmi_instavel` | Nascidos vivos < 50 (taxa instável) | | | |
| `ganho_tecnologico` | Ganho tecnológico: (rendimento alto − baixo insumo) | | | |
| `z_bcp_pos` | Instrumento principal: ganho tecnológico × (ano >= 2003) | | | |
| `z_bcp_tend` | Instrumento alternativo: ganho tecnológico × décadas desde 1985 | | | |
| `log_preco_real` | log do preço real da soja | | | |
| `log_preco_real_l1` | log do preço real da soja, defasado 1 ano | | | |
| `z_yl_alto` | Potencial alto (t/ha) × log preço real t | | | |
| `z_yl_alto_l1` | Instrumento do CLAUDE.md: potencial alto (t/ha) × log preço real t-1 | | | |
| `ano_trat_agri_temp_10` | Primeiro ano em que share_agri_temp >= 10% (NaN = nunca) | | | |
| `trat_agri_temp_10` | 1 a partir do primeiro ano em que share_agri_temp >= 10% | | | |
| `ja_tratado_inicio_agri_temp_10` | share_agri_temp >= 10% já em 1985 | | | |
| `ano_trat_agri_temp_05` | Primeiro ano em que share_agri_temp >= 5% (NaN = nunca) | | | |
| `trat_agri_temp_05` | 1 a partir do primeiro ano em que share_agri_temp >= 5% | | | |
| `ja_tratado_inicio_agri_temp_05` | share_agri_temp >= 5% já em 1985 | | | |
| `ano_trat_agri_temp_20` | Primeiro ano em que share_agri_temp >= 20% (NaN = nunca) | | | |
| `trat_agri_temp_20` | 1 a partir do primeiro ano em que share_agri_temp >= 20% | | | |
| `ja_tratado_inicio_agri_temp_20` | share_agri_temp >= 20% já em 1985 | | | |
| `intensidade_agri_temp` | Intensidade: share_agri_temp(último ano) − share_agri_temp(2000) | | | |
| `ano_trat_soja_10` | Primeiro ano em que share_soja >= 10% (NaN = nunca) | | | |
| `trat_soja_10` | 1 a partir do primeiro ano em que share_soja >= 10% | | | |
| `ja_tratado_inicio_soja_10` | share_soja >= 10% já em 1985 | | | |
| `ano_trat_soja_05` | Primeiro ano em que share_soja >= 5% (NaN = nunca) | | | |
| `trat_soja_05` | 1 a partir do primeiro ano em que share_soja >= 5% | | | |
| `ja_tratado_inicio_soja_05` | share_soja >= 5% já em 1985 | | | |
| `ano_trat_soja_20` | Primeiro ano em que share_soja >= 20% (NaN = nunca) | | | |
| `trat_soja_20` | 1 a partir do primeiro ano em que share_soja >= 20% | | | |
| `ja_tratado_inicio_soja_20` | share_soja >= 20% já em 1985 | | | |
| `intensidade_soja` | Intensidade: share_soja(último ano) − share_soja(2000) | | | |

## painel_amc

176,095 linhas × 141 colunas. Chave: `id_amc`, `ano`

| variável | descrição | unidade | fonte | agregação AMC |
|---|---|---|---|---|
| `id_amc` | Área mínima comparável (Ehrl 2017 estendida, ver DECISOES.md) | | | |
| `ano` | Ano | | | |
| `area_ha` | Área do município | ha | universo (IBGE 2024) | soma |
| `area_soja_ha` | Área de soja (39) | ha | MapBiomas C11 | soma |
| `area_outras_temp_ha` | Área de outras lavouras temporárias (41) | ha | MapBiomas C11 | soma |
| `area_algodao_ha` | Área de algodão (62) | ha | MapBiomas C11 | soma |
| `area_arroz_ha` | Área de arroz (40) | ha | MapBiomas C11 | soma |
| `area_cana_ha` | Área de cana (20) | ha | MapBiomas C11 | soma |
| `area_perenes_ha` | Área de lavouras perenes (35, 46, 47, 48) | ha | MapBiomas C11 | soma |
| `area_pasto_ha` | Área de pastagem (15) | ha | MapBiomas C11 | soma |
| `area_mosaico_ha` | Área de mosaico de usos (21) | ha | MapBiomas C11 | soma |
| `area_silvicultura_ha` | Área de silvicultura (9) | ha | MapBiomas C11 | soma |
| `area_florestal_ha` | Área de formação florestal (3) | ha | MapBiomas C11 | soma |
| `area_savanica_ha` | Área de formação savânica (4) | ha | MapBiomas C11 | soma |
| `area_campestre_ha` | Área de formação campestre (12) | ha | MapBiomas C11 | soma |
| `area_urbano_ha` | Área de área urbanizada (24) | ha | MapBiomas C11 | soma |
| `area_agua_ha` | Área de rio, lago, oceano e aquicultura (31, 33) | ha | MapBiomas C11 | soma |
| `area_agri_temp_ha` | Área de agricultura temporária: soja + arroz + outras temporárias + algodão | ha | MapBiomas C11 | soma |
| `area_nativa_ha` | Área de vegetação nativa (níveis 1 e 2 do MapBiomas: floresta e vegetação herbácea e arbustiva) | ha | MapBiomas C11 | soma |
| `area_total_mb_ha` | Soma de todas as classes do MapBiomas | ha | MapBiomas C11 | soma |
| `perda_nativa_liq_ha` | Perda líquida de vegetação nativa (nativa t-1 − nativa t) | ha/ano | MapBiomas C11 | soma |
| `desmat_prim_ha` | Perda de vegetação nativa primária | ha/ano | MapBiomas C11 desmatamento | soma |
| `desmat_sec_ha` | Perda de vegetação nativa secundária | ha/ano | MapBiomas C11 desmatamento | soma |
| `desmat_ha` | Desmatamento bruto: perda de vegetação primária + secundária | ha/ano | MapBiomas C11 desmatamento | soma |
| `li_dmsp_soma` | Soma de DN do DMSP intercalibrado | DN | Li et al. (2020) | soma |
| `chen_soma` | Soma de radiância VIIRS-like (robustez; quebra em 2011–2013) | nW/cm²/sr | Chen et al. (2021) | soma |
| `dmsp_soma` | Soma de DN do DMSP (stable_lights) | DN | NOAA DMSP-OLS V4 | soma |
| `viirs_soma` | Soma de radiância VIIRS (average_masked) | nW/cm²/sr | NOAA VIIRS anual | soma |
| `luz_soma` | Soma da radiância noturna (série principal encadeada) | nW/cm²/sr | VIIRS (2013+) e Li-DMSP encadeado (1992–2012) | soma |
| `area_urbana_mb_ha` | Área urbanizada (= area_urbano_ha) | ha | MapBiomas C11 | soma |
| `area_construida_ha` | Área construída 'suave' (presença × área), só Matopiba e Cerrado fora, 2016–2023 | ha | Open Buildings Temporal | soma |
| `n_edificacoes` | Contagem estimada de edificações, só Matopiba e Cerrado fora | nº | Open Buildings Temporal | soma |
| `populacao` | População residente | hab. | IBGE (BD br_ibge_populacao) | soma |
| `pib_real` | PIB | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `impostos_liquidos_real` | Impostos líquidos de subsídios | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_real` | Valor adicionado total | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_agropecuaria_real` | VA da agropecuária | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_industria_real` | VA da indústria | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_servicos_real` | VA dos serviços (exceto adm. pública) | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `va_adespss_real` | VA da administração, defesa, educação e saúde públicas e seguridade | R$ de 2023 | IBGE PIB dos Municípios | soma |
| `vinculos_agro` | Vínculos formais ativos em 31/12 — agropecuária | nº | RAIS | soma |
| `vinculos_ignorado` | Vínculos formais ativos em 31/12 — setor ignorado | nº | RAIS | soma |
| `vinculos_nao_agro` | Vínculos formais ativos em 31/12 — demais setores | nº | RAIS | soma |
| `vinculos_total` | Vínculos formais ativos em 31/12 — total | nº | RAIS | soma |
| `massa_salarial_real_total` | Massa salarial anual (12 × remuneração média) — total | R$ de 2023 | RAIS | soma |
| `massa_salarial_real_agro` | Massa salarial anual (12 × remuneração média) — agropecuária | R$ de 2023 | RAIS | soma |
| `massa_salarial_real_nao_agro` | Massa salarial anual (12 × remuneração média) — demais | R$ de 2023 | RAIS | soma |
| `matriculas_creche` | Matrículas — creche | nº | INEP Sinopse | soma |
| `matriculas_eja` | Matrículas — EJA | nº | INEP Sinopse | soma |
| `matriculas_fund_finais` | Matrículas — fundamental anos finais | nº | INEP Sinopse | soma |
| `matriculas_fund_iniciais` | Matrículas — fundamental anos iniciais | nº | INEP Sinopse | soma |
| `matriculas_medio` | Matrículas — ensino médio regular | nº | INEP Sinopse | soma |
| `matriculas_pre_escola` | Matrículas — pré-escola | nº | INEP Sinopse | soma |
| `matriculas_profissional` | Matrículas — educação profissional | nº | INEP Sinopse | soma |
| `matriculas_basica_total` | Matrículas — educação básica, total | nº | INEP Sinopse | soma |
| `nascidos_vivos` | Nascidos vivos (residência da mãe) | nº | SINASC | soma |
| `nv_prenatal_7mais` | Nascidos vivos com 7+ consultas de pré-natal | nº | SINASC | soma |
| `nv_prenatal_informado` | Nascidos vivos com nº de consultas informado | nº | SINASC | soma |
| `nv_prenatal_adequado_k` | Nascidos vivos com pré-natal adequado ou mais (Kotelchuck) | nº | SINASC | soma |
| `nv_prenatal_class` | Nascidos vivos com pré-natal classificado | nº | SINASC | soma |
| `obitos_menor_1` | Óbitos de menores de 1 ano (residência) | nº | SIM | soma |
| `familias_media_mensal` | Famílias beneficiárias, média mensal no ano | nº | CGU (BF, Auxílio Brasil, Novo BF) | soma |
| `familias_dezembro` | Famílias beneficiárias em dezembro | nº | CGU | soma |
| `valor_transferencias_real` | Valor total pago no ano | R$ de 2023 | CGU | soma |
| `flag_area_mb` | Soma das classes difere da área IBGE em > 2% em algum ano (costeiros) |  | MapBiomas C11 | max |
| `flag_luz_base_zero` | Li-DMSP ou VIIRS zero no ano-base do encadeamento (2013) |  | luzes | max |
| `preco_soja_real_usd2010` | Preço internacional da soja | US$ de 2010/t | World Bank Pink Sheet | max |
| `cerrado_share` | Fração da área no bioma Cerrado | 0–1 | universo (IBGE biomas 2025) | media_area |
| `luz_media` | Radiância média por pixel (série principal) | nW/cm²/sr | idem | media_area |
| `salario_medio_sm_total` | Salário médio — total | salários mínimos | RAIS | media_pond (peso vinculos_total) |
| `salario_medio_sm_agro` | Salário médio — agropecuária | salários mínimos | RAIS | media_pond (peso vinculos_agro) |
| `salario_medio_sm_nao_agro` | Salário médio — demais | salários mínimos | RAIS | media_pond (peso vinculos_nao_agro) |
| `ideb_finais` | IDEB, anos finais, rede pública | 0–10 | INEP (BD + planilhas para 2015) | media_pop |
| `ideb_iniciais` | IDEB, anos iniciais, rede pública | 0–10 | INEP (BD + planilhas para 2015) | media_pop |
| `nota_saeb_media_padronizada_finais` | Nota SAEB padronizada, anos finais | 0–10 | INEP | media_pop |
| `nota_saeb_media_padronizada_iniciais` | Nota SAEB padronizada, anos iniciais | 0–10 | INEP | media_pop |
| `yl_alto_media` | Rendimento atingível de soja, sequeiro, alto insumo (1981–2010) | kg/ha | FAO-GAEZ v4 | media_area |
| `yl_alto_frac_acima` | Fração da área com rendimento (alto insumo) >= 2.000 kg/ha | 0–1 | FAO-GAEZ v4 | media_area |
| `yl_baixo_media` | Rendimento atingível de soja, sequeiro, baixo insumo (1981–2010) | kg/ha | FAO-GAEZ v4 | media_area |
| `apt_alto_media` | Índice de aptidão (alto insumo) | 0–1 | FAO-GAEZ v4 | media_area |
| `share_soja` | Participação de soja (39) na área municipal | 0–1 | MapBiomas C11 | razao (area_soja_ha / area_ha) |
| `share_outras_temp` | Participação de outras lavouras temporárias (41) na área municipal | 0–1 | MapBiomas C11 | razao (area_outras_temp_ha / area_ha) |
| `share_algodao` | Participação de algodão (62) na área municipal | 0–1 | MapBiomas C11 | razao (area_algodao_ha / area_ha) |
| `share_arroz` | Participação de arroz (40) na área municipal | 0–1 | MapBiomas C11 | razao (area_arroz_ha / area_ha) |
| `share_cana` | Participação de cana (20) na área municipal | 0–1 | MapBiomas C11 | razao (area_cana_ha / area_ha) |
| `share_perenes` | Participação de lavouras perenes (35, 46, 47, 48) na área municipal | 0–1 | MapBiomas C11 | razao (area_perenes_ha / area_ha) |
| `share_pasto` | Participação de pastagem (15) na área municipal | 0–1 | MapBiomas C11 | razao (area_pasto_ha / area_ha) |
| `share_mosaico` | Participação de mosaico de usos (21) na área municipal | 0–1 | MapBiomas C11 | razao (area_mosaico_ha / area_ha) |
| `share_silvicultura` | Participação de silvicultura (9) na área municipal | 0–1 | MapBiomas C11 | razao (area_silvicultura_ha / area_ha) |
| `share_florestal` | Participação de formação florestal (3) na área municipal | 0–1 | MapBiomas C11 | razao (area_florestal_ha / area_ha) |
| `share_savanica` | Participação de formação savânica (4) na área municipal | 0–1 | MapBiomas C11 | razao (area_savanica_ha / area_ha) |
| `share_campestre` | Participação de formação campestre (12) na área municipal | 0–1 | MapBiomas C11 | razao (area_campestre_ha / area_ha) |
| `share_urbano` | Participação de área urbanizada (24) na área municipal | 0–1 | MapBiomas C11 | razao (area_urbano_ha / area_ha) |
| `share_agua` | Participação de rio, lago, oceano e aquicultura (31, 33) na área municipal | 0–1 | MapBiomas C11 | razao (area_agua_ha / area_ha) |
| `share_agri_temp` | Participação de agricultura temporária: soja + arroz + outras temporárias + algodão na área municipal | 0–1 | MapBiomas C11 | razao (area_agri_temp_ha / area_ha) |
| `share_nativa` | Participação de vegetação nativa (níveis 1 e 2 do MapBiomas: floresta e vegetação herbácea e arbustiva) na área municipal | 0–1 | MapBiomas C11 | razao (area_nativa_ha / area_ha) |
| `luz_pc` | Radiância por habitante (série principal) | nW/cm²/sr por hab. | luzes + população | razao (luz_soma / populacao) |
| `pib_pc_real` | PIB per capita | R$ de 2023/hab. | IBGE | razao (pib_real / populacao) |
| `share_va_agro` | Participação da agropecuária no VA | 0–1 | IBGE | razao (va_agropecuaria_real / va_real) |
| `salario_medio_real_total` | Salário médio mensal — total (1999+) | R$ de 2023 | RAIS | razao (massa_salarial_real_total / vinculos_total) |
| `salario_medio_real_agro` | Salário médio mensal — agropecuária (1999+) | R$ de 2023 | RAIS | razao (massa_salarial_real_agro / vinculos_agro) |
| `salario_medio_real_nao_agro` | Salário médio mensal — demais (1999+) | R$ de 2023 | RAIS | razao (massa_salarial_real_nao_agro / vinculos_nao_agro) |
| `share_vinculos_agro` | Participação da agropecuária nos vínculos | 0–1 | RAIS | razao (vinculos_agro / vinculos_total) |
| `vinculos_pc` | Vínculos formais por habitante | nº/hab. | RAIS + população | razao (vinculos_total / populacao) |
| `tmi` | Taxa de mortalidade infantil | por 1.000 nascidos vivos | SIM/SINASC | razao (obitos_menor_1 / nascidos_vivos) |
| `pct_prenatal_7mais` | Proporção com 7+ consultas de pré-natal | 0–1 | SINASC | razao (nv_prenatal_7mais / nv_prenatal_informado) |
| `pct_prenatal_adequado_kotelchuck` | Proporção com pré-natal adequado ou mais (Kotelchuck, 2014+) | 0–1 | SINASC | razao (nv_prenatal_adequado_k / nv_prenatal_class) |
| `familias_por_mil_hab` | Famílias beneficiárias (média mensal) por 1.000 habitantes |  | CGU + população | razao (familias_media_mensal / populacao) |
| `flag_tmi_instavel` | Nascidos vivos < 50 (taxa instável) | | | |
| `grupo` | matopiba | cerrado_fora | outros (na AMC: grupo de maior área) | | | |
| `share_matopiba` | Fração da área da AMC no Matopiba | | | |
| `n_municipios` | Nº de municípios na AMC | | | |
| `sigla_uf` | UF | | | |
| `id_microrregiao` | Microrregião IBGE | | | |
| `ganho_tecnologico` | Ganho tecnológico: (rendimento alto − baixo insumo) | | | |
| `z_bcp_pos` | Instrumento principal: ganho tecnológico × (ano >= 2003) | | | |
| `z_bcp_tend` | Instrumento alternativo: ganho tecnológico × décadas desde 1985 | | | |
| `log_preco_real` | log do preço real da soja | | | |
| `log_preco_real_l1` | log do preço real da soja, defasado 1 ano | | | |
| `z_yl_alto` | Potencial alto (t/ha) × log preço real t | | | |
| `z_yl_alto_l1` | Instrumento do CLAUDE.md: potencial alto (t/ha) × log preço real t-1 | | | |
| `ano_trat_agri_temp_10` | Primeiro ano em que share_agri_temp >= 10% (NaN = nunca) | | | |
| `trat_agri_temp_10` | 1 a partir do primeiro ano em que share_agri_temp >= 10% | | | |
| `ja_tratado_inicio_agri_temp_10` | share_agri_temp >= 10% já em 1985 | | | |
| `ano_trat_agri_temp_05` | Primeiro ano em que share_agri_temp >= 5% (NaN = nunca) | | | |
| `trat_agri_temp_05` | 1 a partir do primeiro ano em que share_agri_temp >= 5% | | | |
| `ja_tratado_inicio_agri_temp_05` | share_agri_temp >= 5% já em 1985 | | | |
| `ano_trat_agri_temp_20` | Primeiro ano em que share_agri_temp >= 20% (NaN = nunca) | | | |
| `trat_agri_temp_20` | 1 a partir do primeiro ano em que share_agri_temp >= 20% | | | |
| `ja_tratado_inicio_agri_temp_20` | share_agri_temp >= 20% já em 1985 | | | |
| `intensidade_agri_temp` | Intensidade: share_agri_temp(último ano) − share_agri_temp(2000) | | | |
| `ano_trat_soja_10` | Primeiro ano em que share_soja >= 10% (NaN = nunca) | | | |
| `trat_soja_10` | 1 a partir do primeiro ano em que share_soja >= 10% | | | |
| `ja_tratado_inicio_soja_10` | share_soja >= 10% já em 1985 | | | |
| `ano_trat_soja_05` | Primeiro ano em que share_soja >= 5% (NaN = nunca) | | | |
| `trat_soja_05` | 1 a partir do primeiro ano em que share_soja >= 5% | | | |
| `ja_tratado_inicio_soja_05` | share_soja >= 5% já em 1985 | | | |
| `ano_trat_soja_20` | Primeiro ano em que share_soja >= 20% (NaN = nunca) | | | |
| `trat_soja_20` | 1 a partir do primeiro ano em que share_soja >= 20% | | | |
| `ja_tratado_inicio_soja_20` | share_soja >= 20% já em 1985 | | | |
| `intensidade_soja` | Intensidade: share_soja(último ano) − share_soja(2000) | | | |

## painel_censos

25,747 linhas × 42 colunas. Chave: `id_amc`, `ano`

| variável | descrição | unidade | fonte | agregação AMC |
|---|---|---|---|---|
| `id_amc` | Área mínima comparável (Ehrl 2017 estendida, ver DECISOES.md) | | | |
| `ano` | Ano | | | |
| `populacao` | População residente | hab. | IBGE (BD br_ibge_populacao) | soma |
| `idhm` | IDHM (Atlas Brasil) | | | media_pop |
| `idhm_e` | IDHM Educação | | | media_pop |
| `idhm_l` | IDHM Longevidade | | | media_pop |
| `idhm_r` | IDHM Renda | | | media_pop |
| `indice_gini` | Índice de Gini da renda (Atlas) | | | media_pop |
| `indice_theil` | Índice de Theil-L (Atlas) | | | media_pop |
| `prop_pobreza` | % de pobres (Atlas) | | | media_pop |
| `prop_pobreza_extrema` | % de extremamente pobres (Atlas) | | | media_pop |
| `prop_vulner_pobreza` | % de vulneráveis à pobreza (Atlas) | | | media_pop |
| `renda_pc` | Renda per capita (Atlas, R$ de ago/2010) | | | media_pop |
| `expectativa_vida` | Esperança de vida ao nascer (Atlas) | | | media_pop |
| `mortalidade_1` | Mortalidade até 1 ano (Atlas, por mil) | | | media_pop |
| `taxa_analfabetismo_15_mais` | Taxa de analfabetismo, 15 anos ou mais (Atlas) | | | media_pop |
| `expectativa_anos_estudo` | Expectativa de anos de estudo (Atlas) | | | media_pop |
| `pct_nao_natural_municipio` | % de não naturais do município (Censo, ponderado) | | | media_pop |
| `pct_nao_natural_uf` | % de não naturais da UF (Censo 2010) | | | media_pop |
| `taxa_alfabetizacao` | Taxa de alfabetização, 15+ (Censo 2022) | | | media_pop |
| `pct_esgoto_adequado` | % moradores com esgoto por rede ou fossa séptica (Censo 2022) | | | media_pop |
| `pct_agua_rede_geral` | % moradores com água da rede geral como forma principal (2022) | | | media_pop |
| `pct_lixo_coletado` | % moradores com lixo coletado (Censo 2022) | | | media_pop |
| `renda_dom_pc_media` | Rendimento domiciliar per capita médio (Censo 2022, R$ de 2022) | | | media_pop |
| `renda_dom_pc_mediana` | Rendimento domiciliar per capita mediano (Censo 2022; média ponderada das medianas na AMC — aproximação) | | | media_pop |
| `tipo_censo` | demografico | agropecuario | | | media_pop |
| `area_ha` | Área do município | ha | universo (IBGE 2024) | soma |
| `share_soja` | Participação de soja (39) na área municipal | 0–1 | MapBiomas C11 | razao (area_soja_ha / area_ha) |
| `share_agri_temp` | Participação de agricultura temporária: soja + arroz + outras temporárias + algodão na área municipal | 0–1 | MapBiomas C11 | razao (area_agri_temp_ha / area_ha) |
| `share_pasto` | Participação de pastagem (15) na área municipal | 0–1 | MapBiomas C11 | razao (area_pasto_ha / area_ha) |
| `share_nativa` | Participação de vegetação nativa (níveis 1 e 2 do MapBiomas: floresta e vegetação herbácea e arbustiva) na área municipal | 0–1 | MapBiomas C11 | razao (area_nativa_ha / area_ha) |
| `luz_pc` | Radiância por habitante (série principal) | nW/cm²/sr por hab. | luzes + população | razao (luz_soma / populacao) |
| `pib_pc_real` | PIB per capita | R$ de 2023/hab. | IBGE | razao (pib_real / populacao) |
| `ganho_tecnologico` | Ganho tecnológico: (rendimento alto − baixo insumo) | | | |
| `z_bcp_pos` | Instrumento principal: ganho tecnológico × (ano >= 2003) | | | |
| `z_bcp_tend` | Instrumento alternativo: ganho tecnológico × décadas desde 1985 | | | |
| `n_estabelecimentos` | Estabelecimentos agropecuários (Censo Agro) | | | media_pop |
| `area_estabelecimentos_ha` | Área dos estabelecimentos (Censo Agro, ha) | | | media_pop |
| `gini_terra` | Gini da terra (Censo Agro; na AMC, média ponderada pelo nº de estabelecimentos — aproximação) | | | media_pop |
| `share_area_1000ha_mais` | % da área em estabelecimentos de 1.000 ha ou mais | | | media_pop |
| `share_estab_menos_10ha` | % de estabelecimentos com menos de 10 ha | | | media_pop |
| `share_area_imputada` | % da área do Censo Agro imputada (sigilo) | | | media_pop |
