import sys
from pathlib import Path
import requests

# Ajusta PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.seeder import MANUAL_ERP_GENERICO

def main():
    url = "http://localhost:8000/api/v1/documents/upload"
    headers = {
        "X-Admin-Key": "admin",
        "X-Tenant-ID": "quantum_corp"
    }
    
    # Envia o conteúdo do MANUAL_ERP_GENERICO como um arquivo na requisição
    files = {
        "file": ("manual_treinamento_erp.txt", MANUAL_ERP_GENERICO, "text/plain")
    }
    
    print(f"Enviando POST para {url}...")
    response = requests.post(url, headers=headers, files=files)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

if __name__ == "__main__":
    main()
