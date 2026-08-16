"""
app.py — Interface Inteligente para Consulta de Arquivos CSV (Desafio 4)
------------------------------------------------------------------------
Camadas do sistema:
  - dados      -> data_utils.py (le e limpa os CSVs do zip)
  - agente     -> LangChain create_pandas_dataframe_agent (interpreta a pergunta
                  e escreve/executa o codigo pandas para respondar)
  - interface  -> este arquivo (Streamlit): Interface A (carga) e B (consulta)

Como o agente decide (resumo p/ o relatorio):
  O agente recebe a pergunta em portugues + a descricao das tabelas. Ele planeja
  os passos, escreve codigo pandas, executa numa ferramenta de Python e observa
  o resultado. Repete ate ter a resposta, e entao responde em texto. Se gerar um
  grafico com matplotlib, nos o exibimos.
"""

import matplotlib
matplotlib.use("Agg")  # backend sem tela, necessario no servidor
import matplotlib.pyplot as plt

import streamlit as st

import data_utils as du
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# StreamlitCallbackHandler mostra o "raciocinio" do agente ao vivo.
# O caminho de import mudou entre versoes; tentamos os dois.
try:
    from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
except Exception:  # noqa: BLE001
    from langchain.callbacks import StreamlitCallbackHandler

# Modelo padrao do Gemini. Fica editavel na barra lateral do app, entao se o
# Google aposentar este nome, basta digitar outro na tela (ex.: "gemini-3.7-flash")
# sem alterar o codigo nem republicar.
MODELO_LLM = "gemini-3.6-flash"

st.set_page_config(page_title="Consulta de NFs com IA", page_icon="📄", layout="wide")
st.title("📄 Consulta Inteligente de Notas Fiscais (CSV)")
st.caption("Suba um .zip com os CSVs e pergunte em português. "
           "Um agente LangChain interpreta e responde a partir dos dados.")

# --- Chave de API: pega dos secrets (recomendado) ou de um campo na barra lateral.
with st.sidebar:
    st.header("Configuração")
    # Tenta ler a chave dos secrets. Se nao houver secrets configurados
    # (ex.: antes da Parte 3), nao quebra: cai para o campo manual.
    try:
        chave_secrets = st.secrets.get("GOOGLE_API_KEY", "")
    except Exception:  # noqa: BLE001
        chave_secrets = ""
    api_key = chave_secrets or st.text_input("Chave da API do Google (Gemini)",
                                              type="password")
    st.markdown("Crie uma chave gratuita no **Google AI Studio**.")
    # Modelo editavel: se o Google aposentar o padrao, e so trocar aqui.
    modelo = st.text_input("Modelo do Gemini", value=MODELO_LLM)


# =========================================================================
# INTERFACE A — Carga dos dados
# =========================================================================
st.subheader("1) Enviar os dados")
arquivo_zip = st.file_uploader("Arquivo .ZIP com os CSVs (e opcionalmente o "
                               "dicionário de dados)", type="zip")

if arquivo_zip is not None:
    try:
        tabelas, dicionario = du.process_zip(arquivo_zip.getvalue())
        if not tabelas:
            st.error("Nenhum arquivo CSV encontrado dentro do .zip.")
            st.stop()
        # Guarda na sessao para nao reprocessar a cada pergunta.
        st.session_state["tabelas"] = tabelas
        st.session_state["dicionario"] = dicionario
        st.success(f"{len(tabelas)} arquivo(s) CSV carregado(s) com sucesso.")
        for nome, df in tabelas.items():
            with st.expander(f"Prévia: {nome}  ({df.shape[0]} linhas × "
                             f"{df.shape[1]} colunas)"):
                st.dataframe(df.head(20))
    except Exception as e:  # noqa: BLE001
        st.error(f"Não consegui ler o arquivo. Detalhe: {e}")
        st.stop()


# =========================================================================
# INTERFACE B — Consulta em linguagem natural
# =========================================================================
if "tabelas" in st.session_state:
    st.subheader("2) Faça sua pergunta")

    exemplos = [
        "Qual fornecedor recebeu o maior valor no período?",
        "Quais foram os cinco maiores fornecedores por valor total?",
        "Qual produto teve o maior volume (quantidade) comprado?",
        "Qual foi o valor total das notas por UF? Mostre um gráfico.",
    ]
    st.markdown("**Exemplos:** " + " · ".join(f"_{p}_" for p in exemplos))

    pergunta = st.chat_input("Digite sua pergunta sobre os dados...")

    if pergunta:
        if not api_key:
            st.warning("Informe a chave da API na barra lateral para continuar.")
            st.stop()

        st.chat_message("user").write(pergunta)

        # Monta o LLM e o agente sobre a LISTA de dataframes carregados.
        llm = ChatGoogleGenerativeAI(model=modelo, temperature=0,
                                     google_api_key=api_key)
        tabelas = st.session_state["tabelas"]
        contexto = du.montar_contexto(tabelas, st.session_state.get("dicionario", ""))

        agente = create_pandas_dataframe_agent(
            llm,
            list(tabelas.values()),          # df1, df2, ...
            prefix=contexto,                 # explica quais sao as tabelas
            agent_type="tool-calling",       # recomendado (usa tool calling)
            verbose=True,
            allow_dangerous_code=True,       # obrigatorio: agente executa codigo
            max_iterations=15,
        )

        with st.chat_message("assistant"):
            plt.close("all")  # limpa graficos antigos
            callback = StreamlitCallbackHandler(st.container())
            try:
                resposta = agente.invoke({"input": pergunta},
                                         {"callbacks": [callback]})
                texto = resposta.get("output", str(resposta))
                st.markdown(texto)
                # Se o agente desenhou algum grafico, exibe.
                for num in plt.get_fignums():
                    st.pyplot(plt.figure(num))
            except Exception as e:  # noqa: BLE001
                st.error(f"Não consegui responder a essa pergunta. Detalhe: {e}")
else:
    st.info("Envie um arquivo .zip acima para liberar a área de perguntas.")
