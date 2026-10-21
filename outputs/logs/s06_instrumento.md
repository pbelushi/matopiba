# Etapa 6 — instrumento: aceite

- [OK] Primeiro estágio reportado (share_soja ~ z_bcp_pos, EF município e ano, cluster microrregião): coef 0.0157, t 2.48, F 6.2
- [OK] Potencial GAEZ para todos os municípios (sem valor: 0)

## Primeiro estágio preliminar

Amostra: grupos ['matopiba', 'cerrado_fora'], 1162 municípios, 148 microrregiões. F = t² com erro-padrão clusterizado (um instrumento).

| dependente      | instrumento   |    coef |     ep |       t |   F_cluster |   n_obs |   n_municipios |   n_clusters |   r2_within |
|:----------------|:--------------|--------:|-------:|--------:|------------:|--------:|---------------:|-------------:|------------:|
| share_soja      | z_bcp_pos     |  0.0157 | 0.0063 |  2.4832 |      6.1661 |   47642 |           1162 |          148 |      0.1282 |
| share_soja      | z_bcp_tend    |  0.0083 | 0.0029 |  2.8372 |      8.0497 |   47642 |           1162 |          148 |      0.1907 |
| share_soja      | z_yl_alto     |  0.0168 | 0.0096 |  1.7500 |      3.0626 |   47642 |           1162 |          148 |      0.0684 |
| share_soja      | z_yl_alto_l1  |  0.0134 | 0.0091 |  1.4762 |      2.1791 |   47642 |           1162 |          148 |      0.0576 |
| share_soja      | z_yl_baixo    | -0.0067 | 0.0437 | -0.1529 |      0.0234 |   47642 |           1162 |          148 |     -0.0054 |
| share_soja      | z_yl_baixo_l1 | -0.0055 | 0.0413 | -0.1322 |      0.0175 |   47642 |           1162 |          148 |     -0.0042 |
| share_agri_temp | z_bcp_pos     |  0.0079 | 0.0072 |  1.1020 |      1.2145 |   47642 |           1162 |          148 |      0.1024 |
| share_agri_temp | z_bcp_tend    |  0.0043 | 0.0032 |  1.3223 |      1.7485 |   47642 |           1162 |          148 |      0.1524 |
| share_agri_temp | z_yl_alto     |  0.0015 | 0.0107 |  0.1420 |      0.0202 |   47642 |           1162 |          148 |      0.0096 |
| share_agri_temp | z_yl_alto_l1  | -0.0029 | 0.0099 | -0.2887 |      0.0833 |   47642 |           1162 |          148 |     -0.0184 |
| share_agri_temp | z_yl_baixo    | -0.0085 | 0.0478 | -0.1787 |      0.0319 |   47642 |           1162 |          148 |     -0.0067 |
| share_agri_temp | z_yl_baixo_l1 | -0.0067 | 0.0437 | -0.1538 |      0.0236 |   47642 |           1162 |          148 |     -0.0048 |

## Primeiro estágio em diferenças longas (anos censitários)

Δ participação na área ~ ganho tecnológico × duração do período (décadas), EF de UF (e de período no empilhado); cluster microrregião (nível microrregião: erro robusto HC1).

