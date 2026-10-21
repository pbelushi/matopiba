# Registro de decisões

Formato: data — decisão — motivo — alternativas consideradas.

- 2026-10-20 — Python 3.13 do sistema (`C:\WBG\Python313`), venv criado com `python -m venv`
  em `%USERPROFILE%\.venvs\matopiba`; `uv` usado só como instalador (`uv pip`) — a política
  da máquina bloqueia executáveis do Python baixado pelo `uv` e o launcher de venv do `uv` —
  `uv sync` com Python 3.12 gerenciado.
- 2026-10-20 — Venv fora da pasta do projeto — a pasta fica no OneDrive, que rejeita caminhos
  `\?\` (usados por `uv` para o lock/venv) e sincronizaria milhares de arquivos — venv local.
- 2026-10-20 — Lock em `requirements.lock` via `uv pip compile` (stdout) em vez de `uv.lock` —
  mesmo problema de gravação do `uv lock` no OneDrive.
- 2026-10-20 — Teste do Base dos Dados via `google-cloud-bigquery` com `dry_run=True` —
  valida credencial e billing sem custo — `basedosdados.read_sql` (executaria a consulta).
- 2026-10-20 — Lista do Matopiba: arquivo do IBGE com os 337 códigos da Portaria MAPA
  244/2015 — é a lista oficial e baixável — mapa da Embrapa/GITE (sem lista tabular).
- 2026-10-20 — Malha e biomas do IBGE 2025 (geobr), áreas calculadas na Albers do IBGE
  (SIRGAS 2000) — anos mais recentes disponíveis — malha 2022 do Censo.
- 2026-10-20 — `cerrado_fora` = fora do Matopiba e `cerrado_share >= 0,5` (limiar no
  settings.yaml) — escolhido pelo usuário — `> 0` ou `>= 0,9`.
- 2026-10-20 — AMC: Ehrl (2017) 1991–2010 via geobr, estendida aos 6 municípios criados
  depois de 2010 com fusão estrita (Paraíso das Águas/MS funde as AMCs 1085, 1103 e 1107;
  Boa Esperança do Norte/MT funde 1185 e 1187; código final = menor do grupo; sobreposição
  mínima de 1% para ignorar lascas). Resultado: 4.295 AMCs — escolhido pelo usuário —
  atribuir à AMC majoritária; não estender.
- 2026-10-20 — MapBiomas Coleção 11 (lançada em 12/ago/2026, 1985–2025) — coleção vigente.
- 2026-10-20 — Malha do universo trocada de IBGE 2025 para IBGE 2024 — é a malha das
  estatísticas do MapBiomas C11; com a de 2025, 62 municípios divergiam mais de 2% na área
  (revisões de limites no PI/MA, inclusive 2 do Matopiba); com a de 2024, sobram só 19 municípios
  costeiros fora do grupo de análise. Mesmos 5.571 códigos e área do Matopiba igual.
- 2026-10-20 — `area_agri_temp_ha` = soja (39) + arroz (40) + outras temporárias (41) +
  algodão (62). O arroz foi incluído por decisão do usuário (o CLAUDE.md listava só soja +
  temporárias + algodão). Cana (20) fica em coluna separada.
- 2026-10-20 — `area_nativa_ha` = níveis 1 "Floresta" e "Vegetação herbácea e arbustiva" do
  MapBiomas (3, 4, 5, 6, 7, 11, 12, 13/77, 29, 32, 49, 50, 84), definição usada pelo próprio
  MapBiomas; florestal, savânica e campestre também ficam separadas.
- 2026-10-20 — Desmatamento: bruto do produto anual do MapBiomas (`desmat_ha` = primária +
  secundária, 1987–2025) e líquido derivado (`perda_nativa_liq_ha` = nativa_{t-1} − nativa_t).
- 2026-10-20 — Participações (`share_*`) usam a área IBGE do município (`universo.area_ha`)
  como denominador. Municípios com |soma das classes/área − 1| > 2% em algum ano recebem
  `flag_area_mb` (19, todos costeiros no grupo `outros`, mais Fernando de Noronha, que fica NaN).
- 2026-10-20 — Validação no EE: amostra estratificada (5 Matopiba + 5 Cerrado fora, soja >=
  1.000 ha em 2000, semente 42) × anos 2000, 2012 e 2025.
- 2026-10-20 — Aceite da soma de áreas (2%) avaliado nos grupos `matopiba` e `cerrado_fora`
  (decisão do usuário). Os 19 municípios do grupo `outros` fora da tolerância são costeiros:
  o polígono do IBGE inclui baías e lagunas que o MapBiomas não mede (ex.: Florianópolis, 65% na
  tabela). Fernando de Noronha não é coberto pelo raster. Todos ficam com `flag_area_mb`.
- 2026-10-20 — Luzes: o usuário escolheu primeiro o VIIRS-like de Chen (2000–2024). Ao rodar,
  a série mostrou quebra de nível de ~3,5× entre 2010 e 2013 (Matopiba 4,3×, Cerrado fora 3,1×;
  no DMSP a razão 2013/2010 é ~1), o que viesaria o DiD. O Li-DMSP pós-2013 (simVIIRS) é muito
  ruidoso no Matopiba (ex.: 144 → 104 → 170 entre 2015 e 2017). Decisão do usuário: série
  principal encadeada — VIIRS anual oficial (`average_masked`) a partir de 2013 e, antes,
  VIIRS(2013) × Li-DMSP(t)/Li-DMSP(2013) por município. Chen fica como robustez.
- 2026-10-20 — Encadeamento em municípios muito escuros (7, `flag_luz_base_zero`): se o Li-DMSP
  for zero em 2013, a base é a média de 2009–2013; se ainda zero, a média de 1992–2013.
- 2026-10-20 — Luzes: soma e média por município com `reduceRegions` na escala nativa;
  geometrias simplificadas em 100 m (pixels de 464–928 m). Máscara de água: descarta pixels de
  luz com >= 50% de água (MapBiomas classe 33, 2020). Fogo e luzes efêmeras já excluídos por
  `average_masked` (VIIRS) e `stable_lights` (DMSP). Gás de flare não foi mascarado
  (relevância baixa em terra no Brasil).
- 2026-10-20 — Luzes per capita ficam para depois da Etapa 5 (população), na montagem do painel.
- 2026-10-20 — Área construída (Open Buildings Temporal): a primeira tentativa (Brasil todo,
  amostragem a 10 m) consumiu ~560 EECU-h com 3 de 8 anos ainda rodando e foi cancelada; uma
  segunda (grupos de análise, 30 m) falhou na exportação (`toAsset` não aceita geometria nula).
  Total gasto nessas tentativas: ~830 EECU-h.
- 2026-10-20 — Teste de escala (8 municípios pequenos, 2023, contra 4 m): a área por limiar
  (presença > 0,5) e a altura média dependem da escala, porque o EE usa pirâmides de média
  (área −42% e altura −35% a 30 m; altura −65% a 100 m). Contagem (`building_fractional_count`)
  e área "suave" (presença × área do pixel) são somas de médias e não dependem da escala
  (±3% a 100 m). Decisão do usuário: calcular a 100 m só contagem e área suave, para os grupos
  de análise (custo real: 61 EECU-h). Altura média ficou de fora: só seria confiável perto de
  4 m, a um custo de milhares de EECU-h. A área suave é uma medida relativa (a presença não é
  calibrada); a 4 m fica cerca de 15% acima da área por limiar 0,5.
- 2026-10-20 — Grupo `outros` sem Open Buildings (NaN); para todos os municípios, a área
  urbanizada do MapBiomas (1985–2025) entra como complemento em `area_urbana_mb_ha`.
- 2026-10-20 — Malha municipal guardada como asset no EE em
  `projects/matopiba-512215/assets/matopiba/municipios_*` (33 partes, simplificada em 10 m),
  reaproveitável nas próximas etapas.
- 2026-10-20 — Etapa 5: universo = todos os municípios, então as consultas não filtram por
  município; todas agregam no servidor e passam por dry run com limite de GB. Volume total
  processado ≈ 200 GB (dentro da franquia gratuita do BigQuery).
- 2026-10-20 — Reais constantes de 2023 (último ano do PIB municipal), deflator = IPCA médio
  anual. RAIS: o BD só traz remuneração em R$ a partir de 1999; antes, só em salários mínimos
  (`salario_medio_sm_*` cobre 1985–2025). Massa salarial anual ≈ 12 × soma da remuneração
  média dos vínculos ativos em 31/12.
- 2026-10-20 — RAIS agro: CNAE 2.0 divisões 01–03 (2006+); CNAE 1.0 divisões 01, 02 e 05
  (1994–2005); subsetor IBGE 25 (até 1993). Até 1993 há muitos vínculos sem setor
  (`share_setor_ignorado` de 14% a 36% no Matopiba).
- 2026-10-20 — Mortalidade infantil = óbitos < 1 ano (SIM, residência) / nascidos vivos
  (SINASC, residência) × 1000; `flag_tmi_instavel` quando nascidos vivos < 50 (18,7% dos
  municípios em 2020). Atenção: nos anos 1990 há sub-registro de óbitos no Norte/Nordeste (a TMI
  do Matopiba em 1996 sai menor que a de 2000). 2025 marcado como preliminar.
- 2026-10-20 — Pré-natal adequado: duas medidas — 7+ consultas (`pct_prenatal_7mais`, 1996+) e
  índice de Kotelchuck "adequado ou mais" (`pct_prenatal_adequado_kotelchuck`, 2014+).
- 2026-10-20 — IDEB: rede pública, anos iniciais e finais; 2015 vem das planilhas do INEP
  (`fonte_ideb`), porque falta no BD.
- 2026-10-20 — Gini da terra: Lorenz por grupos de área total, excluindo produtores sem área.
  Valores suprimidos por sigilo ("X") imputados como n × ponto médio da classe (classe aberta do
  topo: 1,5 × limite inferior); com isso, a área total fica a −0,9% (2006) e +0,7% (2017) do
  total oficial. `share_area_imputada` registra a fração imputada (mediana de 19% no Matopiba
  em 2017).
- 2026-10-20 — Transferências: famílias = NIS distintos com pagamento no mês (competência),
  somados entre programas no mês; anual = média mensal e dezembro; `meses` registra
  anos parciais (2012 e 2026).
- 2026-10-20 — Censo 2022: saneamento como % de moradores em domicílios com esgoto por rede
  ou fossa séptica, água da rede geral como forma principal e lixo coletado; renda domiciliar
  per capita média e mediana (SIDRA 10295).
- 2026-10-20 — GAEZ v4: potencial principal = rendimento atingível de soja de sequeiro com alto
  insumo (`yl_alto`); alternativo = baixo insumo; também índice de aptidão (`apt_alto`, fração
  >= 0,55 = "boa ou melhor"). Limiares de fração: 2.000 kg/ha (alto, ≈ mediana nacional) e
  500 kg/ha (baixo).
- 2026-10-20 — Preço: soja do Pink Sheet em US$ reais de 2010 (deflator do próprio Banco
  Mundial). Instrumento: z = potencial (t/ha) × log(preço real), contemporâneo e defasado em 1 ano.
- 2026-10-20 — Primeiro estágio preliminar (Matopiba + Cerrado fora, 1985–2025, EF município e
  ano, cluster microrregião): o instrumento do CLAUDE.md é FRACO (F de 0,02 a 3,1). O preço real
  não tem tendência no período (376 → 357 US$/t entre 1985 e 2025), então com EF de ano o
  instrumento só capta ciclos, e a expansão é uma tendência; além disso, o potencial é menor no
  Matopiba do que no Cerrado fora. Alternativas testadas (`notebooks/explora_s06_instrumentos_alternativos.py`): ganho
  tecnológico à la Bustos, Caprettini e Ponticelli (2016) — (alto − baixo) × pós-2003 ou ×
  tendência — e potencial × tendência chegam a F de 6–8 para `share_soja` e < 2 para
  `share_agri_temp`.
- 2026-10-20 — Instrumento (decisão do usuário, opções B + C): principal = ganho tecnológico à
  la Bustos, Caprettini e Ponticelli (2016), `ganho_tecnologico` = rendimento atingível com alto
  menos com baixo insumo (t/ha), × pós-2003 (`z_bcp_pos`; MP 113/2003, primeira liberação da soja
  transgênica), com `z_bcp_tend` (× tendência) como alternativa; tratamento instrumentado =
  `share_soja`. Painel anual (Matopiba + Cerrado fora): F = 6,2 (pós) e 8,0 (tendência),
  ainda abaixo de 10 — na Etapa 8, reportar inferência robusta a instrumento fraco
  (Anderson-Rubin). Diferenças longas (Δ entre censos, EF de UF, cluster microrregião):
  2010–2022 forte em todos os níveis (F 18 no município, 26 na AMC, 20 na microrregião);
  empilhado 2000–2010 + 2010–2022 F 13 / 18 / 23; 2000–2010 sozinho fraco (F < 2). Para
  `share_agri_temp` o instrumento só tem alguma força no nível microrregião (F 7–8).
  Consequência para a Etapa 8: o IV deve instrumentar `share_soja`, e as diferenças longas são a
  especificação de IV mais crível.
- 2026-10-20 — Painéis: regras de agregação para AMC declaradas por variável em
  `s07_paineis.VARS` (soma / razão recalculada dos componentes / média ponderada por população
  ou área / max para flags); o `docs/DICIONARIO.md` é gerado da mesma tabela. Gini da renda
  (Atlas), Gini da terra e renda mediana não têm agregação exata: na AMC são médias ponderadas
  (população ou nº de estabelecimentos), o que é uma aproximação.
- 2026-10-20 — Tratamento escalonado: primeiro ano em que a participação cruza o limiar
  (5%, 10%, 20%), sem exigir permanência acima; `ja_tratado_inicio_*` marca quem já está acima
  em 1985 (sem pré-período; 64 municípios do Cerrado fora a 10%). Definido para
  `share_agri_temp` (CLAUDE.md) e `share_soja` (tratamento do IV). Intensidade = participação
  em 2025 − participação em 2000.
- 2026-10-20 — Transferências: anos com menos de 12 meses (2012, 2026) não entram no painel
  anual. Saúde: `dado_preliminar_saude` marca 2025.
- 2026-10-20 — `painel_censos`: AMC × {1991, 2000, 2010, 2022} (`tipo_censo = demografico`)
  mais AMC × {2006, 2017} (`tipo_censo = agropecuario`), com uso da terra, luzes, PIB per capita
  e instrumento nos mesmos anos para as diferenças longas.
- 2026-10-20 — Etapa 8: Callaway–Sant'Anna implementado em `analise.cs_did` (incondicional,
  nunca tratados, base "varying" e "universal", EP pela função de influência com cluster por
  microrregião). Motivo: o pacote `differences` 0.3 quebra com cluster no pandas atual; as
  estimativas pontuais conferem com ele no painel balanceado (`tests/test_analise.py`). Painel
  balanceado na janela de cada desfecho (como o `did` do R com panel=TRUE); unidades tratadas
  depois do fim da janela contam como nunca tratadas.
- 2026-10-20 — DiD: tratados = municípios do Matopiba + Cerrado fora que cruzam 10% de
  agricultura temporária; controles = nunca tratados da mesma amostra; sem os já tratados em
  1985. Desfechos: log PIB per capita (2002–2023), log luzes per capita (1992–2025), log
  emprego formal per capita (1995–2025), TMI (2000–2024; anos 1990 fora por sub-registro) e
  IDEB anos iniciais (2005–2025, bienal).
- 2026-10-20 — Resultado a registrar: o placebo antecipado e o event study com base universal
  mostram pré-tendência positiva no PIB per capita (~+1% a.a. nos 5 anos antes do cruzamento do
  limiar; o cruzamento é o fim de um processo gradual). O efeito pós acelera além da tendência
  (≈ +0,15 em e = 7 contra ≈ +0,08 da extrapolação), mas o ATT agregado do PIB deve ser lido com
  essa ressalva. Luzes sem pré-tendência.
- 2026-10-20 — IV no painel anual é fraco e instável (F 0,2–6 por desfecho; sinais opostos ao
  DiD); a especificação de IV crível é a de diferenças longas (AMC). Nelas, sem controle de nível
  inicial, o 2SLS 2010–2022 sai fortemente negativo — artefato de convergência/teto (o ganho
  tecnológico é maior onde renda e alfabetização já eram altas); com o nível inicial como
  controle o efeito na renda é ≈ 0 (2SLS +0,06, F 16,8). As tabelas reportam as duas versões.
- 2026-10-20 — Polos = 5 municípios do Matopiba com maior área de soja em 2025 (Formosa do Rio
  Preto, São Desidério, Baixa Grande do Ribeiro, Balsas, Barreiras); vizinhos = municípios que
  tocam um polo, nunca tratados, com a coorte do polo adjacente (transbordamento).
- 2026-10-20 — `make analise` ⇒ `python -m matopiba.tarefas analise` (não há `make` na
  máquina); tempos em `outputs/logs/tempos.csv`.
