import os
import sys
import time
import argparse
from pathlib import Path

# Ajusta o PYTHONPATH para que as importações internas do app funcionem
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Importações do projeto
from app.config import settings
from app.services.qdrant_service import QdrantService

def main():
    parser = argparse.ArgumentParser(description="Ingere documentos convertidos (.md ou .txt) no Qdrant do Agente.")
    parser.add_argument("--format", type=str, choices=["md", "txt"], default="md",
                        help="Formato dos arquivos a serem ingeridos (padrão: md).")
    parser.add_argument("--subdir", type=str, default="",
                        help="Subdiretório específico dentro da pasta de documentos para processar (ex: applications/finance).")
    parser.add_argument("--tenant", type=str, default="quantum_corp",
                        help="ID do Tenant para isolamento dos dados (padrão: quantum_corp).")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Intervalo em segundos entre cada arquivo para evitar limites da API Gemini (padrão: 1.0).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Executa apenas a simulação sem gravar no Qdrant.")
    
    args = parser.parse_args()

    doc_dir = ROOT_DIR / "documents" / args.format
    if not doc_dir.exists():
        print(f"Erro: O diretório de documentos '{doc_dir}' não existe. Execute o script de conversão primeiro.")
        sys.exit(1)

    search_dir = doc_dir / args.subdir if args.subdir else doc_dir
    if not search_dir.exists():
        print(f"Erro: O subdiretório especificado '{search_dir}' não existe.")
        sys.exit(1)

    # Coleta todos os arquivos correspondentes recursivamente
    file_extension = f"*.{args.format}"
    files_to_process = list(search_dir.rglob(file_extension))
    total_files = len(files_to_process)
    
    print("="*60)
    print("Iniciando Ingestao de Documentacao no Qdrant")
    print(f" - Formato: {args.format.upper()}")
    print(f" - Diretorio de busca: {search_dir}")
    print(f" - Tenant ID: {args.tenant}")
    print(f" - Total de arquivos encontrados: {total_files}")
    print(f" - Delay de API: {args.delay}s por arquivo")
    print(f" - Modo Simulacao (Dry-Run): {args.dry_run}")
    print("="*60)

    if total_files == 0:
        print("Nenhum arquivo encontrado para ingestão.")
        return

    if args.dry_run:
        print("Arquivos que seriam processados:")
        for idx, f in enumerate(files_to_process[:20], 1):
            print(f" [{idx}] {f.relative_to(doc_dir)}")
        if total_files > 20:
            print(f" ... e mais {total_files - 20} arquivos.")
        print("\n[Dry-Run] Simulação concluída com sucesso.")
        return

    # Inicializa o serviço Qdrant
    try:
        qdrant_svc = QdrantService()
    except Exception as e:
        print(f"Erro ao inicializar o QdrantService: {str(e)}")
        sys.exit(1)

    success_count = 0
    error_count = 0

    for idx, doc_file in enumerate(files_to_process, 1):
        relative_name = doc_file.relative_to(doc_dir)
        print(f"[{idx}/{total_files}] Ingerindo: {relative_name} ... ", end="", flush=True)

        try:
            with open(doc_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.strip():
                print("Ignorado (Arquivo Vazio)")
                continue

            # Ingestão do documento usando o QdrantService com mecanismo de retry para Rate Limit
            point_ids = None
            retries = 5
            backoff = 25.0
            
            for attempt in range(retries):
                try:
                    point_ids = qdrant_svc.ingest_document(
                        text=content,
                        tenant_id=args.tenant,
                        source_name=str(relative_name)
                    )
                    break
                except Exception as ex:
                    err_msg = str(ex).lower()
                    if "resource_exhausted" in err_msg or "429" in err_msg or "rate limit" in err_msg:
                        print(f"\n[Rate Limit] Limite atingido. Aguardando {backoff}s antes de tentar novamente (Tentativa {attempt+1}/{retries})...")
                        time.sleep(backoff)
                        backoff = backoff * 1.5 + 5.0
                    else:
                        raise ex
            
            if point_ids is None:
                raise Exception("Falhou após múltiplas tentativas devido a limites de cota da API do Gemini.")

            print(f"OK ({len(point_ids)} chunks)")
            success_count += 1
            
            # Delay para evitar rate limiting da API de Embeddings do Gemini
            if args.delay > 0:
                time.sleep(args.delay)

        except Exception as e:
            print(f"ERRO: {str(e)}")
            error_count += 1
            # Se for um erro crítico de conexão ou credencial, interrompe o processo
            if "API_KEY" in str(e) or "authentication" in str(e).lower():
                print("Interrompendo a ingestão devido a erro de credencial da API do Gemini.")
                break

    print("\n" + "="*60)
    print("Ingestao Concluida!")
    print(f" - Processados com sucesso: {success_count}")
    print(f" - Falhas de processamento: {error_count}")
    print("="*60)

if __name__ == "__main__":
    main()
