"""Helpers de interface: ícone local (SVG) embutido como HTML, sem depender de emoji."""
import base64
from pathlib import Path

import streamlit as st

# st.dialog e o parâmetro `icon` em botões/alertas só existem em versões recentes do
# Streamlit. Máquinas com mais de uma instalação de Python podem acabar rodando uma
# versão antiga (ver core/config_manager.py), então todo uso desses recursos passa por
# essa checagem para nunca derrubar o app com um TypeError/AttributeError.
STREAMLIT_MODERNO = hasattr(st, "dialog")


def icone_html(caminho: Path, tamanho: int = 28) -> str:
    dados = base64.b64encode(caminho.read_bytes()).decode("utf-8")
    return (
        f'<img src="data:image/svg+xml;base64,{dados}" width="{tamanho}" '
        f'style="vertical-align:middle;margin-right:8px;">'
    )


def kw_icone(nome_icone: str) -> dict:
    """`icon=nome_icone` só se a versão instalada do Streamlit suportar, senão {}."""
    return {"icon": nome_icone} if STREAMLIT_MODERNO else {}
