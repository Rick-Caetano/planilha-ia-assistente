"""Leitura das sugestões de pedido mostradas abaixo da caixa de texto (sugestoes.json)."""
import json
from pathlib import Path

SUGESTOES_PATH = Path(__file__).parent.parent / "sugestoes.json"

PADRAO = [
    {"rotulo": "Adicionar linha", "texto": "Acrescente na planilha um cliente chamado Maria Souza, telefone 31999998888, status pendente"},
    {"rotulo": "Deixar bonita e séria", "texto": "A planilha deve ficar mais bonita e séria: coloque o cabeçalho em negrito e cada linha com uma cor alternada, de forma discreta e profissional"},
]


def carregar_sugestoes() -> list[dict]:
    """Lê sugestoes.json. Se o arquivo não existir ou estiver malformado, usa uma
    lista mínima padrão em vez de derrubar o app."""
    if not SUGESTOES_PATH.exists():
        return list(PADRAO)
    try:
        with open(SUGESTOES_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)
        lista = dados.get("sugestoes", [])
        if not isinstance(lista, list):
            return list(PADRAO)
        return [
            item for item in lista
            if isinstance(item, dict) and item.get("rotulo") and item.get("texto")
        ] or list(PADRAO)
    except (json.JSONDecodeError, OSError):
        return list(PADRAO)
