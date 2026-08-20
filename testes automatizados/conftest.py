"""Fixtures compartilhadas: uma planilha de teste pequena, com colunas de texto e número."""
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sheet_manager import SheetManager  # noqa: E402

COLUNAS_TESTE = ["Nome", "Cidade", "Preco", "Quantidade"]
LINHAS_TESTE = [
    ["Maria", "Belo Horizonte", 10, 2],
    ["João", "São Paulo", 20, 1],
    ["Ana", "Belo Horizonte", 30, 3],
]


@pytest.fixture
def planilha_teste(tmp_path) -> Path:
    workbook = Workbook()
    planilha = workbook.active
    planilha.append(COLUNAS_TESTE)
    for linha in LINHAS_TESTE:
        planilha.append(linha)
    caminho = tmp_path / "planilha_teste.xlsx"
    workbook.save(caminho)
    return caminho


@pytest.fixture
def manager(planilha_teste) -> SheetManager:
    return SheetManager(planilha_teste)
