"""Traduz uma instrução em linguagem natural num plano de ações estruturadas sobre a planilha."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

import groq
from groq import Groq  # IA com Free tier generoso

from core.sheet_manager import ACOES_VALIDAS
from core.ssl_fix import criar_http_client

MODELO_PADRAO = "openai/gpt-oss-120b"


class InterpretacaoError(Exception):
    """A IA não conseguiu traduzir a instrução num plano de ações válido."""


@dataclass
class Acao:
    tipo: str
    dados: dict
    resumo: str


@dataclass
class Plano:
    acoes: list[Acao] = field(default_factory=list)


# Prompt para a IA
def _prompt_sistema(colunas: list[str], amostra: list[dict], total_linhas: int) -> str:
    return f"""Você traduz um pedido em português de um usuário leigo num plano de uma ou
mais ações estruturadas sobre uma planilha. Responda APENAS com um JSON no formato exato
abaixo, sem nenhum texto antes ou depois:

{{"acoes": [ {{"tipo": "...", "dados": {{...}}, "resumo": "frase curta explicando o que vai acontecer"}}, ... ]}}

Colunas reais da planilha (use exatamente estes nomes, nunca invente coluna nova a menos
que a ação seja justamente criar essa coluna):
{colunas}

A planilha tem exatamente {total_linhas} linha(s) de dados, numeradas de 1 a {total_linhas}.
NUNCA use, em nenhuma ação, um número de linha maior que {total_linhas} nem menor que 1 (isso
inclui a lista "linhas" de formatar_coluna) - isso quebraria o pedido. Se o pedido pedir pra
formatar "todas as linhas" ou "a planilha toda", prefira omitir a lista "linhas" (ou usar a
ação colorir_linhas_alternadas, que já cobre todas as linhas sozinha) em vez de listar os
números manualmente.

Amostra das primeiras linhas (linha 1 = primeira linha de dados, começando em 1):
{json.dumps(amostra, ensure_ascii=False)}

Hoje é {date.today().isoformat()} (use o ano atual se o pedido envolver idade, data ou ano,
ex.: "ano de nascimento" = ano atual menos a idade).

Tipos de ação possíveis e o formato de "dados" de cada um:

adicionar_linha: {{"<coluna>": "<valor>", ...}} (uma entrada por coluna existente)

atualizar_celula: {{"linha": <int, 1-indexado>, "coluna": "<coluna>", "valor": "<novo valor>"}}

remover_linha: {{"linha": <int, 1-indexado>}}

adicionar_coluna: {{"coluna": "<nome da coluna nova>", "valor_padrao": "<valor para todas as linhas>"}}

adicionar_coluna_calculada: {{"coluna": "<nome da coluna nova>", "expressao": "<coluna A> * <coluna B>"}}
  (expressão só pode usar nomes de colunas já existentes na planilha OU de uma coluna criada
  por uma ação anterior nesse mesmo plano, números, e os operadores + - * /. Não suporta
  funções de data/texto nem número da linha; para isso use adicionar_coluna_sequencia.)

