"""Testa cada tipo de ação do SheetManager: caminho feliz e erro esperado."""
import pytest

from core.errors import SheetError


# -- adicionar_linha ---------------------------------------------------------


def test_adicionar_linha_funciona(manager):
    manager.adicionar_linha(Nome="Carlos", Cidade="Recife", Preco=5, Quantidade=1)
    assert manager.total_linhas == 4
    assert manager.dataframe.iloc[3]["Nome"] == "Carlos"


def test_adicionar_linha_coluna_inexistente_nao_aplica_nada(manager):
    with pytest.raises(SheetError):
        manager.adicionar_linha(ColunaFalsa="x")
    assert manager.total_linhas == 3


def test_pre_visualizar_plano_nao_escreve_no_arquivo_real(manager):
    from core.ai_parser import Acao

    manager.pre_visualizar_plano(
        [Acao(tipo="adicionar_linha", dados={"Nome": "Carlos"}, resumo="x")]
    )
    assert manager.total_linhas == 3


# -- atualizar_celula ---------------------------------------------------------


def test_atualizar_celula_funciona(manager):
    manager.atualizar_celula(linha=0, coluna="Nome", valor="Mariazinha")
    assert manager.dataframe.at[0, "Nome"] == "Mariazinha"


def test_atualizar_celula_coluna_inexistente(manager):
    with pytest.raises(SheetError):
        manager.atualizar_celula(linha=0, coluna="Inexistente", valor="x")


def test_atualizar_celula_linha_fora_do_intervalo(manager):
    with pytest.raises(SheetError):
        manager.atualizar_celula(linha=99, coluna="Nome", valor="x")


# -- remover_linha ---------------------------------------------------------


def test_remover_linha_funciona(manager):
    manager.remover_linha(linha=0)
    assert manager.total_linhas == 2
    assert manager.dataframe.iloc[0]["Nome"] == "João"


def test_remover_linha_fora_do_intervalo(manager):
    with pytest.raises(SheetError):
        manager.remover_linha(linha=99)


# -- adicionar_coluna ---------------------------------------------------------


def test_adicionar_coluna_funciona(manager):
    manager.adicionar_coluna(coluna="Status", valor_padrao="Pendente")
    assert "Status" in manager.columns
    assert (manager.dataframe["Status"] == "Pendente").all()


def test_adicionar_coluna_ja_existe(manager):
    with pytest.raises(SheetError):
        manager.adicionar_coluna(coluna="Nome")


# -- adicionar_coluna_calculada ---------------------------------------------------------


def test_adicionar_coluna_calculada_valores_calculados_na_previa(manager):
    detalhe = manager.adicionar_coluna_calculada(coluna="Total", expressao="Preco * Quantidade")
    assert detalhe["valores"] == [
        {"linha": 1, "valor": 20.0},
        {"linha": 2, "valor": 20.0},
        {"linha": 3, "valor": 90.0},
    ]
    # A célula em si vira uma fórmula (Preco=coluna C, Quantidade=coluna D); o Excel
    # recalcula o valor ao abrir o arquivo.
    assert manager.dataframe.at[0, "Total"] == "=(C2*D2)"


def test_adicionar_coluna_calculada_coluna_inexistente(manager):
    with pytest.raises(SheetError):
        manager.adicionar_coluna_calculada(coluna="Total", expressao="Preco * Inexistente")


def test_adicionar_coluna_calculada_sintaxe_nao_suportada(manager):
    with pytest.raises(SheetError):
        manager.adicionar_coluna_calculada(coluna="Total", expressao="__import__('os')")


# -- adicionar_coluna_sequencia ---------------------------------------------------------


def test_adicionar_coluna_sequencia_decrescente(manager):
    detalhe = manager.adicionar_coluna_sequencia(coluna="Idade", valor_inicial=50, incremento=-1)
    assert detalhe["valores"] == [
        {"linha": 1, "valor": 50},
        {"linha": 2, "valor": 49},
        {"linha": 3, "valor": 48},
    ]
    assert list(manager.dataframe["Idade"]) == [50, 49, 48]


def test_adicionar_coluna_sequencia_ja_existe(manager):
    with pytest.raises(SheetError):
        manager.adicionar_coluna_sequencia(coluna="Nome", valor_inicial=1, incremento=1)


