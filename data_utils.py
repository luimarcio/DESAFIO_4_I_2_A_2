"""
data_utils.py
-------------
Funcoes de processamento de dados, separadas da interface (Streamlit) e do
agente (LangChain). Responsabilidades:

  1. Abrir o arquivo .zip enviado pelo usuario.
  2. Ler cada CSV de forma robusta, tratando:
       - encoding (acentuacao) -> tenta utf-8, depois cp1252/latin-1;
       - separador (as NF costumam usar ';') -> deteccao automatica;
       - numeros no formato brasileiro ("1.234,56") -> converte para float;
       - datas -> converte colunas de DATA para datetime.
  3. Ler um eventual dicionario de dados (arquivo .txt/.md/.csv no zip).
  4. Montar um texto de contexto que descreve os dados para o agente.

Manter esta logica isolada facilita testar (ver test_data_utils.py) e deixa
a arquitetura clara: dados / agente / interface sao camadas distintas.
"""

import io
import zipfile
import pandas as pd

# Ordem de tentativa de encoding. utf-8 falha em bytes invalidos (bom: seguimos
# para o proximo); latin-1 nunca falha, por isso fica por ultimo como rede de
# seguranca.
ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]


def _to_float_br(series: pd.Series) -> pd.Series:
    """Converte texto no formato brasileiro '1.234,56' para float 1234.56."""
    s = series.astype(str).str.strip()
    s = s.str.replace(".", "", regex=False)   # remove separador de milhar
    s = s.str.replace(",", ".", regex=False)   # virgula decimal -> ponto
    return pd.to_numeric(s, errors="coerce")


def load_csv_robust(filelike) -> pd.DataFrame:
    """Le um CSV tentando varios encodings e detectando o separador.

    Le tudo como texto (dtype=str) para nao deixar o pandas 'chutar' tipos em
    colunas que sao codigos (chave de acesso, NCM, CFOP). A conversao numerica
    e feita depois, apenas nas colunas certas.
    """
    last_err = None
    for enc in ENCODINGS:
        try:
            if hasattr(filelike, "seek"):
                filelike.seek(0)
            # sep=None + engine='python' detecta o separador automaticamente.
            df = pd.read_csv(filelike, sep=None, engine="python",
                             encoding=enc, dtype=str)
            # Se veio uma coluna so, a deteccao errou: forca ';'.
            if df.shape[1] == 1:
                if hasattr(filelike, "seek"):
                    filelike.seek(0)
                df = pd.read_csv(filelike, sep=";", encoding=enc, dtype=str)
            return _clean_dataframe(df)
        except Exception as e:  # noqa: BLE001 - queremos tentar o proximo encoding
            last_err = e
            continue
    raise last_err


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa nomes de coluna e converte colunas de valor/quantidade e data."""
    # Tira espacos sobrando dos nomes de coluna.
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        upper = col.upper()
        # Converte colunas monetarias e de quantidade (formato brasileiro).
        if any(k in upper for k in ["VALOR", "QUANTIDADE"]):
            convertido = _to_float_br(df[col])
            # So aplica se a conversao funcionou na maioria das linhas.
            if convertido.notna().mean() > 0.5:
                df[col] = convertido
        # Converte colunas de data.
        elif "DATA" in upper:
            convertido = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if convertido.notna().mean() > 0.5:
                df[col] = convertido

    return df


def process_zip(file_bytes: bytes):
    """Recebe os bytes do .zip e devolve (tabelas, dicionario_texto).

    tabelas: dict {nome_do_arquivo: DataFrame}
    dicionario_texto: str com o conteudo de qualquer arquivo de dicionario.
    """
    tabelas = {}
    dicionario_texto = ""

    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
        for nome in z.namelist():
            # Ignora pastas e arquivos de sistema.
            if nome.endswith("/") or "__MACOSX" in nome:
                continue
            dados = z.read(nome)
            nome_baixo = nome.lower()

            if nome_baixo.endswith(".csv"):
                df = load_csv_robust(io.BytesIO(dados))
                # Usa so o nome do arquivo, sem o caminho de pastas.
                tabelas[nome.split("/")[-1]] = df
            elif nome_baixo.endswith((".txt", ".md")):
                for enc in ENCODINGS:
                    try:
                        dicionario_texto += dados.decode(enc) + "\n"
                        break
                    except Exception:  # noqa: BLE001
                        continue

    return tabelas, dicionario_texto


def montar_contexto(tabelas: dict, dicionario_texto: str = "") -> str:
    """Monta o texto que descreve os dados para o agente (vai no 'prefix').

    Como o agente recebe uma LISTA de dataframes, ele os enxerga como df1, df2...
    Aqui explicamos qual e qual, com as colunas de cada um, para que ele saiba
    onde procurar cada informacao.
    """
    linhas = [
        "Voce e um analista de dados. Responda SEMPRE em portugues do Brasil.",
        "Voce tem acesso aos dataframes do pandas listados abaixo.",
        "Use-os para responder. Se um calculo for necessario, calcule com o codigo.",
        "Quando fizer sentido, gere um grafico com matplotlib (plt).",
        "",
        "TABELAS DISPONIVEIS:",
    ]
    for i, (nome, df) in enumerate(tabelas.items(), start=1):
        linhas.append(f"- df{i} (arquivo '{nome}'): {df.shape[0]} linhas, "
                      f"{df.shape[1]} colunas.")
        linhas.append(f"  Colunas: {', '.join(map(str, df.columns))}")

    if dicionario_texto.strip():
        linhas.append("")
        linhas.append("DICIONARIO DE DADOS FORNECIDO:")
        linhas.append(dicionario_texto.strip()[:4000])

    return "\n".join(linhas)
