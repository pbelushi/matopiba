"""Etapa 0: verifica autenticação no Earth Engine e acesso ao Base dos Dados.

Uso: python -m matopiba.s00_check_auth
"""

import sys

from matopiba.config import gcp_project
from matopiba.gcp import bigquery_credentials

BD_TEST_QUERY = """
SELECT id_municipio, nome, sigla_uf
FROM `basedosdados.br_bd_diretorios_brasil.municipio`
WHERE sigla_uf = 'TO'
LIMIT 5
"""


def check_earth_engine() -> str:
    import ee

    project = gcp_project("gee_project")
    ee.Initialize(project=project)
    # Initialize sozinho não valida tudo: força uma chamada ao servidor
    n = ee.Image("USGS/SRTMGL1_003").bandNames().size().getInfo()
    return f"projeto={project}, chamada de teste ok (SRTM com {n} banda)"


def check_base_dos_dados() -> str:
    from google.cloud import bigquery

    project = gcp_project("billing_project")
    creds, origem = bigquery_credentials()
    client = bigquery.Client(project=project, credentials=creds)
    job = client.query(
        BD_TEST_QUERY,
        job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
    )
    mb = job.total_bytes_processed / 1e6
    return f"billing={project} ({origem}), dry run ok ({mb:.2f} MB seriam processados)"


def main() -> int:
    checks = [("Earth Engine", check_earth_engine), ("Base dos Dados", check_base_dos_dados)]
    failures = 0
    for name, fn in checks:
        try:
            print(f"[OK]    {name}: {fn()}")
        except Exception as e:  # noqa: BLE001 - reportar qualquer falha
            failures += 1
            print(f"[FALHA] {name}: {type(e).__name__}: {e}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
