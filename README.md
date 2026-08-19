# 📊 Assistente de Planilhas com IA

Um app web simples que deixa uma pessoa **sem conhecimento técnico** editar uma
planilha `.xlsx` descrevendo o que quer em português comum — em vez de mexer
direto nas células.

> "adiciona um cliente chamado Maria Souza, telefone 31999998888, status pendente"

O texto vira uma ação estruturada (adicionar linha / atualizar célula / remover
linha), o app mostra uma **prévia** antes de gravar qualquer coisa, e só aplica
a mudança depois de confirmação manual.

## Por que existe

Em ambiente industrial é comum controle de estoque, chamados e cadastros
ficarem em planilhas operadas por gente que não programa. Esse projeto nasceu
de experiência real com esse tipo de situação: em vez de treinar cada pessoa a
usar fórmulas ou uma interface de sistema, a interface passa a ser a própria
linguagem natural.

## Como funciona

1. **Streamlit** renderiza a planilha atual e recebe o pedido em texto livre.
2. O pedido + os nomes reais das colunas da planilha são enviados pra
   **Groq API** (modelo Llama 3.3, gratuito), que responde só com um JSON
   estruturado (`{"tipo": ..., "dados": ...}`).
3. `componentes/core/sheet_manager.py` valida a ação contra as colunas e o
   número de linhas reais do arquivo antes de aplicar — se a IA "alucinar"
   uma coluna que não existe ou uma linha fora do intervalo, a ação é
   rejeitada com uma mensagem clara em vez de corromper o arquivo.
4. Só depois de o usuário clicar em **Aplicar** a planilha é regravada.

## Estrutura do projeto

```
Instalar.bat            <- instalador Windows (ver seção abaixo)
build_release.bat        <- empacota tudo num .zip pra Release do GitHub
requirements.txt
instalation/              <- lógica de instalação de dependências + atalho
  install.py
  dependencies.json
  icon.ico
componentes/              <- código do app em si (sempre fica aqui,
  app.py                     tanto no repositório quanto no pacote instalado)
  core/
  data/
  .env.example
```

## Rodando localmente (dev)

```bash
pip install -r requirements.txt
cp componentes/.env.example componentes/.env   # coloque sua GROQ_API_KEY (gratuita em console.groq.com)
streamlit run componentes/app.py
```

O app já sobe com uma planilha de exemplo (`componentes/data/planilha_exemplo.xlsx`,
dados fictícios) — ou envie a sua própria pela barra lateral.

## Instalação para quem não é técnico (Windows)

Quem for só usar o app (sem editar código) não precisa instalar Python nem
mexer em terminal — a Release do GitHub traz um `Instalar.bat` que:

1. Detecta se já existe Python instalado; se não existir, baixa e instala o
   Python 3.11 oficial silenciosamente.
2. Instala as dependências do projeto (`instalation/dependencies.json`).
3. Cria um atalho **AssistentePlanilhasIA** na Área de Trabalho, que abre o
   app com `streamlit run componentes/app.py`.

Basta baixar o `.zip` da Release, extrair, e dar duplo clique em
`Instalar.bat`.

### Gerando uma nova Release (dev)

```bat
build_release.bat
```

Isso empacota `Instalar.bat`, `instalation/` e `componentes/` (a mesma
estrutura do repositório) em `dist/AssistentePlanilhasIA.zip`, pronto pra
anexar numa Release do GitHub.

## Stack

- Python 3.11+
- Streamlit (interface)
- pandas + openpyxl (leitura/escrita do `.xlsx`)
- Groq API (interpretação de linguagem natural, saída em JSON estruturado)

## Limitações conhecidas

- Uma ação por instrução (não interpreta "faz isso e mais aquilo" numa frase
  só).
- Funciona com uma aba por vez.
- A IA só pode agir sobre colunas que já existem na planilha — criar coluna
  nova precisa ser feito manualmente, por segurança.