def test_plano_encadeado_coluna_calculada_usa_coluna_criada_antes(manager):
    """Reproduz o pedido real que falhava: cria uma sequência de Idade e depois uma
    coluna calculada (Ano de Nascimento) baseada nela, no mesmo plano."""
    from core.ai_parser import Acao

    acoes = [
        Acao(
            tipo="adicionar_coluna_sequencia",
            dados={"coluna": "Idade", "valor_inicial": 50, "incremento": -1},
            resumo="cria Idade",
        ),
        Acao(
            tipo="adicionar_coluna_calculada",
            dados={"coluna": "AnoNascimento", "expressao": "2026 - Idade"},
            resumo="cria AnoNascimento a partir de Idade",
        ),
    ]

    detalhes_previa = manager.pre_visualizar_plano(acoes)
    assert detalhes_previa[1]["valores"] == [
        {"linha": 1, "valor": 1976.0},
        {"linha": 2, "valor": 1977.0},
        {"linha": 3, "valor": 1978.0},
    ]
    # A prévia não deve ter escrito nada de verdade ainda.
    assert "Idade" not in manager.columns

    manager.aplicar_plano(acoes)
    assert list(manager.dataframe["Idade"]) == [50, 49, 48]
    # Idade é a 5ª coluna (E) depois que Nome/Cidade/Preco/Quantidade já existiam.
    assert manager.dataframe.at[0, "AnoNascimento"] == "=(2026-E2)"


# -- remover_coluna ---------------------------------------------------------


def test_remover_coluna_funciona(manager):
    manager.remover_coluna(coluna="Cidade")
    assert "Cidade" not in manager.columns


def test_remover_coluna_inexistente(manager):
    with pytest.raises(SheetError):
        manager.remover_coluna(coluna="Inexistente")


# -- renomear_coluna ---------------------------------------------------------


def test_renomear_coluna_funciona(manager):
    manager.renomear_coluna(coluna_atual="Nome", coluna_nova="NomeCompleto")
    assert "NomeCompleto" in manager.columns
    assert "Nome" not in manager.columns


def test_renomear_coluna_para_nome_ja_existente(manager):
    with pytest.raises(SheetError):
        manager.renomear_coluna(coluna_atual="Nome", coluna_nova="Cidade")


# -- atualizar_em_massa ---------------------------------------------------------


def test_atualizar_em_massa_funciona(manager):
    detalhe = manager.atualizar_em_massa(
        coluna="Nome",
        valor_novo="Cliente BH",
        condicao_coluna="Cidade",
        condicao_operador="igual",
        condicao_valor="Belo Horizonte",
    )
    assert len(detalhe["linhas_afetadas"]) == 2
    assert manager.dataframe.at[0, "Nome"] == "Cliente BH"
    assert manager.dataframe.at[2, "Nome"] == "Cliente BH"
    assert manager.dataframe.at[1, "Nome"] == "João"


def test_atualizar_em_massa_operador_desconhecido(manager):
    with pytest.raises(SheetError):
        manager.atualizar_em_massa(
            coluna="Nome",
            valor_novo="x",
            condicao_coluna="Cidade",
            condicao_operador="parecido_com",
            condicao_valor="BH",
        )


def test_atualizar_em_massa_comparacao_numerica_invalida(manager):
    with pytest.raises(SheetError):
        manager.atualizar_em_massa(
            coluna="Nome",
            valor_novo="x",
            condicao_coluna="Nome",
            condicao_operador="maior_que",
            condicao_valor="10",
        )


# -- inserir_total ---------------------------------------------------------


def test_inserir_total_soma_funciona(manager):
    detalhe = manager.inserir_total(coluna="Preco", operacao="soma")
    assert detalhe["resultado"] == 60
    assert manager.total_linhas == 4


def test_inserir_total_operacao_desconhecida(manager):
    with pytest.raises(SheetError):
        manager.inserir_total(coluna="Preco", operacao="mediana")


def test_inserir_total_coluna_nao_numerica(manager):
    with pytest.raises(SheetError):
        manager.inserir_total(coluna="Nome", operacao="soma")


# -- formatar_coluna ---------------------------------------------------------


def test_formatar_coluna_funciona(manager):
    detalhe = manager.formatar_coluna(coluna="Nome", negrito=True, cor_fundo="FFCC00")
    assert detalhe["negrito"] is True


def test_formatar_coluna_cor_invalida(manager):
    with pytest.raises(SheetError):
        manager.formatar_coluna(coluna="Nome", cor_fundo="não é uma cor")


def test_formatar_coluna_sem_nenhum_estilo(manager):
    with pytest.raises(SheetError):
        manager.formatar_coluna(coluna="Nome")


def test_formatar_coluna_linha_fora_do_intervalo(manager):
    with pytest.raises(SheetError):
        manager.formatar_coluna(coluna="Nome", negrito=True, linhas=[99])


