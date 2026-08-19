"""Assistente de planilhas por linguagem natural de IA

Interface Streamlit que deixa uma pessoa sem conhecimento técnico descrever o que quer mudar numa planilha (adicionar cliente, atualizar
status, remover linha) e aplica a ação de forma segura, sempre mostrando uma
prévia antes de gravar no arquivo.
"""
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from core.ai_parser import InterpretacaoError, interpretar
from core.sheet_manager import SheetError, SheetManager

load_dotenv(Path(__file__).parent / ".env")

PLANILHA_EXEMPLO = Path(__file__).parent / "data" / "planilha_exemplo.xlsx"

st.set_page_config(page_title="Assistente de Planilhas com IA", page_icon="📊", layout="centered")
st.title("📊 Assistente de Planilhas com IA")
st.caption(
    "Descreva em português o que você quer mudar na planilha. "
    "A IA interpreta o pedido, mostra uma prévia e só aplica depois da sua confirmação."
)

with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input(
        "Groq API key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Gratuita em console.groq.com. Também pode ser definida em .env como GROQ_API_KEY.",
    )
    arquivo = st.file_uploader("Planilha (.xlsx)", type=["xlsx"])
    st.divider()
    if "historico" not in st.session_state:
        st.session_state.historico = []
    if st.session_state.historico:
        st.subheader("Histórico desta sessão")
        for item in reversed(st.session_state.historico):
            st.write(f"✅ {item}")

if "manager" not in st.session_state or st.session_state.get("_arquivo_nome") != (
    arquivo.name if arquivo else "exemplo"
):
    origem = arquivo if arquivo else PLANILHA_EXEMPLO
    st.session_state.manager = SheetManager(origem)
    st.session_state._arquivo_nome = arquivo.name if arquivo else "exemplo"

manager: SheetManager = st.session_state.manager

st.subheader("Planilha atual")
st.dataframe(manager.dataframe, use_container_width=True)

st.subheader("O que você quer fazer?")
instrucao = st.text_area(
    "Descreva o pedido",
    placeholder="Ex.: adiciona um cliente chamado Maria Souza, telefone 31999998888, status pendente",
    height=80,
)

col1, col2 = st.columns(2)
interpretar_clicado = col1.button("Interpretar pedido", type="primary", disabled=not instrucao or not api_key)
if not api_key:
    col1.caption("Informe a Groq API key na barra lateral.")

if interpretar_clicado:
    try:
        acao = interpretar(
            instrucao=instrucao,
            colunas=manager.columns,
            amostra=manager.ver_linhas(),
            api_key=api_key,
        )
        st.session_state.acao_pendente = acao
    except InterpretacaoError as exc:
        st.session_state.acao_pendente = None
        st.error(f"Não consegui interpretar o pedido: {exc}")

acao = st.session_state.get("acao_pendente")
if acao:
    st.info(f"**Prévia da ação:** {acao.resumo}")
    st.json({"tipo": acao.tipo, "dados": acao.dados})

    if st.button("Aplicar na planilha"):
        try:
            if acao.tipo == "adicionar_linha":
                manager.adicionar_linha(acao.dados)
            elif acao.tipo == "atualizar_celula":
                manager.atualizar_celula(**acao.dados)
            elif acao.tipo == "remover_linha":
                manager.remover_linha(**acao.dados)

            manager.salvar()
            st.session_state.historico.append(acao.resumo)
            st.session_state.acao_pendente = None
            st.success("Alteração aplicada e salva na planilha.")
            st.rerun()
        except SheetError as exc:
            st.error(f"Não foi possível aplicar: {exc}")

st.divider()
with open(manager.caminho, "rb") as f:
    st.download_button(
        "⬇️ Baixar planilha atualizada",
        data=f,
        file_name=manager.caminho.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
