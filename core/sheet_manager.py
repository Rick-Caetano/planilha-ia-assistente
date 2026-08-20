"""Leitura, validação e escrita de planilhas .xlsx usadas pelo assistente.

Trabalha direto em cima do workbook do openpyxl (não via pandas), para preservar
formatação e fórmulas que já existiam no arquivo entre um salvamento e outro. O pandas
ainda é usado, mas só como projeção de leitura (`dataframe`) para exibir a planilha na
tela e para cálculos de prévia.
"""
from __future__ import annotations

import io
import re
import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from core.errors import SheetError
from core.formula_utils import calcular_valor, montar_formula_excel

OPERADORES_CONDICAO = {"igual", "diferente", "contem", "maior_que", "menor_que"}

FORMATOS_NUMERO = {
    "moeda": "R$ #,##0.00",
    "porcentagem": "0.00%",
    "data": "DD/MM/YYYY",
    "padrao": "General",
}

OPERACOES_TOTAL = {
    "soma": ("SUM", sum),
    "media": ("AVERAGE", lambda valores: sum(valores) / len(valores)),
    "contagem": ("COUNTA", len),
    "maximo": ("MAX", max),
    "minimo": ("MIN", min),
}

_LINHA_CABECALHO = 1
_PRIMEIRA_LINHA_DADOS = 2

_REGEX_COR_HEX = re.compile(r"^[0-9A-Fa-f]{6}$")

_LARGURA_COLUNA_MINIMA = 4
_LARGURA_COLUNA_MAXIMA = 100

ACOES_VALIDAS = {
    "adicionar_linha",
    "atualizar_celula",
    "remover_linha",
    "adicionar_coluna",
    "adicionar_coluna_calculada",
    "adicionar_coluna_sequencia",
    "remover_coluna",
    "renomear_coluna",
    "atualizar_em_massa",
    "inserir_total",
    "formatar_coluna",
    "ajustar_largura_coluna",
    "congelar_cabecalho",
    "colorir_linhas_alternadas",
}

_COR_LINHA_PAR_PADRAO = "FFFFFF"
_COR_LINHA_IMPAR_PADRAO = "F2F2F2"


