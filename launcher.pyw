"""Launcher sem janela: sobe o Streamlit em segundo plano, abre o navegador na
página do app e encerra o servidor sozinho quando o navegador é fechado.

Roda via pythonw.exe (sem console), chamado por AbrirAssistente.bat. Fica na
raiz do projeto de propósito: precisa sobreviver à instalação e continuar
disponível pra recriar um atalho novo a qualquer momento.
"""
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJETO = Path(__file__).resolve().parent
LOG_DIR = PROJETO / "logs"
LOG_DIR.mkdir(exist_ok=True)

INTERVALO_MONITOR = 3  # segundos entre checagens de conexão ativa
TOLERANCIA_DESCONEXAO = 3  # checagens seguidas sem conexão antes de encerrar o servidor
TIMEOUT_PRIMEIRA_CONEXAO = 60  # segundos esperando o navegador abrir a página pela 1ª vez


def porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar_servidor(porta: int, tentativas: int = 60, intervalo: float = 0.25) -> bool:
    for _ in range(tentativas):
        try:
            with socket.create_connection(("127.0.0.1", porta), timeout=0.3):
                return True
        except OSError:
            time.sleep(intervalo)
    return False


def tem_conexao_ativa(porta: int) -> bool:
    try:
        import psutil
    except ImportError:
        return True  # sem psutil, nunca encerra sozinho: melhor que matar o servidor à toa

    for conexao in psutil.net_connections(kind="tcp"):
        if (
            conexao.laddr
            and conexao.laddr.port == porta
            and conexao.status == psutil.CONN_ESTABLISHED
        ):
            return True
    return False


def main() -> None:
    porta = porta_livre()
    log_path = LOG_DIR / "streamlit_servidor.log"

    with open(log_path, "a", encoding="utf-8") as log_arquivo:
        processo = subprocess.Popen(
            [
                sys.executable,
                "-m", "streamlit", "run", str(PROJETO / "app.py"),
                "--server.port", str(porta),
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=str(PROJETO),
            stdout=log_arquivo,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        try:
            if not esperar_servidor(porta):
                return

            webbrowser.open(f"http://127.0.0.1:{porta}")

            conectou_alguma_vez = False
            desconectado_desde = time.monotonic()
            inicio = time.monotonic()

            while processo.poll() is None:
                time.sleep(INTERVALO_MONITOR)
                ativo = tem_conexao_ativa(porta)

                if ativo:
                    conectou_alguma_vez = True
                    desconectado_desde = time.monotonic()
                elif conectou_alguma_vez:
                    if time.monotonic() - desconectado_desde > INTERVALO_MONITOR * TOLERANCIA_DESCONEXAO:
                        break
                elif time.monotonic() - inicio > TIMEOUT_PRIMEIRA_CONEXAO:
                    break
        finally:
            if processo.poll() is None:
                processo.terminate()
                try:
                    processo.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    processo.kill()


if __name__ == "__main__":
    main()
