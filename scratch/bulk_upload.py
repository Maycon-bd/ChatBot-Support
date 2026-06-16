import os
import sys
import time
from pathlib import Path
import requests

# Ajusta PYTHONPATH para que as importações internas do app funcionem
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

def main():
    api_url_list = "http://localhost:8000/api/v1/documents/list"
    api_url_upload = "http://localhost:8000/api/v1/documents/upload"
    headers = {
        "X-Admin-Key": "admin",
        "X-Tenant-ID": "quantum_corp"
    }

    doc_dir = ROOT_DIR / "documents" / "md"
    if not doc_dir.exists():
        print(f"Erro: O diretório de documentos '{doc_dir}' não existe.")
        return

    # 1. Recupera documentos que já foram indexados no Qdrant para evitar duplicidade
    try:
        res = requests.get(api_url_list, headers=headers)
        res.raise_for_status()
        uploaded_docs = {item["source"] for item in res.json()}
        print(f"Carregados {len(uploaded_docs)} documentos já indexados a partir do servidor.")
    except Exception as e:
        print(f"Erro ao buscar documentos indexados: {e}")
        return

    # 2. Coleta todos os arquivos .md recursivamente
    all_files = list(doc_dir.rglob("*.md"))
    files_to_upload = []
    for f in all_files:
        rel_path = f.relative_to(doc_dir)
        # Normalização de caminhos para comparação entre OS
        rel_path_str = str(rel_path)
        rel_path_alt1 = rel_path_str.replace("/", "\\")
        rel_path_alt2 = rel_path_str.replace("\\", "/")
        
        if (rel_path_str not in uploaded_docs and 
            rel_path_alt1 not in uploaded_docs and 
            rel_path_alt2 not in uploaded_docs):
            files_to_upload.append((f, rel_path_str))

    total_files = len(files_to_upload)
    print(f"Total de arquivos .md encontrados: {len(all_files)}. Faltando indexar: {total_files}.")
    
    if total_files == 0:
        print("Todos os documentos já estão indexados no Qdrant.")
        return

    success_count = 0
    error_count = 0
    delay = 0.05  # Intervalo de segurança em segundos entre as requisições

    print("="*60)
    print("Iniciando Importação em Lote via API HTTP")
    print("="*60)

    for idx, (filepath, rel_name) in enumerate(files_to_upload, 1):
        print(f"[{idx}/{total_files}] Ingerindo: {rel_name} ... ", end="", flush=True)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                print("Ignorado (Arquivo Vazio)")
                continue

            # Payload em multipart form-data
            files = {
                "file": (os.path.basename(rel_name), content, "text/markdown")
            }

            retries = 5
            backoff = 25.0
            success = False

            for attempt in range(retries):
                try:
                    response = requests.post(api_url_upload, headers=headers, files=files)
                    
                    if response.status_code == 200:
                        print(f"OK ({response.json().get('chunks_count', 0)} chunks)")
                        success_count += 1
                        success = True
                        break
                    else:
                        resp_data = response.json()
                        err_msg = str(resp_data.get("detail", "")).lower()
                        
                        # Tratamento de rate limit (Gemini API ou Qdrant)
                        if "resource_exhausted" in err_msg or "429" in err_msg or "rate limit" in err_msg or "limit" in err_msg:
                            print(f"\n[Rate Limit] Limite de API atingido. Aguardando {backoff}s (Tentativa {attempt+1}/{retries})...")
                            time.sleep(backoff)
                            backoff = backoff * 1.5 + 5.0
                        else:
                            print(f"ERRO (Status {response.status_code}): {resp_data.get('detail')}")
                            error_count += 1
                            break
                except Exception as ex:
                    print(f"\nErro na tentativa {attempt+1} de requisição: {ex}")
                    time.sleep(5)
            
            if not success:
                print("FALHA final após múltiplas tentativas.")

            # Pausa para evitar gargalos na API
            time.sleep(delay)

        except Exception as e:
            print(f"ERRO de leitura: {e}")
            error_count += 1

    print("="*60)
    print("Importação em Lote Concluída!")
    print(f"Sucesso: {success_count}")
    print(f"Erros: {error_count}")
    print("="*60)

if __name__ == "__main__":
    main()
