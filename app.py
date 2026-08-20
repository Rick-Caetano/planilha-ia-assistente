"""Assistente de planilhas por linguagem natural de IA

Interface Streamlit que deixa uma pessoa sem conhecimento técnico descrever o que quer mudar numa planilha (adicionar cliente, atualizar
status, remover linha) e aplica a ação de forma segura, sempre mostrando uma
prévia antes de gravar no arquivo.
"""
import traceback
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from core.ai_parser import InterpretacaoError, interpretar
from core.config_manager import carregar_config, salvar_api_key
from core.errors import SheetError
from core.logger import logger, registrar_inicio
from core.preview_render import renderizar_detalhe
from core.sheet_manager import SheetManager
from core.sugestoes_manager import carregar_sugestoes
from core.ui_helpers import STREAMLIT_MODERNO, icone_html, kw_icone

registrar_inicio()

load_dotenv(Path(__file__).parent / ".env")

PLANILHA_EXEMPLO = Path(__file__).parent / "data" / "planilha_exemplo.xlsx"
VIDEO_TUTORIAL = Path(__file__).parent / "assets" / "video" / "Criar chave API grok.mp4"
GROQ_CONSOLE_URL = "https://console.groq.com/home"

ICONS = Path(__file__).parent / "assets" / "icons"
ICONE_TABELA = ICONS / "tabela.svg"

st.set_page_config(
    page_title="Assistente de Planilhas com IA",
    page_icon=":material/table_view:" if STREAMLIT_MODERNO else None,
    layout="centered",
)

config = carregar_config()


def mostrar_detalhes_erro(detalhes: str) -> None:
    if STREAMLIT_MODERNO:
        @st.dialog("Detalhes técnicos do erro")
        def _abrir_modal() -> None:
            st.code(detalhes, language="text")

        _abrir_modal()
    else:
        with st.expander("Detalhes técnicos do erro"):
            st.code(detalhes, language="text")


def tratar_erro(mensagem: str, exc: Exception) -> None:
    origem = exc.__cause__ or exc
    detalhes = "".join(traceback.format_exception(type(origem), origem, origem.__traceback__))
    logger.error("%s\n%s", mensagem, detalhes)

    st.error(mensagem, **kw_icone(":material/error:"))
    if config.get("desenvolver"):
        mostrar_detalhes_erro(detalhes)


if config["primeiro_uso"] or not config["groq_api_key"]:
    st.markdown(
        f'<h1>{icone_html(ICONE_TABELA, 40)}Bem-vindo ao Assistente de Planilhas com IA</h1>',
        unsafe_allow_html=True,
    )
    st.write(
        "Antes de começar, você precisa de uma chave gratuita da Groq, é quem "
        "roda a IA que entende seus pedidos. Assista o vídeo abaixo, é rápido:"
    )
    if VIDEO_TUTORIAL.exists():
        st.video(str(VIDEO_TUTORIAL))
    st.link_button(
        "Crie sua chave API grátis. Não demora 2 minutos, assista o vídeo",
        GROQ_CONSOLE_URL,
        type="primary",
        **kw_icone(":material/key:"),
    )
    st.write("Depois de criar, cole a chave aqui:")
    chave_digitada = st.text_input("Groq API key", type="password", placeholder="gsk_...")
    if st.button(
        "Salvar e começar a usar",
        type="primary",
        disabled=not chave_digitada,
        **kw_icone(":material/rocket_launch:"),
    ):
        salvar_api_key(chave_digitada)
        st.rerun()
    st.stop()

st.markdown(
    f'<h1>{icone_html(ICONE_TABELA, 40)}Assistente de Planilhas com IA</h1>',
    unsafe_allow_html=True,
)
st.caption(
    "Descreva em português o que você quer mudar na planilha. "
    "A IA interpreta o pedido, mostra uma prévia e só aplica depois da sua confirmação."
)

with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input(
        "Groq API key",
        value=config["groq_api_key"],
        type="password",
        help="Gratuita em console.groq.com.",
    )
    if api_key != config["groq_api_key"]:
        salvar_api_key(api_key)
    arquivo = st.file_uploader("Planilha (.xlsx)", type=["xlsx"])
    st.divider()
    if "historico" not in st.session_state:
        st.session_state.historico = []
    if st.session_state.historico:
        st.subheader("Histórico desta sessão")
        for item in reversed(st.session_state.historico):
            st.success(item, **kw_icone(":material/check_circle:"))

