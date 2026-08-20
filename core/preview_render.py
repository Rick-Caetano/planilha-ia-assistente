"""Desenha o detalhe de cada ação do plano em linguagem simples, sem JSON cru."""
import pandas as pd
import streamlit as st


def renderizar_detalhe(tipo: str, detalhe: dict) -> None:
    if tipo == "adicionar_linha":
        st.write("Nova linha:")
        st.table(pd.DataFrame([detalhe["valores"]]))

    elif tipo == "atualizar_celula":
        st.write(
            f"Linha {detalhe['linha']}, coluna **{detalhe['coluna']}**: "
            f"`{detalhe['valor_antigo']}` → `{detalhe['valor_novo']}`"
        )

    elif tipo == "remover_linha":
        st.write(f"Linha {detalhe['linha']} removida:")
        st.table(pd.DataFrame([detalhe["valores_removidos"]]))

    elif tipo == "adicionar_coluna":
        st.write(
            f"Coluna **{detalhe['coluna']}** criada com valor `{detalhe['valor_padrao']}` "
            f"em {detalhe['linhas_preenchidas']} linha(s)."
        )

    elif tipo == "adicionar_coluna_calculada":
        st.write(f"Coluna **{detalhe['coluna']}** = `{detalhe['expressao']}`:")
        st.table(pd.DataFrame(detalhe["valores"]).rename(columns={"linha": "Linha", "valor": "Valor calculado"}))

    elif tipo == "adicionar_coluna_sequencia":
        st.write(
            f"Coluna **{detalhe['coluna']}** = sequência começando em `{detalhe['valor_inicial']}`, "
            f"passo `{detalhe['incremento']}` por linha:"
        )
        st.table(pd.DataFrame(detalhe["valores"]).rename(columns={"linha": "Linha", "valor": "Valor"}))

    elif tipo == "remover_coluna":
        st.write(f"Coluna **{detalhe['coluna']}** removida.")

    elif tipo == "renomear_coluna":
        st.write(f"Coluna **{detalhe['de']}** renomeada para **{detalhe['para']}**.")

    elif tipo == "atualizar_em_massa":
        st.write(f"Condição: {detalhe['condicao']} → {detalhe['coluna']} = `{detalhe['valor_novo']}`")
        if detalhe["linhas_afetadas"]:
            tabela = pd.DataFrame(detalhe["linhas_afetadas"]).rename(
                columns={"linha": "Linha", "valor_antigo": "Valor antigo"}
            )
            tabela["Valor novo"] = detalhe["valor_novo"]
            st.table(tabela)
        else:
            st.write("Nenhuma linha bateu com essa condição.")

    elif tipo == "inserir_total":
        st.write(
            f"{detalhe['operacao'].capitalize()} da coluna **{detalhe['coluna']}**: "
            f"`{detalhe['resultado']}` (linha de total adicionada no fim da planilha)."
        )

    elif tipo == "formatar_coluna":
        estilos = [
            nome
            for nome, valor in [
                ("negrito", detalhe.get("negrito")),
                ("itálico", detalhe.get("italico")),
                (f"cor de fundo {detalhe.get('cor_fundo')}", detalhe.get("cor_fundo")),
                (f"cor de texto {detalhe.get('cor_texto')}", detalhe.get("cor_texto")),
                (f"formato {detalhe.get('formato_numero')}", detalhe.get("formato_numero")),
                (f"tamanho da fonte {detalhe.get('tamanho_fonte')}", detalhe.get("tamanho_fonte")),
            ]
            if valor
        ]
        alvo = "todas as linhas" if detalhe["linhas"] == "todas" else f"linha(s) {detalhe['linhas']}"
        if detalhe.get("incluir_cabecalho"):
            alvo += " + cabeçalho"
        st.write(f"Coluna **{detalhe['coluna']}** ({alvo}): {', '.join(estilos)}.")

    elif tipo == "ajustar_largura_coluna":
        st.write(f"Coluna **{detalhe['coluna']}** ajustada para {detalhe['largura']} caracteres de largura.")

    elif tipo == "congelar_cabecalho":
        acao = "travado no topo" if detalhe["ativar"] else "destravado"
        st.write(f"Cabeçalho da planilha {acao} ao rolar a tela.")

    elif tipo == "colorir_linhas_alternadas":
        st.write(
            f"Linhas coloridas alternando **{detalhe['cor_par']}** e **{detalhe['cor_impar']}** "
            f"em {detalhe['linhas_coloridas']} linha(s) de dados."
        )

    else:
        st.write("Alteração aplicada.")
