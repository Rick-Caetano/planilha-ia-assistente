"""Avaliação segura de expressões aritméticas simples entre colunas.

Usado só por `adicionar_coluna_calculada` (ex.: "Preço * Quantidade"). Nunca usa
`eval`/`exec`: percorre a árvore sintática (`ast`) e só aceita nomes de coluna, números,
`+ - * /` e parênteses. Qualquer outra coisa (chamada de função, atributo, import) é
rejeitada antes de qualquer execução.
"""
from __future__ import annotations

import ast

from openpyxl.utils import get_column_letter

from core.errors import SheetError

_OPERADORES = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


def _validar_arvore(no: ast.AST, colunas: list[str]) -> None:
    if isinstance(no, ast.Expression):
        _validar_arvore(no.body, colunas)
    elif isinstance(no, ast.BinOp):
        if type(no.op) not in _OPERADORES:
            raise SheetError("Fórmula só pode usar +, -, * e / entre colunas e números.")
        _validar_arvore(no.left, colunas)
        _validar_arvore(no.right, colunas)
    elif isinstance(no, ast.UnaryOp):
        if not isinstance(no.op, (ast.UAdd, ast.USub)):
            raise SheetError("Fórmula só pode usar +, -, * e / entre colunas e números.")
        _validar_arvore(no.operand, colunas)
    elif isinstance(no, ast.Name):
        if no.id not in colunas:
            raise SheetError(f"A fórmula usa a coluna '{no.id}', que não existe na planilha.")
    elif isinstance(no, ast.Constant):
        if not isinstance(no.value, (int, float)):
            raise SheetError("Fórmula só pode usar números e nomes de coluna.")
    else:
        raise SheetError("Fórmula usa uma sintaxe não suportada.")


def _parsear(expressao: str, colunas: list[str]) -> ast.Expression:
    try:
        arvore = ast.parse(expressao, mode="eval")
    except SyntaxError as exc:
        raise SheetError(f"Não entendi a fórmula '{expressao}'.") from exc
    _validar_arvore(arvore, colunas)
    return arvore


def calcular_valor(expressao: str, colunas: list[str], valores_linha: dict) -> float:
    """Calcula o resultado da expressão para uma linha específica (valores já numéricos)."""
    arvore = _parsear(expressao, colunas)

    def _avaliar(no: ast.AST):
        if isinstance(no, ast.Expression):
            return _avaliar(no.body)
        if isinstance(no, ast.BinOp):
            esquerda = _avaliar(no.left)
            direita = _avaliar(no.right)
            try:
                return _OPERADORES[type(no.op)](esquerda, direita)
            except ZeroDivisionError as exc:
                raise SheetError("A fórmula tentou dividir por zero.") from exc
        if isinstance(no, ast.UnaryOp):
            valor = _avaliar(no.operand)
            return -valor if isinstance(no.op, ast.USub) else valor
        if isinstance(no, ast.Name):
            valor = valores_linha.get(no.id)
            try:
                return float(valor)
            except (TypeError, ValueError) as exc:
                raise SheetError(
                    f"A coluna '{no.id}' não tem um número válido nessa linha (valor: {valor!r})."
                ) from exc
        if isinstance(no, ast.Constant):
            return float(no.value)
        raise SheetError("Fórmula usa uma sintaxe não suportada.")

    return _avaliar(arvore)


def montar_formula_excel(expressao: str, colunas: list[str], numero_linha: int) -> str:
    """Traduz a expressão em fórmula Excel, trocando nome de coluna por referência de célula.

    `numero_linha` é o número real da linha na planilha (1-indexado, já contando o
    cabeçalho), ex.: primeira linha de dados = 2.
    """
    arvore = _parsear(expressao, colunas)
    indice_coluna = {nome: i + 1 for i, nome in enumerate(colunas)}

    def _traduzir(no: ast.AST) -> str:
        if isinstance(no, ast.Expression):
            return _traduzir(no.body)
        if isinstance(no, ast.BinOp):
            simbolo = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(no.op)]
            return f"({_traduzir(no.left)}{simbolo}{_traduzir(no.right)})"
        if isinstance(no, ast.UnaryOp):
            sinal = "-" if isinstance(no.op, ast.USub) else ""
            return f"{sinal}{_traduzir(no.operand)}"
        if isinstance(no, ast.Name):
            letra = get_column_letter(indice_coluna[no.id])
            return f"{letra}{numero_linha}"
        if isinstance(no, ast.Constant):
            return str(no.value)
        raise SheetError("Fórmula usa uma sintaxe não suportada.")

    return f"={_traduzir(arvore)}"