| nivel        | periodo   | dependente        |    coef |     ep |       t |       F |    n |   n_clusters |
|:-------------|:----------|:------------------|--------:|-------:|--------:|--------:|-----:|-------------:|
| municipio    | 2000-2010 | d_share_soja      |  0.0045 | 0.0039 |  1.1487 |  1.3196 | 1162 |     148.0000 |
| municipio    | 2010-2022 | d_share_soja      |  0.0161 | 0.0038 |  4.2394 | 17.9725 | 1162 |     148.0000 |
| municipio    | empilhado | d_share_soja      |  0.0122 | 0.0034 |  3.6106 | 13.0364 | 2324 |     148.0000 |
| municipio    | 2000-2010 | d_share_agri_temp | -0.0020 | 0.0049 | -0.4097 |  0.1678 | 1162 |     148.0000 |
| municipio    | 2010-2022 | d_share_agri_temp |  0.0011 | 0.0044 |  0.2462 |  0.0606 | 1162 |     148.0000 |
| municipio    | empilhado | d_share_agri_temp |  0.0003 | 0.0041 |  0.0695 |  0.0048 | 2324 |     148.0000 |
| amc          | 2000-2010 | d_share_soja      |  0.0060 | 0.0046 |  1.3040 |  1.7005 |  835 |     146.0000 |
| amc          | 2010-2022 | d_share_soja      |  0.0222 | 0.0044 |  5.0731 | 25.7368 |  835 |     146.0000 |
| amc          | empilhado | d_share_soja      |  0.0164 | 0.0039 |  4.2428 | 18.0017 | 1670 |     146.0000 |
| amc          | 2000-2010 | d_share_agri_temp | -0.0026 | 0.0059 | -0.4481 |  0.2008 |  835 |     146.0000 |
| amc          | 2010-2022 | d_share_agri_temp |  0.0032 | 0.0046 |  0.6993 |  0.4891 |  835 |     146.0000 |
| amc          | empilhado | d_share_agri_temp |  0.0015 | 0.0044 |  0.3498 |  0.1223 | 1670 |     146.0000 |
| microrregiao | 2000-2010 | d_share_soja      |  0.0076 | 0.0057 |  1.3326 |  1.7759 |  148 |     nan      |
| microrregiao | 2010-2022 | d_share_soja      |  0.0204 | 0.0046 |  4.4615 | 19.9051 |  148 |     nan      |
| microrregiao | empilhado | d_share_soja      |  0.0166 | 0.0035 |  4.7826 | 22.8730 |  296 |     nan      |
| microrregiao | 2000-2010 | d_share_agri_temp |  0.0056 | 0.0058 |  0.9660 |  0.9332 |  148 |     nan      |
| microrregiao | 2010-2022 | d_share_agri_temp |  0.0097 | 0.0037 |  2.6512 |  7.0289 |  148 |     nan      |
| microrregiao | empilhado | d_share_agri_temp |  0.0091 | 0.0031 |  2.9003 |  8.4115 |  296 |     nan      |

## Potencial por grupo (mediana)

| grupo        |   yl_alto_media |   yl_baixo_media |   ganho_tecnologico |   yl_alto_frac_acima |
|:-------------|----------------:|-----------------:|--------------------:|---------------------:|
| cerrado_fora |        2628.102 |          284.182 |               2.335 |                1.000 |
| matopiba     |        1890.333 |          226.091 |               1.649 |                0.419 |
| outros       |        2165.583 |          284.000 |               1.837 |                0.667 |

## Preço real da soja (US$ de 2010/t)

|   ano |   preco_soja_nominal_usd |   preco_soja_real_usd2010 |
|------:|-------------------------:|--------------------------:|
|  1985 |                      224 |                       376 |
|  1986 |                      208 |                       304 |
|  1987 |                      216 |                       287 |
|  1988 |                      304 |                       379 |
|  1989 |                      275 |                       345 |
|  1990 |                      247 |                       298 |
|  1991 |                      240 |                       292 |
|  1992 |                      236 |                       282 |
|  1993 |                      255 |                       296 |
|  1994 |                      252 |                       301 |
|  1995 |                      259 |                       282 |
|  1996 |                      305 |                       338 |
|  1997 |                      295 |                       344 |
|  1998 |                      243 |                       296 |
|  1999 |                      202 |                       250 |
|  2000 |                      212 |                       266 |
|  2001 |                      196 |                       256 |
|  2002 |                      213 |                       281 |
|  2003 |                      264 |                       332 |
|  2004 |                      307 |                       360 |
|  2005 |                      275 |                       313 |
|  2006 |                      269 |                       299 |
|  2007 |                      383 |                       401 |
|  2008 |                      522 |                       508 |
|  2009 |                      424 |                       439 |
|  2010 |                      447 |                       447 |
|  2011 |                      538 |                       484 |
|  2012 |                      596 |                       540 |
|  2013 |                      551 |                       502 |
|  2014 |                      485 |                       448 |
|  2015 |                      392 |                       401 |
|  2016 |                      405 |                       431 |
|  2017 |                      393 |                       404 |
|  2018 |                      394 |                       387 |
|  2019 |                      369 |                       371 |
|  2020 |                      407 |                       415 |
|  2021 |                      583 |                       533 |
|  2022 |                      675 |                       575 |
|  2023 |                      598 |                       524 |
|  2024 |                      462 |                       402 |
|  2025 |                      414 |                       357 |
