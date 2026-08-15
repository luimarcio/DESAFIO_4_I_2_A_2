# Consulta Inteligente de Notas Fiscais (CSV) — Desafio 4

Aplicação que permite consultar dados de notas fiscais (arquivos CSV dentro de
um .zip) usando **linguagem natural**. Um agente inteligente construído com
**LangChain** interpreta a pergunta, escreve o código de análise em pandas,
executa e devolve a resposta em texto, tabela ou gráfico.

## Arquitetura (3 camadas)

- **Dados** — `data_utils.py`: abre o .zip, lê cada CSV tratando encoding
  (acentuação), separador (`;`) e números no formato brasileiro (`1.234,56`),
  além de converter datas.
- **Agente** — `create_pandas_dataframe_agent` (LangChain) sobre os dataframes
  carregados, usando o modelo Gemini como "cérebro".
- **Interface** — `app.py` (Streamlit): Interface A (upload do .zip) e
  Interface B (perguntas em linguagem natural).

## Como o agente decide

O agente recebe a pergunta + a descrição das tabelas. Ele **planeja** os passos,
**escreve** código pandas, **executa** numa ferramenta de Python e **observa** o
resultado, repetindo até chegar à resposta. Se gerar um gráfico com matplotlib,
a interface o exibe.

## Rodar no seu computador

1. Instale o Python 3.10+.
2. No terminal, dentro desta pasta:
   ```
   pip install -r requirements.txt
   ```
3. Crie o arquivo `.streamlit/secrets.toml` com sua chave do Gemini:
   ```
   GOOGLE_API_KEY = "sua_chave_aqui"
   ```
   (ou deixe em branco e digite a chave na barra lateral do app)
4. Rode:
   ```
   streamlit run app.py
   ```
5. O navegador abre sozinho. Suba o .zip e pergunte.

## Publicar no Streamlit Community Cloud (sem instalar nada)

1. Crie um repositório no GitHub e suba estes arquivos
   (**não suba** `secrets.toml`).
2. Em share.streamlit.io, conecte o repositório e aponte para `app.py`.
3. Em *Settings → Secrets*, cole:
   ```
   GOOGLE_API_KEY = "sua_chave_aqui"
   ```
4. Publique. Você recebe um link público funcionando.

## Chave da API (gratuita)

Crie em **Google AI Studio** (ai.google.dev). O modelo padrão é `gemini-2.5-flash`;
se o nome mudar, troque a constante `MODELO_LLM` no topo de `app.py`.
