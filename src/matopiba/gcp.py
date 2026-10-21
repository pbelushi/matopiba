"""Clientes autenticados do Earth Engine e do BigQuery (Base dos Dados)."""

from matopiba.config import gcp_project


def ee_init():
    import ee

    ee.Initialize(project=gcp_project("gee_project"))
    return ee


def bigquery_credentials():
    """ADC do gcloud, se houver; senão, as credenciais salvas por `ee.Authenticate()`."""
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    try:
        creds, _ = google.auth.default()
        return creds, "ADC"
    except DefaultCredentialsError:
        import ee

        return ee.data.get_persistent_credentials(), "credenciais do Earth Engine"


def bq_client():
    from google.cloud import bigquery

    creds, _ = bigquery_credentials()
    return bigquery.Client(project=gcp_project("billing_project"), credentials=creds)


def bq_query(sql: str, max_gb: float = 1.0):
    """Roda uma consulta depois de um dry run; aborta se for processar mais que `max_gb`."""
    from google.cloud import bigquery

    client = bq_client()
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    if dry.total_bytes_processed is None:  # views: o dry run não estima o volume
        print("  aviso: dry run sem estimativa de bytes (view); seguindo", flush=True)
        return client.query(sql).to_dataframe()
    gb = dry.total_bytes_processed / 1e9
    if gb > max_gb:
        raise RuntimeError(f"Consulta processaria {gb:.2f} GB (limite {max_gb} GB).")
    return client.query(sql).to_dataframe()