def test_formatar_coluna_incluir_cabecalho(manager):
    detalhe = manager.formatar_coluna(coluna="Nome", negrito=True, incluir_cabecalho=True)
    assert detalhe["incluir_cabecalho"] is True
    celula_cabecalho = manager.worksheet.cell(row=1, column=1)
    assert celula_cabecalho.font.bold is True


def test_formatar_coluna_tamanho_fonte_funciona(manager):
    detalhe = manager.formatar_coluna(coluna="Nome", tamanho_fonte=14)
    assert detalhe["tamanho_fonte"] == 14
    celula = manager.worksheet.cell(row=2, column=1)
    assert celula.font.size == 14


def test_formatar_coluna_tamanho_fonte_fora_do_razoavel(manager):
    with pytest.raises(SheetError):
        manager.formatar_coluna(coluna="Nome", tamanho_fonte=500)


# -- ajustar_largura_coluna ---------------------------------------------------------


def test_ajustar_largura_coluna_com_valor_explicito(manager):
    detalhe = manager.ajustar_largura_coluna(coluna="Nome", largura=30)
    assert detalhe["largura"] == 30
    assert manager.worksheet.column_dimensions["A"].width == 30


def test_ajustar_largura_coluna_automatica(manager):
    detalhe = manager.ajustar_largura_coluna(coluna="Nome")
    assert detalhe["largura"] > 0


def test_ajustar_largura_coluna_inexistente(manager):
    with pytest.raises(SheetError):
        manager.ajustar_largura_coluna(coluna="Inexistente", largura=20)


def test_ajustar_largura_coluna_fora_do_razoavel(manager):
    with pytest.raises(SheetError):
        manager.ajustar_largura_coluna(coluna="Nome", largura=1000)


# -- congelar_cabecalho ---------------------------------------------------------


def test_congelar_cabecalho_ativa(manager):
    detalhe = manager.congelar_cabecalho()
    assert detalhe["ativar"] is True
    assert manager.worksheet.freeze_panes == "A2"


def test_congelar_cabecalho_desativa(manager):
    manager.congelar_cabecalho()
    detalhe = manager.congelar_cabecalho(ativar=False)
    assert detalhe["ativar"] is False
    assert manager.worksheet.freeze_panes is None


# -- colorir_linhas_alternadas ---------------------------------------------------------


def test_colorir_linhas_alternadas_com_cores_padrao(manager):
    detalhe = manager.colorir_linhas_alternadas()
    assert detalhe["linhas_coloridas"] == 3
    primeira_linha = manager.worksheet.cell(row=2, column=1)
    segunda_linha = manager.worksheet.cell(row=3, column=1)
    assert primeira_linha.fill.start_color.rgb.endswith(detalhe["cor_par"])
    assert segunda_linha.fill.start_color.rgb.endswith(detalhe["cor_impar"])


def test_colorir_linhas_alternadas_com_cores_explicitas(manager):
    detalhe = manager.colorir_linhas_alternadas(cor_par="FFCC00", cor_impar="003366")
    assert detalhe["cor_par"] == "FFCC00"
    assert detalhe["cor_impar"] == "003366"


def test_colorir_linhas_alternadas_pinta_todas_as_colunas(manager):
    manager.colorir_linhas_alternadas(cor_par="FFCC00", cor_impar="003366")
    for numero_coluna in range(1, len(manager.columns) + 1):
        assert manager.worksheet.cell(row=2, column=numero_coluna).fill.start_color.rgb.endswith("FFCC00")


def test_colorir_linhas_alternadas_cor_invalida(manager):
    with pytest.raises(SheetError):
        manager.colorir_linhas_alternadas(cor_par="não é uma cor")


# -- aplicar_plano / salvar ---------------------------------------------------------


def test_aplicar_plano_com_varias_acoes(manager):
    from core.ai_parser import Acao

    acoes = [
        Acao(tipo="adicionar_coluna", dados={"coluna": "Status", "valor_padrao": "Novo"}, resumo="x"),
        Acao(tipo="atualizar_celula", dados={"linha": 0, "coluna": "Nome", "valor": "Mariazinha"}, resumo="y"),
    ]
    manager.aplicar_plano(acoes)
    assert "Status" in manager.columns
    assert manager.dataframe.at[0, "Nome"] == "Mariazinha"


def test_salvar_e_recarregar_preserva_dados(manager, tmp_path):
    manager.adicionar_linha(Nome="Carlos", Cidade="Recife", Preco=5, Quantidade=1)
    manager.salvar()

    from core.sheet_manager import SheetManager

    recarregado = SheetManager(manager.caminho)
    assert recarregado.total_linhas == 4
    assert recarregado.dataframe.iloc[3]["Nome"] == "Carlos"
