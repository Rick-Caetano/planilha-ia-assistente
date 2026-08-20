"""Testa a mini-linguagem de expressões usada em adicionar_coluna_calculada."""
import pytest

from core.errors import SheetError
from core.formula_utils import calcular_valor, montar_formula_excel

COLUNAS = ["Preco", "Quantidade"]
VALORES_LINHA = {"Preco": 10, "Quantidade": 3}


def test_calcular_valor_multiplicacao():
    assert calcular_valor("Preco * Quantidade", COLUNAS, VALORES_LINHA) == 30


def test_calcular_valor_com_parenteses_e_numero():
    assert calcular_valor("(Preco + 5) * Quantidade", COLUNAS, VALORES_LINHA) == 45


def test_calcular_valor_divisao_por_zero():
    with pytest.raises(SheetError):
        calcular_valor("Preco / (Quantidade - 3)", COLUNAS, VALORES_LINHA)


def test_calcular_valor_coluna_inexistente():
    with pytest.raises(SheetError):
        calcular_valor("Preco * Inexistente", COLUNAS, VALORES_LINHA)


@pytest.mark.parametrize(
    "expressao_maliciosa",
    [
        "__import__('os').system('echo oi')",
        "open('arquivo.txt')",
        "Preco.bit_length()",
        "[1, 2, 3]",
        "Preco if True else Quantidade",
        "lambda: 1",
    ],
)
def test_expressoes_nao_suportadas_sao_rejeitadas(expressao_maliciosa):
    with pytest.raises(SheetError):
        calcular_valor(expressao_maliciosa, COLUNAS, VALORES_LINHA)


def test_montar_formula_excel_usa_referencias_de_celula():
    formula = montar_formula_excel("Preco * Quantidade", COLUNAS, numero_linha=5)
    assert formula == "=(A5*B5)"