adicionar_coluna_sequencia: {{"coluna": "<nome da coluna nova>", "valor_inicial": <número>, "incremento": <número>}}
  (preenche uma sequência numérica: primeira linha = valor_inicial, cada linha seguinte
  soma incremento; use incremento negativo para uma sequência decrescente. Ex.: "idade da
  primeira pessoa é 50 e vai diminuindo" = valor_inicial 50, incremento -1)

remover_coluna: {{"coluna": "<coluna>"}}

renomear_coluna: {{"coluna_atual": "<coluna>", "coluna_nova": "<novo nome>"}}

atualizar_em_massa: {{"coluna": "<coluna a mudar>", "valor_novo": "<novo valor>",
  "condicao_coluna": "<coluna da condição>", "condicao_operador": "igual" | "diferente" | "contem" | "maior_que" | "menor_que",
  "condicao_valor": "<valor da condição>"}}

inserir_total: {{"coluna": "<coluna numérica>", "operacao": "soma" | "media" | "contagem" | "maximo" | "minimo"}}

formatar_coluna: {{"coluna": "<coluna>", "negrito": true|false, "italico": true|false,
  "cor_fundo": "<hex sem #, ex: FFCC00>", "cor_texto": "<hex sem #>",
  "formato_numero": "moeda" | "porcentagem" | "data" | "padrao", "tamanho_fonte": <int, opcional>,
  "linhas": [<int 1-indexado>, ...] (opcional, omita para a coluna toda),
  "incluir_cabecalho": true|false (opcional, default false; use true quando o pedido falar em
  "cabeçalho", "título da coluna" ou primeira linha da planilha, além ou no lugar das linhas de dados)}}

ajustar_largura_coluna: {{"coluna": "<coluna>", "largura": <int, opcional>}}
  (número de caracteres de largura; omita "largura" para ajuste automático baseado no
  conteúdo mais longo da coluna)

congelar_cabecalho: {{"ativar": true|false (opcional, default true)}}
  (trava a primeira linha no topo ao rolar a planilha; "ativar": false desfaz isso)

colorir_linhas_alternadas: {{"cor_par": "<hex sem #, opcional>", "cor_impar": "<hex sem #, opcional>"}}
  (pinta o fundo de TODAS as colunas, alternando uma cor a cada linha de dados, tipo "linhas
  zebradas" de planilha profissional; use esta ação para pedidos como "linhas com cores
  diferentes", "zebrado", "listrado", "planilha mais fácil de ler" - nunca tente simular isso
  chamando formatar_coluna várias vezes com listas de linha manuais, é mais fácil de errar.
  Se o pedido não especificar cores, omita os dois campos: o app usa um estilo discreto por
  padrão, cinza claro alternado com branco.)

Se o pedido for só "deixa o cabeçalho bonito"/"formata o cabeçalho" sem especificar cor,
negrito etc., use formatar_coluna com "incluir_cabecalho": true e escolha um estilo razoável
(ex.: negrito) em vez de responder com erro. Se o pedido for sobre o cabeçalho mas a única
coisa pedida for algo sem ação equivalente (ex.: mudar a fonte para "Arial"), responda com
"erro" explicando que só é possível mudar cor, negrito, itálico e tamanho da fonte.

Uma instrução pode virar mais de uma ação na lista "acoes", aplicadas nessa ordem (ex.:
"adiciona um cliente novo e marca a linha 2 como concluída" vira duas ações). Uma ação
pode usar uma coluna criada por uma ação anterior na mesma lista (ex.: "cria a coluna
Idade decrescente a partir de 50 e depois uma coluna Ano de Nascimento com base nela" vira
duas ações: adicionar_coluna_sequencia pra Idade, depois adicionar_coluna_calculada pra Ano
de Nascimento usando a coluna Idade).

Se o pedido for ambíguo, impossível com as colunas disponíveis, ou não tiver relação
nenhuma com editar a planilha, responda:
{{"acoes": [{{"tipo": "erro", "dados": {{}}, "resumo": "explicação curta do motivo"}}]}}
"""


def interpretar(
    instrucao: str,
    colunas: list[str],
    amostra: list[dict],
    total_linhas: int,
    api_key: str,
    modelo: str = MODELO_PADRAO,
) -> Plano:
    """Chama a Groq API e devolve o plano de ações estruturadas correspondente à instrução."""

    cliente = Groq(api_key=api_key, http_client=criar_http_client())
    try:
        resposta_bruta = cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": _prompt_sistema(colunas, amostra, total_linhas)},
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

    try:
        payload = json.loads(resposta)
    except json.JSONDecodeError as exc:
        raise InterpretacaoError(f"Resposta da IA não é um JSON válido: {resposta}") from exc

    return _validar_payload(payload)


def _validar_payload(payload) -> Plano:
    if not isinstance(payload, dict):
        raise InterpretacaoError("A IA não respondeu no formato esperado.")

    lista_acoes = payload.get("acoes")
    if not isinstance(lista_acoes, list) or not lista_acoes:
        raise InterpretacaoError("A IA não devolveu nenhuma ação para o pedido.")

    acoes = []
    for item in lista_acoes:
        if not isinstance(item, dict):
            raise InterpretacaoError("A IA devolveu uma ação em formato inesperado.")

        tipo = item.get("tipo")
        resumo = item.get("resumo", "")
        if tipo == "erro":
            raise InterpretacaoError(resumo or "Pedido não pôde ser interpretado.")
        if tipo not in ACOES_VALIDAS:
            raise InterpretacaoError(f"Tipo de ação desconhecido retornado pela IA: {tipo!r}")

        dados = item.get("dados", {})
        if not isinstance(dados, dict):
            raise InterpretacaoError(f"Dados inválidos para a ação '{tipo}'.")

        dados = _normalizar_linhas_para_zero_indexado(tipo, dados)
        acoes.append(Acao(tipo=tipo, dados=dados, resumo=resumo))

    return Plano(acoes=acoes)


def _normalizar_linhas_para_zero_indexado(tipo: str, dados: dict) -> dict:
    """A IA responde com linha 1-indexada (mais natural pra um leigo); o SheetManager
    trabalha 0-indexado internamente."""
    if tipo in {"atualizar_celula", "remover_linha"} and "linha" in dados:
        try:
            dados["linha"] = int(dados["linha"]) - 1
        except (TypeError, ValueError) as exc:
            raise InterpretacaoError(f"A IA devolveu um número de linha inválido: {dados['linha']!r}") from exc
    return dados
