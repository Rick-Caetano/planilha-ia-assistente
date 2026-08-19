"""Log de erros em arquivo, para diagnóstico posterior sem depender do usuário copiar o erro."""
import logging
import platform
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "erros.log"

logger = logging.getLogger("assistente_planilhas")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)


def registrar_inicio() -> None:
    try:
        import streamlit
        versao_streamlit = streamlit.__version__
    except Exception:
        versao_streamlit = "desconhecida"

    logger.info(
        "Início do app | Python %s | Streamlit %s | %s",
        sys.version.split()[0],
        versao_streamlit,
        platform.platform(),
    )
