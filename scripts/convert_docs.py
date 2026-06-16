import os
import sys
import pypandoc
from pathlib import Path

# Configuração de caminhos padrões
SOURCE_DIR = Path("D:/MAYCON/documentation-19.0/documentation-19.0/content")
TARGET_MD_DIR = Path("D:/MAYCON/AGENTES/support/documents/md")
TARGET_TXT_DIR = Path("D:/MAYCON/AGENTES/support/documents/txt")

def convert_rst_files():
    if not SOURCE_DIR.exists():
        print(f"Erro: O diretório de origem {SOURCE_DIR} não existe.")
        sys.exit(1)

    print("Iniciando varredura de arquivos RST no repositório de documentação...")
    
    # Encontra recursivamente todos os arquivos .rst
    rst_files = list(SOURCE_DIR.rglob("*.rst"))
    total_files = len(rst_files)
    print(f"Total de arquivos .rst encontrados: {total_files}")
    
    if total_files == 0:
        print("Nenhum arquivo encontrado para conversão.")
        return

    # Garante a existência dos diretórios de saída
    TARGET_MD_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_TXT_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0

    for idx, rst_file in enumerate(rst_files, 1):
        # Calcula o caminho relativo ao diretório content/
        relative_path = rst_file.relative_to(SOURCE_DIR)
        
        # Define os caminhos de destino preservando a estrutura de diretórios
        out_md_path = TARGET_MD_DIR / relative_path.with_suffix(".md")
        out_txt_path = TARGET_TXT_DIR / relative_path.with_suffix(".txt")
        
        # Garante a criação das subpastas necessárias
        out_md_path.parent.mkdir(parents=True, exist_ok=True)
        out_txt_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{idx}/{total_files}] Convertendo: {relative_path} ... ", end="", flush=True)

        try:
            # Converte para Markdown
            pypandoc.convert_file(
                str(rst_file),
                "markdown",
                format="rst",
                outputfile=str(out_md_path)
            )
            
            # Converte para Plain Text (Texto Plano)
            pypandoc.convert_file(
                str(rst_file),
                "plain",
                format="rst",
                outputfile=str(out_txt_path)
            )
            
            print("OK")
            success_count += 1
        except Exception as e:
            print(f"ERRO\nFalha ao converter '{relative_path}': {str(e)}")
            error_count += 1

    print("\n" + "="*50)
    print(f"Conversão Concluída!")
    print(f"Arquivos convertidos com sucesso: {success_count}")
    print(f"Falhas durante o processo: {error_count}")
    print(f"Diretórios de saída:")
    print(f" - Markdown: {TARGET_MD_DIR}")
    print(f" - Texto Plano: {TARGET_TXT_DIR}")
    print("="*50)

if __name__ == "__main__":
    convert_rst_files()
