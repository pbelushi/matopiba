"""Leitura do settings.yaml e caminhos do projeto."""

import os
from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = ROOT / "config" / "settings.yaml"

_ENV_OVERRIDES = {
    "gee_project": "MATOPIBA_GEE_PROJECT",
    "billing_project": "MATOPIBA_BILLING_PROJECT",
}


@cache
def settings() -> dict:
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key, env in _ENV_OVERRIDES.items():
        if os.environ.get(env):
            cfg["gcp"][key] = os.environ[env]
    return cfg


def path(name: str) -> Path:
    """Caminho absoluto de uma pasta declarada em `paths` no settings.yaml."""
    p = ROOT / settings()["paths"][name]
    p.mkdir(parents=True, exist_ok=True)
    return p


def gcp_project(key: str) -> str:
    value = settings()["gcp"][key]
    if not value or str(value).startswith("PREENCHER"):
        raise RuntimeError(
            f"gcp.{key} não configurado em {SETTINGS_PATH} "
            f"(ou defina a variável {_ENV_OVERRIDES[key]})."
        )
    if str(value).startswith("AIza"):
        raise RuntimeError(
            f"gcp.{key} contém uma chave de API, não um ID de projeto. Use o ID do projeto "
            "(ex.: 'meu-projeto-123', visível no seletor de projetos do Cloud Console)."
        )
    return value
