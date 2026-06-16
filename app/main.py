import logging  # reload triggered after lock release
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
# Importação dos modelos para garantir que a metadata do SQLAlchemy os reconheça e crie as tabelas
import app.models  
from app.routes import documents, chat

# Configuração de Logs básica para facilitar depuração no terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("app.main")

# 1. Inicializa tabelas do SQLite/PostgreSQL na inicialização do app
logger.info("Verificando e criando tabelas no banco de dados relacional...")
Base.metadata.create_all(bind=engine)
logger.info("Tabelas do banco de dados criadas com sucesso.")

# 2. Instancia a aplicação FastAPI
app = FastAPI(
    title="QuantumFlow Support System",
    description="Backend de copiloto de base de conhecimento com isolamento estrito de tenants, RAG avançado e orquestração por LangGraph.",
    version="1.0.0"
)

# Roda o Seeder na inicialização do servidor
from app.database import SessionLocal
from app.seeder import seed_database

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# 3. Configura CORS para permitir chamadas de interfaces web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Inclui as rotas desenvolvidas
app.include_router(documents.router)
app.include_router(chat.router)

# 5. Configura diretório de arquivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    index_path = "static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "status": "online",
        "service": "ERP Support Assistant"
    })

@app.get("/admin")
def read_admin():
    admin_path = "static/admin.html"
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return JSONResponse({"error": "Admin panel não encontrado."}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Iniciando servidor local em http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
