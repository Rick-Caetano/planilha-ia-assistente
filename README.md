# Assistente de Planilhas com IA

Um app web simples que deixa uma pessoa **sem conhecimento técnico** editar uma
planilha `.xlsx` descrevendo o que quer em português comum, em vez de mexer
direto nas células.

> "adiciona um cliente chamado Maria Souza, telefone 31999998888, status pendente"

O texto vira um **plano de uma ou mais ações estruturadas** (adicionar/remover linha,
atualizar célula, criar/remover/renomear coluna, coluna calculada com fórmula, alteração
em massa por condição, linha de totais, formatação), o app mostra uma **prévia em
linguagem simples** antes de gravar qualquer coisa (resumo sempre visível, detalhe linha a
linha só ao abrir "Ver detalhes"), e só aplica a mudança depois de confirmação manual.

## Por que existe

Em ambiente industrial é comum controle de estoque, chamados e cadastros
ficarem em planilhas operadas por gente que não programa. Esse projeto nasceu
de experiência real com esse tipo de situação: em vez de treinar cada pessoa a
usar fórmulas ou uma interface de sistema, a interface passa a ser a própria
linguagem natural.

## Como funciona

1. **Streamlit** renderiza a planilha atual e recebe o pedido em texto livre.
2. O pedido + os nomes reais das colunas da planilha são enviados pra
   **Groq API** (modelo `openai/gpt-oss-120b`, gratuito), que responde só com
   um JSON estruturado com uma lista de ações (`{"acoes": [{"tipo": ..., "dados": ...}, ...]}`).
   Uma instrução pode virar mais de uma ação (ex.: "cria a coluna Total e preenche com
   Preço vezes Quantidade").
3. `core/sheet_manager.py` valida cada ação contra as colunas e o número de linhas reais do
   arquivo antes de aplicar (contra um vocabulário fixo de 14 tipos de ação, nunca executa
   texto livre da IA como código). Se a IA "alucinar" uma coluna que não existe, uma linha
   fora do intervalo, ou uma fórmula com sintaxe estranha, o plano inteiro é rejeitado com
   uma mensagem clara em vez de corromper o arquivo ou aplicar parte do pedido. Ações do
   mesmo plano são aplicadas em ordem e podem se referenciar (ex.: uma coluna calculada pode
   usar uma coluna que uma ação anterior no mesmo plano acabou de criar). A prévia roda o
   plano de verdade numa cópia descartável do arquivo antes de mostrar qualquer coisa, então
   o que aparece na tela é exatamente o que vai ser gravado.
4. A prévia mostra o resumo de cada ação em português simples; o detalhe linha a linha
   (valor antigo/novo, linhas afetadas) fica dentro de um "Ver detalhes" fechado por
   padrão, nunca como JSON cru.
5. Só depois de o usuário clicar em **Aplicar** a planilha é regravada. O arquivo é lido e
   escrito direto via `openpyxl` (não por um round-trip de DataFrame), preservando
   formatação e fórmulas que já existiam no restante do arquivo.

### Ações suportadas

`adicionar_linha`, `atualizar_celula`, `remover_linha`, `adicionar_coluna`,
`adicionar_coluna_calculada` (fórmula simples entre colunas, ex.: `Preço * Quantidade`),
`adicionar_coluna_sequencia` (sequência numérica por linha, ex.: idade começando em 50 e
diminuindo 1 a cada linha), `remover_coluna`, `renomear_coluna`, `atualizar_em_massa` (muda
uma coluna em todas as linhas que batem uma condição), `inserir_total`
(soma/média/contagem/máximo/mínimo no fim da planilha), `formatar_coluna` (negrito,
itálico, cor, formato de número, tamanho da fonte, e opcionalmente o cabeçalho da coluna
junto com as linhas de dados), `ajustar_largura_coluna` (largura em número de caracteres,
ou automática pelo conteúdo mais longo), `congelar_cabecalho` (trava a primeira linha no
topo ao rolar a planilha) e `colorir_linhas_alternadas` (efeito zebrado: pinta o fundo de
todas as colunas alternando cor a cada linha de dados, sem depender da IA saber o total de
linhas).

## Estrutura do projeto

```
app.py                    <- app Streamlit
core/                      <- lógica (IA, planilha, fórmulas, prévia, config, logs, SSL)
tests/                      <- bateria pytest (ver "Rodando os testes")
data/                       planilha de exemplo
assets/                      ícones e vídeo tutorial
AbrirAssistente.bat        <- "executável" do dia a dia (sem janela preta)
launcher.pyw                sobe o servidor e encerra sozinho ao fechar o navegador
requirements.txt            dependências de produção (o instalador usa isso)
requirements-dev.txt        dependências só de desenvolvimento (pytest)
config.json                <- criado no primeiro uso (chave da Groq, preferências)

instalation/                <- só existe no repositório e no pacote recém-baixado;
  Instalar.bat                 o Instalar.bat se apaga sozinho no fim da instalação
  install.py
  dependencies.json
  icon.ico
  build_release.bat          (não vai pro pacote final, só gera ele)
```

## Rodando localmente (dev)

```bash
pip install -r requirements.txt
cp .env.example .env   # coloque sua GROQ_API_KEY (gratuita em console.groq.com)
streamlit run app.py
```

### Rodando os testes

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

A bateria cobre cada tipo de ação (caminho feliz + erro esperado), a mini-linguagem de
fórmulas (`core/formula_utils.py`), o parsing da resposta da IA com o cliente Groq mockado
(sem gastar cota real), e um conjunto de planos "adversários" (coluna inventada, fórmula
com código malicioso, tipo de ação desconhecido, plano com 2 ações onde a 2ª falha) que
precisam sempre virar um erro amigável e nunca alterar a planilha.

O app já sobe com uma planilha de exemplo (`data/planilha_exemplo.xlsx`,
dados fictícios), ou envie a sua própria pela barra lateral. Em vez do `.env`,
também dá pra colar a chave direto na tela de primeiro uso do app (ela fica
salva em `config.json`).

## Instalação para quem não é técnico (Windows)

Quem for só usar o app (sem editar código) não precisa instalar Python nem
mexer em terminal. A Release do GitHub traz um `Instalar.bat` que:

1. Detecta se já existe Python instalado; se não existir, baixa e instala o
   Python 3.11 oficial silenciosamente.
2. Instala as dependências do projeto (`instalation/dependencies.json`).
3. Cria o atalho **AssistentePlanilhasIA** na Área de Trabalho, apontando pra
   `AbrirAssistente.bat` (abre o app sem mostrar janela de terminal, e fecha o
   servidor sozinho quando o navegador é fechado).
4. Apaga `Instalar.bat` e a pasta `instalation/` (já cumpriram a função),
   deixando a pasta limpa pro dia a dia.

Basta baixar o `.zip` da Release, extrair, e dar duplo clique em
`Instalar.bat`. Se algum dia apagar o atalho da Área de Trabalho sem querer,
não precisa rodar o instalador de novo: `AbrirAssistente.bat` continua na
pasta do app, é só criar um atalho novo apontando pra ele.

### Gerando uma nova Release (dev)

```bat
instalation\build_release.bat
```

Isso empacota `app.py`, `core/`, `data/`, `assets/`, `AbrirAssistente.bat`,
`launcher.pyw`, `requirements.txt` e o conteúdo de `instalation/` em
`dist/AssistentePlanilhasIA.zip`, pronto pra anexar numa Release do GitHub.
Nunca inclui `.env`, `config.json` ou `logs/` (segredos e estado local do
dev).

## Stack

- Python 3.11+
- Streamlit (interface)
- pandas + openpyxl (leitura/escrita do `.xlsx`)
- Groq API (interpretação de linguagem natural, saída em JSON estruturado)
- truststore / certifi (evita erro de certificado SSL em máquinas com
  antivírus/proxy interceptando HTTPS)
- psutil (o launcher usa pra saber quando o navegador foi fechado)

## Limitações conhecidas

- Funciona com uma aba por vez.
- Fórmulas ficam como texto na tabela em tela até o arquivo ser aberto no Excel: o
  Python não recalcula fórmulas (nem as que já existiam no arquivo original, nem as que o
  assistente acabou de criar). A prévia mostra o valor calculado separadamente pra
  fórmulas simples criadas pelo assistente (coluna calculada e linha de total).
- A "coluna calculada" só aceita expressões simples entre colunas numéricas (`+ - * /` e
  parênteses), não interpreta funções de planilha por extenso (tipo `SE`, `PROCV`). Para uma
  sequência numérica por linha (idade decrescente, numeração), use `adicionar_coluna_sequencia`.
