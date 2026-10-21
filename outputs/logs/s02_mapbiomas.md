# Etapa 2 — MapBiomas: aceite

- [OK] Painel balanceado: 228,411 linhas = 5,571 municípios × 41 anos, chave única
- [OK] Soma das classes ≈ área do município (tolerância 2%) em todos os municípios do Matopiba e do Cerrado fora (fora: 0)
- [OK] Divergência tabela × EE < 3% (máx. 0.02%, 30 pares)

## Informações

- Coleção 11, anos 1985–2025; desmatamento (1987, 2025)
- Municípios calculados no EE (ausentes da tabela): ['2605459']
- AVISO — universo todo: 99.66% das linhas dentro da tolerância; 19 municípios fora, todos do grupo ['outros'] (costeiros + Fernando de Noronha), marcados com flag_area_mb. Aceito pelo usuário: o critério vale para os grupos de análise.
- Desvio soma das classes/área IBGE — mediana -0.00%, p1 -0.72%, p99 +0.02%; Matopiba: máx. |desvio| 0.53%
- Municípios fora da tolerância (pior ano): Fernando de Noronha (PE, outros) -100.0%; Florianópolis (SC, outros) -35.0%; Governador Celso Ramos (SC, outros) -26.5%; São José (SC, outros) -24.0%; Palhoça (SC, outros) -17.0%; Biguaçu (SC, outros) -13.4%; Raposa (MA, outros) -13.0%; Vitória (ES, outros) -12.4%; Godofredo Viana (MA, outros) -7.2%; Porto Rico do Maranhão (MA, outros) -4.5%; Barra dos Coqueiros (SE, outros) -3.4%; São João de Pirabas (PA, outros) -3.0%; Arroio do Sal (RS, outros) -2.9%; Cururupu (MA, outros) -2.7%; Ilha Comprida (SP, outros) -2.7%; Capão da Canoa (RS, outros) -2.5%; Augusto Corrêa (PA, outros) -2.2%; Luís Domingues (MA, outros) -2.2%; Cabedelo (PB, outros) -2.0%

## Validação no Earth Engine (soja)

|   id_municipio | nome                    | sigla_uf   | grupo        |   ano |   soja_tabela_ha |   soja_ee_ha |   divergencia |
|---------------:|:------------------------|:-----------|:-------------|------:|-----------------:|-------------:|--------------:|
|        2919553 | Luís Eduardo Magalhães  | BA         | matopiba     |  2000 |       76393.2595 |   76393.4470 |        0.0000 |
|        2919553 | Luís Eduardo Magalhães  | BA         | matopiba     |  2012 |      109029.6994 |  109029.3149 |       -0.0000 |
|        2919553 | Luís Eduardo Magalhães  | BA         | matopiba     |  2025 |      225053.1447 |  225053.2147 |        0.0000 |
|        2112001 | Tasso Fragoso           | MA         | matopiba     |  2000 |       24799.0834 |   24799.2708 |        0.0000 |
|        2112001 | Tasso Fragoso           | MA         | matopiba     |  2012 |       78936.1938 |   78935.5022 |       -0.0000 |
|        2112001 | Tasso Fragoso           | MA         | matopiba     |  2025 |      104404.5533 |  104404.5596 |        0.0000 |
|        2902500 | Baianópolis             | BA         | matopiba     |  2000 |        2589.0249 |    2588.6380 |       -0.0001 |
|        2902500 | Baianópolis             | BA         | matopiba     |  2012 |        7202.1674 |    7202.2099 |        0.0000 |
|        2902500 | Baianópolis             | BA         | matopiba     |  2025 |       33307.3575 |   33306.3170 |       -0.0000 |
|        2201150 | Baixa Grande do Ribeiro | PI         | matopiba     |  2000 |       13358.6065 |   13358.6305 |        0.0000 |
|        2201150 | Baixa Grande do Ribeiro | PI         | matopiba     |  2012 |       81528.6383 |   81535.5380 |        0.0001 |
|        2201150 | Baixa Grande do Ribeiro | PI         | matopiba     |  2025 |      288720.0903 |  288732.1695 |        0.0000 |
|        2102804 | Carolina                | MA         | matopiba     |  2000 |        1205.1324 |    1205.1113 |       -0.0000 |
|        2102804 | Carolina                | MA         | matopiba     |  2012 |       17350.2389 |   17350.5321 |        0.0000 |
|        2102804 | Carolina                | MA         | matopiba     |  2025 |       31191.3042 |   31191.6241 |        0.0000 |
|        3166808 | Serra do Salitre        | MG         | cerrado_fora |  2000 |        1830.8287 |    1830.8555 |        0.0000 |
|        3166808 | Serra do Salitre        | MG         | cerrado_fora |  2012 |       11932.8431 |   11934.4060 |        0.0001 |
|        3166808 | Serra do Salitre        | MG         | cerrado_fora |  2025 |       23958.8413 |   23961.8227 |        0.0001 |
|        5203302 | Bela Vista de Goiás     | GO         | cerrado_fora |  2000 |        2272.8291 |    2273.2397 |        0.0002 |
|        5203302 | Bela Vista de Goiás     | GO         | cerrado_fora |  2012 |        8324.5786 |    8326.0664 |        0.0002 |
|        5203302 | Bela Vista de Goiás     | GO         | cerrado_fora |  2025 |       25186.1240 |   25188.0371 |        0.0001 |
|        5213756 | Montividiu              | GO         | cerrado_fora |  2000 |      103223.6723 |  103219.2094 |       -0.0000 |
|        5213756 | Montividiu              | GO         | cerrado_fora |  2012 |      122491.6742 |  122488.4315 |       -0.0000 |
|        5213756 | Montividiu              | GO         | cerrado_fora |  2025 |      136746.5997 |  136741.9630 |       -0.0000 |
|        5204250 | Cachoeira Dourada       | GO         | cerrado_fora |  2000 |       13306.1007 |   13306.2689 |        0.0000 |
|        5204250 | Cachoeira Dourada       | GO         | cerrado_fora |  2012 |       10784.7019 |   10784.9177 |        0.0000 |
|        5204250 | Cachoeira Dourada       | GO         | cerrado_fora |  2025 |       10385.6110 |   10385.4157 |       -0.0000 |
|        5211503 | Itumbiara               | GO         | cerrado_fora |  2000 |       52217.6071 |   52217.0976 |       -0.0000 |
|        5211503 | Itumbiara               | GO         | cerrado_fora |  2012 |       39132.9384 |   39132.7786 |       -0.0000 |
|        5211503 | Itumbiara               | GO         | cerrado_fora |  2025 |       68691.5661 |   68690.9929 |       -0.0000 |
