"""Traduz uma instrução em linguagem natural numa ação estruturada sobre a planilha."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

import groq
from groq import Groq # IA com Free tier generoso

from core.ssl_fix import criar_http_client

MODELO_PADRAO = "openai/gpt-oss-120b"

ACOES_VALIDAS = {"adicionar_linha", "atualizar_celula", "remover_linha"}


class InterpretacaoError(Exception):
    """A IA não conseguiu traduzir a instrução numa ação válida."""


@dataclass
class Acao:
    tipo: Literal["adicionar_linha", "atualizar_celula", "remover_linha"]
    dados: dict
    resumo: str

# Prompt para a IA 
def _prompt_sistema(colunas: list[str], amostra: list[dict]) -> str:
    return f"""Você traduz um pedido em português de um usuário leigo numa única ação
estruturada sobre uma planilha. Responda APENAS com um JSON no formato exato abaixo,
sem nenhum texto antes ou depois.

Colunas reais da planilha (use exatamente estes nomes, nunca invente coluna nova):
{colunas}

Amostra das primeiras linhas (linha 1 = primeira linha de dados, começando em 1):
{json.dumps(amostra, ensure_ascii=False)}

Formatos de resposta possíveis:

Para adicionar uma linha nova:
{{"tipo": "adicionar_linha", "dados": {{"<coluna>": "<valor>", ...}}, "resumo": "frase curta explicando o que vai acontecer"}}

Para atualizar uma célula existente:
{{"tipo": "atualizar_celula", "dados": {{"linha": <int, 1-indexado>, "coluna": "<coluna>", "valor": "<novo valor>"}}, "resumo": "..."}}

Para remover uma linha:
{{"tipo": "remover_linha", "dados": {{"linha": <int, 1-indexado>}}, "resumo": "..."}}

Se o pedido for ambíguo ou impossível com as colunas disponíveis, responda:
{{"tipo": "erro", "dados": {{}}, "resumo": "explicação curta do motivo"}}
"""


def interpretar(
    instrucao: str,
    colunas: list[str],
    amostra: list[dict],
    api_key: str,
    modelo: str = MODELO_PADRAO,
) -> Acao:
    """Chama a Groq API e devolve a ação estruturada correspondente à instrução."""

    cliente = Groq(api_key=api_key, http_client=criar_http_client())
    try:
        resposta_bruta = cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": _prompt_sistema(colunas, amostra)},
                {"role": "user", "content": instrucao},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except groq.AuthenticationError as exc:
        raise InterpretacaoError(
            "Chave da API inválida ou expirada. Confira a chave na barra lateral."
        ) from exc
    except groq.RateLimitError as exc:
        raise InterpretacaoError(
            "Limite de uso da IA atingido no momento. Aguarde um pouco e tente de novo."
        ) from exc
    except groq.APIConnectionError as exc:
        raise InterpretacaoError(
            "Não foi possível conectar ao servidor da IA. Verifique sua internet e tente de novo."
        ) from exc
    except groq.APIStatusError as exc:
        raise InterpretacaoError(
            f"O servidor da IA retornou um erro (código {exc.status_code}). Tente de novo em instantes."
        ) from exc
    except groq.GroqError as exc:
        raise InterpretacaoError("Não foi possível falar com a IA agora. Tente de novo.") from exc

    resposta = resposta_bruta.choices[0].message.content

    # Interpretar a resposta da IA como JSON
    try:
        payload = json.loads(resposta)
    except json.JSONDecodeError as exc:
        raise InterpretacaoError(f"Resposta da IA não é um JSON válido: {resposta}") from exc

    # identificar o tipo de ação e validar
    tipo = payload.get("tipo")
    if tipo == "erro":
        raise InterpretacaoError(payload.get("resumo", "Pedido não pôde ser interpretado."))
    if tipo not in ACOES_VALIDAS:
        raise InterpretacaoError(f"Tipo de ação desconhecido retornado pela IA: {tipo!r}")

    dados = payload.get("dados", {})
    if tipo in {"atualizar_celula", "remover_linha"} and "linha" in dados:
        # A IA responde com linha 1-indexada (mais natural pra um leigo); o
        # SheetManager trabalha 0-indexado internamente.
        dados["linha"] = int(dados["linha"]) - 1

    return Acao(tipo=tipo, dados=dados, resumo=payload.get("resumo", ""))
