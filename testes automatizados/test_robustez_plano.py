"""Garante que nenhum plano malformado ou 'alucinado' pela IA derruba o app.

Todos os casos abaixo devem virar SheetError (erro amigável, tratável pelo app.py) e a
planilha deve continuar exatamente igual depois, mesmo quando o erro acontece no meio de
um plano de várias ações (rollback).
"""
import pytest

from core.ai_parser import Acao
from core.errors import SheetError

PLANOS_INVALIDOS = [
    pytest.param(
        [Acao(tipo="adicionar_linha", dados={"ColunaFalsa": "x"}, resumo="x")],
        id="coluna_inexistente_ao_adicionar_linha",
    ),
    pytest.param(
        [Acao(tipo="atualizar_celula", dados={"linha": 999, "coluna": "Nome", "valor": "x"}, resumo="x")],
        id="linha_fora_do_intervalo",
    ),
    pytest.param(
        [Acao(tipo="remover_coluna", dados={"coluna": "Inexistente"}, resumo="x")],
        id="remover_coluna_inexistente",
    ),
    pytest.param(
        [Acao(tipo="renomear_coluna", dados={"coluna_atual": "Nome", "coluna_nova": "Cidade"}, resumo="x")],
        id="renomear_para_nome_ja_existente",
    ),
    pytest.param(
        [
            Acao(
                tipo="atualizar_em_massa",
                dados={
                    "coluna": "Nome",
                    "valor_novo": "x",
                    "condicao_coluna": "Cidade",
                    "condicao_operador": "quase_igual",
                    "condicao_valor": "BH",
                },
                resumo="x",
            )
        ],
        id="operador_de_condicao_desconhecido",
    ),
    pytest.param(
        [Acao(tipo="inserir_total", dados={"coluna": "Nome", "operacao": "soma"}, resumo="x")],
        id="soma_de_coluna_nao_numerica",
    ),
    pytest.param(
        [Acao(tipo="formatar_coluna", dados={"coluna": "Nome", "cor_fundo": "roxo"}, resumo="x")],
        id="cor_hexadecimal_invalida",
    ),
    pytest.param(
        [Acao(tipo="formatar_coluna", dados={"coluna": "Nome", "tamanho_fonte": 999}, resumo="x")],
        id="tamanho_de_fonte_fora_do_razoavel",
    ),
    pytest.param(
        [Acao(tipo="ajustar_largura_coluna", dados={"coluna": "Inexistente", "largura": 20}, resumo="x")],
        id="ajustar_largura_coluna_inexistente",
    ),
    pytest.param(
        [Acao(tipo="ajustar_largura_coluna", dados={"coluna": "Nome", "largura": 5000}, resumo="x")],
        id="ajustar_largura_coluna_fora_do_razoavel",
    ),
    pytest.param(
        [Acao(tipo="colorir_linhas_alternadas", dados={"cor_par": "roxo"}, resumo="x")],
        id="colorir_linhas_alternadas_cor_invalida",
    ),
    pytest.param(
        [Acao(tipo="adicionar_coluna_calculada", dados={"coluna": "Total", "expressao": "__import__('os')"}, resumo="x")],
        id="formula_com_codigo_malicioso",
    ),
    pytest.param(
        [Acao(tipo="apagar_tudo", dados={}, resumo="x")],
        id="tipo_de_acao_desconhecido",
    ),
    pytest.param(
        [Acao(tipo="atualizar_celula", dados={"coluna": "Nome"}, resumo="x")],
        id="dados_incompletos_faltando_campo_obrigatorio",
    ),
    pytest.param(
        [
            Acao(tipo="adicionar_coluna", dados={"coluna": "Status", "valor_padrao": "Novo"}, resumo="1a ação, válida"),
            Acao(tipo="remover_coluna", dados={"coluna": "NaoExiste"}, resumo="2a ação, inválida"),
        ],
        id="segunda_acao_de_um_plano_de_duas_falha",
    ),
]


@pytest.mark.parametrize("acoes", PLANOS_INVALIDOS)
def test_plano_invalido_nunca_quebra_e_nao_altera_a_planilha(manager, acoes):
    estado_antes = manager.dataframe.copy()

    with pytest.raises(SheetError):
        manager.aplicar_plano(acoes)

    assert manager.dataframe.equals(estado_antes)


@pytest.mark.parametrize("acoes", PLANOS_INVALIDOS)
def test_plano_invalido_na_previa_tambem_nunca_quebra(manager, acoes):
    estado_antes = manager.dataframe.copy()

    with pytest.raises(SheetError):
        manager.pre_visualizar_plano(acoes)

    assert manager.dataframe.equals(estado_antes)


def test_getattr_nao_permite_chamar_metodo_fora_da_lista_de_acoes(manager):
    """Dispatch por nome de método é perigoso se não for validado contra uma allowlist
    (a IA poderia, em tese, devolver tipo="salvar" ou tipo="_carregar")."""
    acoes = [Acao(tipo="salvar", dados={}, resumo="x")]
    with pytest.raises(SheetError):
        manager.aplicar_plano(acoes)
