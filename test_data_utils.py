import io, zipfile
import data_utils as du

# CSV que imita o arquivo real: separador ';', acentos em latin-1, numero BR.
cabecalho = (
    "RAZÃO SOCIAL EMITENTE;UF EMITENTE;DATA EMISSÃO;VALOR NOTA FISCAL\n"
    "FORNECEDOR ALPHA LTDA;SP;15/01/2024;1.234,56\n"
    "BETA COMERCIO SA;RJ;20/01/2024;10.000,00\n"
    "FORNECEDOR ALPHA LTDA;SP;28/01/2024;500,00\n"
).encode("latin-1")

itens = (
    "DESCRIÇÃO DO PRODUTO/SERVIÇO;QUANTIDADE;VALOR UNITÁRIO;VALOR TOTAL\n"
    "PARAFUSO;100;2,50;250,00\n"
    "PORCA;1.000;0,80;800,00\n"
).encode("latin-1")

# Monta um zip em memoria com os dois CSVs + um dicionario.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("202401_NFs_Cabecalho.csv", cabecalho)
    z.writestr("202401_NFs_Itens.csv", itens)
    z.writestr("dicionario.txt", "VALOR NOTA FISCAL = valor total da nota em reais")

tabelas, dic = du.process_zip(buf.getvalue())

print("=== Arquivos lidos ===")
for nome, df in tabelas.items():
    print(f"\n[{nome}]  dtypes:")
    print(df.dtypes)
    print(df)

cab = tabelas["202401_NFs_Cabecalho.csv"]
print("\n=== Testes de correcao ===")
print("Acento na coluna OK? ->", "DATA EMISSÃO" in cab.columns)
print("Soma total das notas (esperado 11734.56) ->", cab["VALOR NOTA FISCAL"].sum())
print("Maior fornecedor por valor ->",
      cab.groupby("RAZÃO SOCIAL EMITENTE")["VALOR NOTA FISCAL"].sum().idxmax())
print("Data virou datetime? ->", str(cab["DATA EMISSÃO"].dtype))
print("\n=== Contexto para o agente (trecho) ===")
print(du.montar_contexto(tabelas, dic)[:600])
