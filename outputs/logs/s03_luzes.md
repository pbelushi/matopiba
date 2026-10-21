# Etapa 3 — luzes noturnas: aceite

- [OK] Sem municípios faltando nos anos cobertos: luz_soma 1992–2025 (máx. faltando num ano: 0, sempre ausentes: []); li_dmsp_soma 1992–2013 (máx. faltando num ano: 0, sempre ausentes: []); dmsp_soma 1992–2013 (máx. faltando num ano: 0, sempre ausentes: []); viirs_soma 2013–2025 (máx. faltando num ano: 0, sempre ausentes: []); chen_soma 2000–2024 (máx. faltando num ano: 0, sempre ausentes: [])
- [OK] Correlação positiva luzes × PIB municipal em 2023 (log-log, n=5569): 0.906

## Informações

- Série principal encadeada em 2013: VIIRS oficial a partir de 2013; antes, VIIRS(2013) × Li-DMSP(t)/Li-DMSP(2013) por município
- Municípios com Li-DMSP ou VIIRS zerado no ano-base (flag_luz_base_zero): 7; valores pré-2013 indefinidos (NaN): 0
- Chen (VIIRS-like) mantido só como robustez: quebra de nível de ~3,5× entre 2010 e 2013, maior no Matopiba (ver docs/DECISOES.md)
- Fonte da série principal por ano: {'li_dmsp_encadeado': {'min': 1992, 'max': 2012}, 'viirs': {'min': 2013, 'max': 2025}}
- Máscara de água: pixels com >= 50% de água (MapBiomas classe 33, 2020) descartados