class SheetManager:
    """Envolve um arquivo .xlsx e expõe operações seguras de leitura/escrita.

    Cada operação valida a ação contra as colunas e linhas reais da planilha antes de
    escrever, para uma alucinação da IA (coluna inventada, linha fora do intervalo,
    fórmula com sintaxe estranha) nunca corromper o arquivo nem derrubar o app.
    """

    def __init__(self, origem, nome_planilha: str | int = 0):
        self.nome_planilha = nome_planilha
        if isinstance(origem, (str, Path)):
            self.caminho = Path(origem)
        else:
            # Objeto tipo st.file_uploader (fica só em memória, sem caminho próprio no
            # disco): grava uma cópia local para poder salvar e oferecer o download depois.
            nome = getattr(origem, "name", "planilha.xlsx")
            self.caminho = Path(tempfile.gettempdir()) / f"assistente_planilhas_{nome}"
            conteudo = origem.getvalue() if hasattr(origem, "getvalue") else origem.read()
            self.caminho.write_bytes(conteudo)
        self._carregar()

    def _carregar(self) -> None:
        self.workbook = load_workbook(self.caminho)
        if isinstance(self.nome_planilha, str):
            self.worksheet = self.workbook[self.nome_planilha]
        else:
            self.worksheet = self.workbook.worksheets[self.nome_planilha]

    # -- projeções de leitura -------------------------------------------------

    @property
    def dataframe(self) -> pd.DataFrame:
        linhas = list(self.worksheet.iter_rows(values_only=True))
        if not linhas:
            return pd.DataFrame()
        cabecalho, *dados = linhas
        return pd.DataFrame(dados, columns=list(cabecalho))

    @property
    def columns(self) -> list[str]:
        return list(self.dataframe.columns)

    def ver_linhas(self, num: int = 5) -> list[dict]:
        return self.dataframe.head(num).to_dict(orient="records")

    @property
    def total_linhas(self) -> int:
        return len(self.dataframe)

    # -- validações compartilhadas ---------------------------------------------

    def _validar_coluna(self, coluna: str) -> None:
        if coluna not in self.columns:
            raise SheetError(
                f"Coluna '{coluna}' não existe na planilha. Colunas válidas: "
                f"{', '.join(self.columns)}"
            )

    def _validar_linha(self, linha: int) -> None:
        if not (0 <= linha < self.total_linhas):
            raise SheetError(
                f"Linha {linha + 1} não existe. A planilha tem {self.total_linhas} linha(s) de dados."
            )

    def _numero_linha_planilha(self, indice_0: int) -> int:
        return _PRIMEIRA_LINHA_DADOS + indice_0

    def _numero_coluna_planilha(self, coluna: str) -> int:
        return self.columns.index(coluna) + 1

    # -- ações -------------------------------------------------------------

    def adicionar_linha(self, **dados) -> dict:
        """`dados` são as colunas soltas como kwargs (ex.: Nome="Carlos"), não um dict
        aninhado, para bater com o despacho genérico de `_executar_acao`."""
        colunas_desconhecidas = set(dados) - set(self.columns)
        if colunas_desconhecidas:
            raise SheetError(
                f"Coluna(s) inexistente(s) na planilha: {', '.join(sorted(colunas_desconhecidas))}."
            )
        valores = {col: dados.get(col, "") for col in self.columns}
        numero_linha = self._numero_linha_planilha(self.total_linhas)
        for coluna, valor in valores.items():
            self.worksheet.cell(
                row=numero_linha, column=self._numero_coluna_planilha(coluna), value=valor
            )
        return {"valores": valores}

    def atualizar_celula(self, linha: int, coluna: str, valor) -> dict:
        self._validar_coluna(coluna)
        self._validar_linha(linha)
        valor_antigo = self.dataframe.at[linha, coluna]
        self.worksheet.cell(
            row=self._numero_linha_planilha(linha),
            column=self._numero_coluna_planilha(coluna),
            value=valor,
        )
        return {"linha": linha + 1, "coluna": coluna, "valor_antigo": valor_antigo, "valor_novo": valor}

    def remover_linha(self, linha: int) -> dict:
        self._validar_linha(linha)
        valores_removidos = self.dataframe.iloc[linha].to_dict()
        self.worksheet.delete_rows(self._numero_linha_planilha(linha))
        return {"linha": linha + 1, "valores_removidos": valores_removidos}

    def adicionar_coluna(self, coluna: str, valor_padrao=None) -> dict:
        if coluna in self.columns:
            raise SheetError(f"A coluna '{coluna}' já existe na planilha.")
        valor_padrao = "" if valor_padrao is None else valor_padrao
        numero_coluna = len(self.columns) + 1
        self.worksheet.cell(row=_LINHA_CABECALHO, column=numero_coluna, value=coluna)
        for indice in range(self.total_linhas):
            self.worksheet.cell(
                row=self._numero_linha_planilha(indice), column=numero_coluna, value=valor_padrao
            )
        return {"coluna": coluna, "valor_padrao": valor_padrao, "linhas_preenchidas": self.total_linhas}

    def adicionar_coluna_calculada(self, coluna: str, expressao: str) -> dict:
        if coluna in self.columns:
            raise SheetError(f"A coluna '{coluna}' já existe na planilha.")
        colunas_existentes = self.columns
        df = self.dataframe
        valores_calculados = []
        for indice in range(self.total_linhas):
            valores_linha = df.iloc[indice].to_dict()
            valor = calcular_valor(expressao, colunas_existentes, valores_linha)
            valores_calculados.append({"linha": indice + 1, "valor": valor})

        numero_coluna = len(self.columns) + 1
        self.worksheet.cell(row=_LINHA_CABECALHO, column=numero_coluna, value=coluna)
        for indice in range(self.total_linhas):
            formula = montar_formula_excel(
                expressao, colunas_existentes, self._numero_linha_planilha(indice)
            )
            self.worksheet.cell(
                row=self._numero_linha_planilha(indice), column=numero_coluna, value=formula
            )
        return {"coluna": coluna, "expressao": expressao, "valores": valores_calculados}

    def adicionar_coluna_sequencia(self, coluna: str, valor_inicial: float, incremento: float) -> dict:
        """Nova coluna com uma sequência numérica: primeira linha = valor_inicial, cada
        linha seguinte soma `incremento` (pode ser negativo, ex.: idade decrescente)."""
        if coluna in self.columns:
            raise SheetError(f"A coluna '{coluna}' já existe na planilha.")
        numero_coluna = len(self.columns) + 1
        self.worksheet.cell(row=_LINHA_CABECALHO, column=numero_coluna, value=coluna)
        valores = []
        for indice in range(self.total_linhas):
            valor = valor_inicial + indice * incremento
            self.worksheet.cell(row=self._numero_linha_planilha(indice), column=numero_coluna, value=valor)
            valores.append({"linha": indice + 1, "valor": valor})
        return {"coluna": coluna, "valor_inicial": valor_inicial, "incremento": incremento, "valores": valores}

    def remover_coluna(self, coluna: str) -> dict:
        self._validar_coluna(coluna)
        self.worksheet.delete_cols(self._numero_coluna_planilha(coluna))
        return {"coluna": coluna}

    def renomear_coluna(self, coluna_atual: str, coluna_nova: str) -> dict:
        self._validar_coluna(coluna_atual)
        if coluna_nova in self.columns:
            raise SheetError(f"Já existe uma coluna chamada '{coluna_nova}'.")
        self.worksheet.cell(
            row=_LINHA_CABECALHO, column=self._numero_coluna_planilha(coluna_atual), value=coluna_nova
        )
        return {"de": coluna_atual, "para": coluna_nova}

    def atualizar_em_massa(
        self,
        coluna: str,
        valor_novo,
        condicao_coluna: str,
        condicao_operador: str,
        condicao_valor,
    ) -> dict:
        self._validar_coluna(coluna)
        self._validar_coluna(condicao_coluna)
        if condicao_operador not in OPERADORES_CONDICAO:
            raise SheetError(
                f"Condição '{condicao_operador}' não é suportada. "
                f"Use uma destas: {', '.join(sorted(OPERADORES_CONDICAO))}."
            )

        df = self.dataframe
        linhas_afetadas = []
        for indice in range(self.total_linhas):
            valor_atual = df.at[indice, condicao_coluna]
            if self._condicao_bate(valor_atual, condicao_operador, condicao_valor):
                linhas_afetadas.append(
                    {"linha": indice + 1, "valor_antigo": df.at[indice, coluna]}
                )

        numero_coluna = self._numero_coluna_planilha(coluna)
        for item in linhas_afetadas:
            self.worksheet.cell(
                row=self._numero_linha_planilha(item["linha"] - 1),
                column=numero_coluna,
                value=valor_novo,
            )
        return {
            "coluna": coluna,
            "valor_novo": valor_novo,
            "condicao": f"{condicao_coluna} {condicao_operador} {condicao_valor}",
            "linhas_afetadas": linhas_afetadas,
        }

    @staticmethod
    def _condicao_bate(valor_atual, operador: str, valor_esperado) -> bool:
        if operador in {"igual", "diferente", "contem"}:
            texto_atual = "" if valor_atual is None else str(valor_atual).strip().lower()
            texto_esperado = str(valor_esperado).strip().lower()
            if operador == "igual":
                return texto_atual == texto_esperado
            if operador == "diferente":
                return texto_atual != texto_esperado
            return texto_esperado in texto_atual

        try:
            numero_atual = float(valor_atual)
            numero_esperado = float(valor_esperado)
        except (TypeError, ValueError) as exc:
            raise SheetError(
                f"Não é possível comparar '{valor_atual}' numericamente para aplicar essa condição."
            ) from exc
        if operador == "maior_que":
            return numero_atual > numero_esperado
        return numero_atual < numero_esperado

    def inserir_total(self, coluna: str, operacao: str) -> dict:
        self._validar_coluna(coluna)
        if operacao not in OPERACOES_TOTAL:
            raise SheetError(
                f"Operação '{operacao}' não é suportada. "
                f"Use uma destas: {', '.join(sorted(OPERACOES_TOTAL))}."
            )
        nome_funcao_excel, funcao_python = OPERACOES_TOTAL[operacao]

        df = self.dataframe
        if operacao == "contagem":
            resultado = funcao_python(df[coluna].dropna())
        else:
            try:
                valores_numericos = [float(v) for v in df[coluna] if v is not None and v != ""]
            except (TypeError, ValueError) as exc:
                raise SheetError(f"A coluna '{coluna}' não tem só números, não dá pra calcular {operacao}.") from exc
            if not valores_numericos:
                raise SheetError(f"A coluna '{coluna}' está vazia, não tem o que calcular.")
            resultado = funcao_python(valores_numericos)

        numero_coluna = self._numero_coluna_planilha(coluna)
        numero_linha_total = self._numero_linha_planilha(self.total_linhas)
        primeira_linha_dados = self._numero_linha_planilha(0)
        ultima_linha_dados = numero_linha_total - 1
        letra_coluna = get_column_letter(numero_coluna)
        formula = f"={nome_funcao_excel}({letra_coluna}{primeira_linha_dados}:{letra_coluna}{ultima_linha_dados})"
        self.worksheet.cell(row=numero_linha_total, column=1, value=operacao.capitalize())
        self.worksheet.cell(row=numero_linha_total, column=numero_coluna, value=formula)

        return {"coluna": coluna, "operacao": operacao, "resultado": resultado}

    def formatar_coluna(
        self,
        coluna: str,
        negrito: bool | None = None,
        italico: bool | None = None,
        cor_fundo: str | None = None,
        cor_texto: str | None = None,
        formato_numero: str | None = None,
        tamanho_fonte: int | None = None,
        linhas: list[int] | None = None,
        incluir_cabecalho: bool = False,
    ) -> dict:
        self._validar_coluna(coluna)
        if not any([negrito, italico, cor_fundo, cor_texto, formato_numero, tamanho_fonte]):
            raise SheetError("Nenhuma formatação foi especificada para aplicar.")
        for cor, nome in ((cor_fundo, "cor de fundo"), (cor_texto, "cor de texto")):
            if cor and not _REGEX_COR_HEX.match(cor):
                raise SheetError(f"A {nome} '{cor}' não é uma cor hexadecimal válida (ex.: FFCC00).")
        if formato_numero and formato_numero not in FORMATOS_NUMERO:
            raise SheetError(
                f"Formato de número '{formato_numero}' não é suportado. "
                f"Use um destes: {', '.join(sorted(FORMATOS_NUMERO))}."
            )
        if tamanho_fonte is not None and not (1 <= tamanho_fonte <= 100):
            raise SheetError(f"Tamanho de fonte '{tamanho_fonte}' fora do razoável (use entre 1 e 100).")
        if linhas is not None:
            for linha in linhas:
                self._validar_linha(linha - 1)

        indices_linhas = [l - 1 for l in linhas] if linhas is not None else list(range(self.total_linhas))
        linhas_planilha = [self._numero_linha_planilha(indice) for indice in indices_linhas]
        if incluir_cabecalho:
            linhas_planilha.append(_LINHA_CABECALHO)

        numero_coluna = self._numero_coluna_planilha(coluna)
        for numero_linha in linhas_planilha:
            celula = self.worksheet.cell(row=numero_linha, column=numero_coluna)
            if negrito is not None or italico is not None or tamanho_fonte is not None:
                celula.font = Font(
                    bold=bool(negrito), italic=bool(italico), color=cor_texto, size=tamanho_fonte or 11
                )
            elif cor_texto:
                celula.font = Font(color=cor_texto)
            if cor_fundo:
                celula.fill = PatternFill(start_color=cor_fundo, end_color=cor_fundo, fill_type="solid")
            if formato_numero:
                celula.number_format = FORMATOS_NUMERO[formato_numero]

        return {
            "coluna": coluna,
            "linhas": "todas" if linhas is None else linhas,
            "incluir_cabecalho": incluir_cabecalho,
            "negrito": negrito,
            "italico": italico,
            "cor_fundo": cor_fundo,
            "cor_texto": cor_texto,
            "formato_numero": formato_numero,
            "tamanho_fonte": tamanho_fonte,
        }

    def ajustar_largura_coluna(self, coluna: str, largura: int | None = None) -> dict:
        self._validar_coluna(coluna)
        if largura is None:
            maior_conteudo = max(
                (len(str(valor)) for valor in [coluna, *self.dataframe[coluna].tolist()] if valor is not None),
                default=len(coluna),
            )
            largura = maior_conteudo + 2
        if not (_LARGURA_COLUNA_MINIMA <= largura <= _LARGURA_COLUNA_MAXIMA):
            raise SheetError(
                f"Largura '{largura}' fora do razoável "
                f"(use entre {_LARGURA_COLUNA_MINIMA} e {_LARGURA_COLUNA_MAXIMA})."
            )
        letra_coluna = get_column_letter(self._numero_coluna_planilha(coluna))
        self.worksheet.column_dimensions[letra_coluna].width = largura
        return {"coluna": coluna, "largura": largura}

    def congelar_cabecalho(self, ativar: bool = True) -> dict:
        self.worksheet.freeze_panes = f"A{_PRIMEIRA_LINHA_DADOS}" if ativar else None
        return {"ativar": ativar}

    def colorir_linhas_alternadas(
        self, cor_par: str | None = None, cor_impar: str | None = None
    ) -> dict:
        """Pinta o fundo de todas as colunas, alternando cor a cada linha de dados
        (efeito "zebrado"). Não depende da IA saber o total de linhas nem enumerá-las."""
        if self.total_linhas == 0:
            raise SheetError("A planilha não tem nenhuma linha de dados para colorir.")
        cor_par = cor_par or _COR_LINHA_PAR_PADRAO
        cor_impar = cor_impar or _COR_LINHA_IMPAR_PADRAO
        for cor, nome in ((cor_par, "cor das linhas pares"), (cor_impar, "cor das linhas ímpares")):
            if not _REGEX_COR_HEX.match(cor):
                raise SheetError(f"A {nome} '{cor}' não é uma cor hexadecimal válida (ex.: FFCC00).")

        total_colunas = len(self.columns)
        for indice in range(self.total_linhas):
            numero_linha = self._numero_linha_planilha(indice)
            cor = cor_par if indice % 2 == 0 else cor_impar
            preenchimento = PatternFill(start_color=cor, end_color=cor, fill_type="solid")
            for numero_coluna in range(1, total_colunas + 1):
                self.worksheet.cell(row=numero_linha, column=numero_coluna).fill = preenchimento

        return {"cor_par": cor_par, "cor_impar": cor_impar, "linhas_coloridas": self.total_linhas}

    # -- plano de ações -----------------------------------------------------

    def aplicar_plano(self, acoes: list) -> list[dict]:
        """Executa uma lista de ações em sequência, de verdade, no workbook atual.

        Cada ação já pode enxergar o que a ação anterior do mesmo plano acabou de criar
        (ex.: uma coluna calculada pode usar uma coluna criada duas ações antes). Se uma
        ação falhar no meio do caminho, o workbook é recarregado do disco antes do erro
        ser relançado, para nunca deixar o arquivo num estado parcialmente aplicado.
        """
        try:
            return [self._executar_acao(acao) for acao in acoes]
        except SheetError:
            self._carregar()
            raise

    def pre_visualizar_plano(self, acoes: list) -> list[dict]:
        """Roda o mesmo plano de verdade, mas numa cópia descartável do workbook, só
        para validar e montar os detalhes da prévia. O arquivo real nunca é tocado."""
        workbook_real, worksheet_real = self.workbook, self.worksheet
        try:
            self.workbook = self._clonar_workbook()
            if isinstance(self.nome_planilha, str):
                self.worksheet = self.workbook[self.nome_planilha]
            else:
                self.worksheet = self.workbook.worksheets[self.nome_planilha]
            return [self._executar_acao(acao) for acao in acoes]
        finally:
            self.workbook, self.worksheet = workbook_real, worksheet_real

    def _clonar_workbook(self):
        buffer = io.BytesIO()
        self.workbook.save(buffer)
        buffer.seek(0)
        return load_workbook(buffer)

    def _executar_acao(self, acao) -> dict:
        if acao.tipo not in ACOES_VALIDAS:
            raise SheetError(f"Tipo de ação desconhecido: {acao.tipo!r}")
        metodo = getattr(self, acao.tipo)
        try:
            return metodo(**acao.dados)
        except TypeError as exc:
            raise SheetError(f"Dados incompletos ou inválidos para a ação '{acao.tipo}'.") from exc

    def salvar(self, destino: str | Path | None = None) -> Path:
        destino = Path(destino) if destino else self.caminho
        self.workbook.save(destino)
        return destino
