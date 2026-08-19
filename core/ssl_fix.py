"""Corrige o erro comum no Windows "CERTIFICATE_VERIFY_FAILED: unable to get local
issuer certificate" ao falar com a Groq.

Causa típica: antivírus com inspeção SSL/TLS (AVG, Avast, Kaspersky, ESET) ou proxy
corporativo interceptando o HTTPS com um certificado raiz próprio. O Windows confia
nesse certificado, mas o parser X.509 estrito do OpenSSL usado pelo Python (mesmo com
o pacote certifi) rejeita. `truststore` resolve delegando a verificação para a API
nativa do sistema operacional (CryptoAPI no Windows), que já confia nesse certificado.
"""
import logging
import subprocess
import sys

import httpx

logger = logging.getLogger("assistente_planilhas")


def _instalar(pacote: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "--quiet", pacote],
            check=True,
            timeout=60,
        )
        return True
    except Exception:
        return False


def _cliente_com_truststore() -> httpx.Client | None:
    try:
        import ssl

        import truststore
    except ImportError:
        if not _instalar("truststore"):
            return None
        try:
            import ssl

            import truststore
        except ImportError:
            return None

    try:
        contexto = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return httpx.Client(verify=contexto)
    except Exception as exc:
        logger.warning("truststore falhou: %s", exc)
        return None


def _cliente_com_certifi() -> httpx.Client | None:
    try:
        import certifi
    except ImportError:
        if not _instalar("certifi"):
            return None
        try:
            import certifi
        except ImportError:
            return None

    try:
        return httpx.Client(verify=certifi.where())
    except Exception as exc:
        logger.warning("certifi falhou: %s", exc)
        return None


def criar_http_client() -> httpx.Client | None:
    """Devolve um httpx.Client com verificação de certificado robusta, ou None
    (nesse caso a Groq usa o comportamento padrão do httpx)."""
    return _cliente_com_truststore() or _cliente_com_certifi()
