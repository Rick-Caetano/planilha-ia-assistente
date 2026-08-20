"""Instalação das dependências e criação do atalho para rodar o projeto."""

import json
import os
import shutil
import subprocess
import sys


class Install:
    def __init__(self):
        self.pasta_instalation = os.path.dirname(os.path.abspath(__file__))
        self.raiz_projeto = os.path.dirname(self.pasta_instalation)
        self.arquivo_dependencias = os.path.join(self.pasta_instalation, "dependencies.json")
        with open(self.arquivo_dependencias, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.python_version = data["py_version"]
        self.pip_version = data["pip_version"]
        self.libs = data["libs"]

    def instalar_dependencias(self):
        self._verificar_pip()

        for dependencia in self.libs:
            nome_import = _NOMES_IMPORT.get(dependencia.split("==")[0], dependencia.split("==")[0])
            try:
                __import__(nome_import)
            except ImportError:
                print(f"Dependência {dependencia} não encontrada. Instalando...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", dependencia])
                    print(f"Dependência {dependencia} instalada com sucesso!")
                except subprocess.CalledProcessError as erro:
                    print(f"Erro ao instalar a dependência {dependencia}: {erro}\n")
                    print(
                        "####################################################\n"
                        f"    Tente instalar manualmente com o comando:\n"
                        f"            pip install {dependencia}\n"
                        "####################################################"
                    )

    def _verificar_pip(self):
        try:
            import pip
            print(f"Pip instalado: {pip.__version__}")
        except ImportError:
            print("Pip não encontrado. Tentando ativá-lo...")
            try:
                subprocess.check_call([sys.executable, "-m", "ensurepip", "--default-pip"])
            except subprocess.CalledProcessError as erro:
                print(f"Erro ao ativar o pip: {erro}\nTentando instalar o pip manualmente...")
                import urllib.request

                try:
                    url = "https://bootstrap.pypa.io/get-pip.py"
                    urllib.request.urlretrieve(url, "get-pip.py")
                    subprocess.check_call([sys.executable, "get-pip.py"])
                    print("Pip instalado manualmente com sucesso!")
                except Exception as erro:
                    print(f"Falha crítica ao instalar o pip: {erro}")

    def preservar_icone(self) -> str | None:
        """Copia o ícone pra raiz do projeto, pra sobreviver depois que
        instalation/ for apagada no fim da instalação."""
        origem = os.path.join(self.pasta_instalation, "icon.ico")
        destino = os.path.join(self.raiz_projeto, "icon.ico")
        if not os.path.exists(origem):
            return None
        shutil.copyfile(origem, destino)
        return destino

    def criar_atalho(self, caminho_icone: str | None):
        """Cria o atalho na Área de Trabalho apontando pro AbrirAssistente.bat,
        via VBScript (sem depender de pywin32)."""
        if os.name != "nt":
            print("Criação de atalho não suportada neste sistema operacional.")
            return

        alvo = os.path.join(self.raiz_projeto, "AbrirAssistente.bat")
        if not os.path.exists(alvo):
            print(f"AbrirAssistente.bat não encontrado em {alvo}. Atalho não foi criado.")
            return

        atalho = os.path.join(os.path.expanduser("~"), "Desktop", "AssistentePlanilhasIA.lnk")
        linha_icone = f'oLink.IconLocation = "{caminho_icone}"' if caminho_icone else ""

        vbs = f"""Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{atalho}")
oLink.TargetPath = "{alvo}"
oLink.WorkingDirectory = "{self.raiz_projeto}"
oLink.Description = "Assistente de Planilhas com IA"
{linha_icone}
oLink.Save
"""
        vbs_temp = os.path.join(self.pasta_instalation, "_criar_atalho.vbs")
        with open(vbs_temp, "w", encoding="utf-8") as f:
            f.write(vbs)

        try:
            subprocess.check_call(["cscript", "//nologo", vbs_temp])
            print(f"Atalho criado na área de trabalho: {atalho}")
        except subprocess.CalledProcessError as erro:
            print(f"Erro ao criar o atalho: {erro}")
        finally:
            os.remove(vbs_temp)


_NOMES_IMPORT = {
    "python-dotenv": "dotenv",
}


if __name__ == "__main__":
    instalador = Install()
    instalador.instalar_dependencias()
    icone = instalador.preservar_icone()
    instalador.criar_atalho(icone)
    print("\nInstalação concluída.")
