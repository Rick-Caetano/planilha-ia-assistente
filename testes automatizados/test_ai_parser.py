"""Testa interpretar(): parsing da resposta da IA, sem chamar a Groq de verdade."""
import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from core import ai_parser
from core.ai_parser import InterpretacaoError, interpretar

_REQUEST_FAKE = httpx.Request("POST", "https://api.groq.com")
_RESPOSTA_401 = httpx.Response(401, request=_REQUEST_FAKE)
_RESPOSTA_429 = httpx.Response(429, request=_REQUEST_FAKE)


def _resposta_fake(conteudo: str):
    """Monta um objeto com o mesmo formato de resposta_bruta.choices[0].message.content."""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=conteudo))])


class _ClienteFake:
    """Substitui groq.Groq: devolve `resposta` ou levanta `excecao`, sem rede."""

    def __init__(self, resposta=None, excecao=None):
        self._resposta = resposta
        self._excecao = excecao
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        if self._excecao:
            raise self._excecao
        return self._resposta


def _interpretar_com_resposta(monkeypatch, payload_dict):
    cliente = _ClienteFake(resposta=_resposta_fake(json.dumps(payload_dict)))
    monkeypatch.setattr(ai_parser, "Groq", lambda **kwargs: cliente)
    return interpretar(instrucao="qualquer coisa", colunas=["Nome"], amostra=[], total_linhas=3, api_key="fake")


def _interpretar_com_excecao(monkeypatch, excecao):
    cliente = _ClienteFake(excecao=excecao)
    monkeypatch.setattr(ai_parser, "Groq", lambda **kwargs: cliente)
    return interpretar(instrucao="qualquer coisa", colunas=["Nome"], amostra=[], total_linhas=3, api_key="fake")


# -- plano válido ---------------------------------------------------------


def test_plano_com_varias_acoes(monkeypatch):
    payload = {
        "acoes": [
            {"tipo": "adicionar_linha", "dados": {"Nome": "Maria"}, "resumo": "adiciona Maria"},
            {"tipo": "atualizar_celula", "dados": {"linha": 2, "coluna": "Nome", "valor": "x"}, "resumo": "atualiza"},
        ]
    }
    plano = _interpretar_com_resposta(monkeypatch, payload)
    assert len(plano.acoes) == 2
    assert plano.acoes[0].tipo == "adicionar_linha"
    # linha vem 1-indexada da IA e é convertida pra 0-indexada internamente
    assert plano.acoes[1].dados["linha"] == 1


def test_tipo_erro_vira_interpretacao_error(monkeypatch):
    payload = {"acoes": [{"tipo": "erro", "dados": {}, "resumo": "pedido não faz sentido"}]}
    with pytest.raises(InterpretacaoError, match="pedido não faz sentido"):
        _interpretar_com_resposta(monkeypatch, payload)


def test_tipo_desconhecido_vira_interpretacao_error(monkeypatch):
    payload = {"acoes": [{"tipo": "apagar_planilha_inteira", "dados": {}, "resumo": "x"}]}
    with pytest.raises(InterpretacaoError):
        _interpretar_com_resposta(monkeypatch, payload)


def test_acoes_ausente_vira_interpretacao_error(monkeypatch):
    with pytest.raises(InterpretacaoError):
        _interpretar_com_resposta(monkeypatch, {"algo_errado": []})


def test_acoes_vazia_vira_interpretacao_error(monkeypatch):
    with pytest.raises(InterpretacaoError):
        _interpretar_com_resposta(monkeypatch, {"acoes": []})


def test_dados_nao_e_dict_vira_interpretacao_error(monkeypatch):
    payload = {"acoes": [{"tipo": "adicionar_linha", "dados": "não é um dict", "resumo": "x"}]}
    with pytest.raises(InterpretacaoError):
        _interpretar_com_resposta(monkeypatch, payload)


def test_json_malformado_vira_interpretacao_error(monkeypatch):
    cliente = _ClienteFake(resposta=_resposta_fake("isso não é JSON"))
    monkeypatch.setattr(ai_parser, "Groq", lambda **kwargs: cliente)
    with pytest.raises(InterpretacaoError):
        interpretar(instrucao="x", colunas=["Nome"], amostra=[], total_linhas=3, api_key="fake")


def test_linha_invalida_vira_interpretacao_error(monkeypatch):
    payload = {
        "acoes": [{"tipo": "remover_linha", "dados": {"linha": "não é número"}, "resumo": "x"}]
    }
    with pytest.raises(InterpretacaoError):
        _interpretar_com_resposta(monkeypatch, payload)


# -- exceções da Groq ---------------------------------------------------------


@pytest.mark.parametrize(
    "excecao, trecho_esperado",
    [
        (groq.AuthenticationError("x", response=_RESPOSTA_401, body=None), "Chave da API"),
        (groq.RateLimitError("x", response=_RESPOSTA_429, body=None), "Limite de uso"),
        (groq.APIConnectionError(request=_REQUEST_FAKE), "conectar"),
        (groq.APITimeoutError(request=_REQUEST_FAKE), "conectar"),  # é subclasse de APIConnectionError
        (groq.InternalServerError("x", response=httpx.Response(500, request=_REQUEST_FAKE), body=None), "servidor da IA"),
    ],
)
def test_erros_da_groq_viram_mensagem_amigavel(monkeypatch, excecao, trecho_esperado):
    with pytest.raises(InterpretacaoError, match=trecho_esperado):
        _interpretar_com_excecao(monkeypatch, excecao)
