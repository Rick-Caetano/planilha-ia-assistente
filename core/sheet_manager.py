"""Leitura, validação e escrita de planilhas .xlsx usadas pelo assistente."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


class SheetError(Exception):
    """Erro de dados ou de ação inválida sobre a planilha."""


class SheetManager:
    """Envolve um arquivo .xlsx e expõe operações seguras de leitura/escrita.

    Nunca aplica uma ação sem antes validar que ela é compatível com as
    colunas reais da planilha carregada, evita que uma alucinação da IA
    (nome de coluna inventado, linha fora do intervalo) corrompa o arquivo.
    """

    def __init__(self, caminho: str | Path, nome_planilha: str | int = 0):
        self.caminho = Path(caminho)
        self.nome_planilha = nome_planilha
        self.dataframe = pd.read_excel(self.caminho, sheet_name=nome_planilha)

    @property
    def columns(self) -> list[str]:
        return list(self.dataframe.columns)

    def ver_linhas(self, num: int = 5) -> list[dict]:
        return self.dataframe.head(num).to_dict(orient="records")

    def _validar_colunas(self, colunas: dict) -> None:
        colunas_desconhecidas = set(colunas) - set(self.columns)
        if colunas_desconhecidas:
            raise SheetError(
                f"Coluna(s) inexistente(s) na planilha: {', '.join(sorted(colunas_desconhecidas))}. "
                f"Colunas válidas: {', '.join(self.columns)}"
            )

    def adicionar_linha(self, dados: dict) -> None:
        self._validar_colunas(dados)
        nova_linha = {col: dados.get(col, "") for col in self.columns}
        self.dataframe.loc[len(self.dataframe)] = nova_linha

    def atualizar_celula(self, linha: int, coluna: str, valor) -> None:
        self._validar_colunas({coluna: valor})
        if not (0 <= linha < len(self.dataframe)):
            raise SheetError(
                f"Linha {linha + 1} não existe. A planilha tem {len(self.dataframe)} linha(s) de dados."
            )
        self.dataframe.at[linha, coluna] = valor

    def remover_linha(self, linha: int) -> None:
        if not (0 <= linha < len(self.dataframe)):
            raise SheetError(
                f"Linha {linha + 1} não existe. A planilha tem {len(self.dataframe)} linha(s) de dados."
            )
        self.dataframe = self.dataframe.drop(index=linha).reset_index(drop=True)

    def salvar(self, destino: str | Path | None = None) -> Path:
        destino = Path(destino) if destino else self.caminho
        self.dataframe.to_excel(destino, sheet_name=self._nome_aba_saida(), index=False)
        return destino

    def _nome_aba_saida(self) -> str:
        if isinstance(self.nome_planilha, str):
            return self.nome_planilha
        try:
            return load_workbook(self.caminho, read_only=True).sheetnames[self.nome_planilha]
        except Exception:
            return "Sheet1"