if "manager" not in st.session_state or st.session_state.get("_arquivo_nome") != (
    arquivo.name if arquivo else "exemplo"
):
    origem = arquivo if arquivo else PLANILHA_EXEMPLO
    try:
        st.session_state.manager = SheetManager(origem)
        st.session_state._arquivo_nome = arquivo.name if arquivo else "exemplo"
        st.session_state.plano_pendente = None
    except Exception as exc:
        tratar_erro("Não foi possível abrir essa planilha. Confira se o arquivo .xlsx não está corrompido.", exc)
        st.stop()

manager: SheetManager = st.session_state.manager

st.subheader("Planilha atual")
st.dataframe(manager.dataframe, **({"width": "stretch"} if STREAMLIT_MODERNO else {"use_container_width": True}))

st.subheader("O que você quer fazer?")

sugestoes = carregar_sugestoes()
if sugestoes:
    st.caption("Não sabe por onde começar? Clique numa sugestão e ajuste como quiser:")
    colunas_sugestao = st.columns(3)
    for indice, sugestao in enumerate(sugestoes):
        if colunas_sugestao[indice % 3].button(
            sugestao["rotulo"], key=f"sugestao_{indice}", **({"width": "stretch"} if STREAMLIT_MODERNO else {"use_container_width": True})
        ):
            st.session_state.instrucao_texto = sugestao["texto"]

instrucao = st.text_area(
    "Descreva o pedido",
    placeholder="Ex.: adiciona um cliente chamado Maria Souza, telefone 31999998888, status pendente",
    height=80,
    key="instrucao_texto",
)

col1, col2 = st.columns(2)
interpretar_clicado = col1.button(
    "Interpretar pedido", type="primary", **kw_icone(":material/auto_awesome:")
)

if interpretar_clicado:
    if not instrucao.strip():
        st.warning("Digite um pedido antes de interpretar.", **kw_icone(":material/info:"))
    else:
        try:
            plano = interpretar(
                instrucao=instrucao,
                colunas=manager.columns,
                amostra=manager.ver_linhas(),
                total_linhas=manager.total_linhas,
                api_key=api_key,
            )
            # Roda o plano de verdade numa cópia descartável do workbook, só para
            # validar e montar os detalhes da prévia. O arquivo real não é tocado.
            detalhes = manager.pre_visualizar_plano(plano.acoes)
            st.session_state.plano_pendente = plano
            st.session_state.detalhes_pendentes = detalhes
        except InterpretacaoError as exc:
            st.session_state.plano_pendente = None
            tratar_erro(f"Não consegui interpretar o pedido: {exc}", exc)
        except SheetError as exc:
            st.session_state.plano_pendente = None
            tratar_erro(f"A IA sugeriu algo que não dá pra aplicar: {exc}", exc)
        except Exception as exc:
            st.session_state.plano_pendente = None
            tratar_erro("Ocorreu um erro inesperado ao falar com a IA.", exc)

plano = st.session_state.get("plano_pendente")
if plano:
    st.write("Veja o que vai acontecer:")
    for item in plano.acoes:
        st.write(f"- {item.resumo}")

    with st.expander("Ver todas as alterações em detalhe"):
        for item, detalhe in zip(plano.acoes, st.session_state.detalhes_pendentes):
            st.markdown(f"**{item.resumo}**")
            renderizar_detalhe(item.tipo, detalhe)
            st.divider()

    if st.button("Aplicar na planilha", **kw_icone(":material/save:")):
        try:
            manager.aplicar_plano(plano.acoes)
            manager.salvar()
            for item in plano.acoes:
                st.session_state.historico.append(item.resumo)
            st.session_state.plano_pendente = None
            st.success("Alteração aplicada e salva na planilha.", **kw_icone(":material/check_circle:"))
            st.rerun()
        except SheetError as exc:
            tratar_erro(f"Não foi possível aplicar: {exc}", exc)
        except Exception as exc:
            tratar_erro("Ocorreu um erro inesperado ao salvar a planilha.", exc)

st.divider()
try:
    with open(manager.caminho, "rb") as f:
        st.download_button(
            "Baixar planilha atualizada",
            data=f,
            file_name=manager.caminho.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            **kw_icone(":material/download:"),
        )
except Exception as exc:
    tratar_erro("Não foi possível preparar o download da planilha.", exc)
