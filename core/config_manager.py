"""Leitura e gravação do config.json: configuração persistente do usuário."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

PADRAO = {
    "primeiro_uso": True,
    "groq_api_key": "",
    "desenvolver": False,
}


def carregar_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(PADRAO)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    return {**PADRAO, **config}


def salvar_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def salvar_api_key(chave: str) -> None:
    config = carregar_config()
    config["groq_api_key"] = chave.strip()
    config["primeiro_uso"] = False
    salvar_config(config)
