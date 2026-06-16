# 🤖 ERP Support Assistant

> Copiloto de Suporte Nível 1 inteligente para o **Odoo ERP** com isolamento estrito de tenants, busca RAG híbrida avançada e orquestração baseada em agentes autônomos com **LangGraph**.

---

## 🎯 Visão Geral

O **ERP Support Assistant** é um MVP (Minimum Viable Product) de suporte técnico de nível 1 projetado para atender múltiplos clientes (multi-tenant) no ecossistema de sistemas ERP, utilizando como base de conhecimento a documentação oficial do **Odoo ERP**. 

O sistema permite que usuários façam perguntas operacionais sobre o sistema, anexem imagens/prints de tela com erros, e obtenham respostas contextualizadas geradas por IA a partir de manuais técnicos. Se a inteligência artificial não encontrar respostas na base de conhecimento ou detectar insatisfação extrema, ela simula a escalação do caso criando um ticket/chamado para o suporte de Nível 2.

---

## 🛠️ Arquitetura e Fluxo do Agente

O núcleo da aplicação utiliza o **LangGraph** para criar um fluxo não-linear em grafo direcionado, guiado por uma máquina de estados:

```
                      ┌────────────────────────┐
                      │  Mensagem do Usuário   │
                      │  (Texto e/ou Imagem)   │
                      └───────────┬────────────┘
                                  │
                       [ Roteador Inteligente ]
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼ (Imagem de Erro)       ▼ (Dúvida Técnica)       ▼ (Escalação)
  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
  │ Vision Node  │         │   RAG Node   │         │ Action Node  │
  │  (Gemini 2)  │         │  (Qdrant DB) │         │ (Abertura de │
  └──────┬───────┘         │  BM25 + RRF  │         │   Chamado)   │
         │                 └──────┬───────┘         └──────┬───────┘
         └──────────┬─────────────┘                        │
                    ▼                                      ▼
             [ Resposta IA ]                         [ Ticket ID ]
```

1. **Roteador Inteligente (`router_edge`):** Avalia se a entrada contém uma imagem (direciona para `Vision Node`), se o usuário quer abrir um chamado humano (direciona para `Action Node`), ou se é uma pergunta operacional (direciona para `RAG Node`). Utiliza Groq Llama 3.3 com fallback para Gemini.
2. **Nó de Visão (`vision_node`):** Processa imagens e prints de erros enviados no formato base64 através da API Multimodal do Gemini 2.5 Flash, extraindo textos técnicos e convertendo-os em contexto útil de pesquisa.
3. **Nó RAG (`rag_node`):** Realiza uma busca híbrida e gera a resposta contextualizada usando Groq Llama 3.3 (ou Gemini como fallback), exibindo também as fontes utilizadas.
4. **Nó de Ação (`action_node`):** Gera um identificador único de ticket (`TK-XXXXXX`) e abre um chamado no banco de dados para atenção humana.

---

## ✨ Recursos Principais

* **Isolamento de Tenants (Multi-tenancy):** Separação estrita de dados nos bancos relacional (SQLite) e vetorial (Qdrant) através da chave `tenant_id`. Um cliente jamais acessa informações ou histórico de outro.
* **Busca RAG Híbrida:** Combina busca semântica (Dense Vectors gerados localmente de forma offline via `sentence-transformers/all-MiniLM-L6-v2` de 384 dimensões) com busca lexical por palavras-chave (Sparse via `BM25Retriever`). Isso elimina gargalos e limites de cota da API.
* **Reranking por RRF (Reciprocal Rank Fusion):** Fusão de scores de busca para reclassificar os pedaços de textos mais relevantes, colocando o que realmente importa no topo do contexto.
* **Semantic Chunking:** Divisão dos manuais em pedaços baseados na variação do significado semântico das sentenças, em vez de cortes arbitrários por número de caracteres.
* **Memória Inteligente:** Sumarização automática do histórico após 5 mensagens, preservando contexto de conversas longas e economizando tokens de API.
* **Painel Administrativo:** Interface intuitiva para upload e gerenciamento de arquivos de documentação para cada tenant.
* **Monitoramento de Contexto:** Widget em tempo real na interface gráfica mostrando o consumo da janela de tokens de contexto do modelo.
* **Conversor RST para MD/TXT:** Pipeline automático para converter repositórios de documentação legados (Sphinx RST) para formatos legíveis pelo RAG.

---

## ⚙️ Tecnologias Utilizadas

* **Backend:** Python 3.12, FastAPI, LangChain, LangGraph
* **Banco de Dados Relacional:** SQLite (com SQLAlchemy ORM)
* **Banco de Dados Vetorial:** Qdrant (modo tempo real/disco)
* **Inteligência Artificial (LLM & Embeddings):** Groq (`llama-3.3-70b-versatile` para chat/roteamento), Google Gemini (`gemini-2.5-flash` para visão) e local `sentence-transformers/all-MiniLM-L6-v2` (embeddings de 384 dimensões executados offline).
* **Conversão de Documentos:** Pandoc / `pypandoc`
* **Frontend:** HTML5, CSS3 (Glassmorphism), Vanilla JavaScript

---

## 📂 Estrutura de Diretórios

```
support/
├── app/
│   ├── config.py         # Configurações do app e leitura do .env
│   ├── database.py       # Configuração e Sessão do SQLAlchemy (SQLite)
│   ├── main.py           # Ponto de entrada FastAPI e inicialização do servidor
│   ├── models/           # Modelos ORM (Tenant, User, Conversation, Message)
│   ├── routes/           # Rotas FastAPI (chat.py, documents.py)
│   ├── schemas/          # Validação de dados com Pydantic
│   ├── seeder.py         # Dados iniciais para simulação do MVP
│   └── services/         # Regras de Negócio (agent_service.py, qdrant_service.py)
├── documents/            # Documentos convertidos organizados para ingestão
│   ├── md/
│   └── txt/
├── scratch/              # Scripts rápidos para teste em desenvolvimento
├── scripts/
│   ├── convert_docs.py   # Conversor de RST para MD/TXT via Pandoc
│   └── ingest_converted_docs.py # Importação automatizada de diretórios de docs no Qdrant
├── static/               # Interface web estática (Chat & Admin UI)
├── requirements.txt      # Dependências do Python
└── .env                  # Variáveis de ambiente configuradas
```

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
* Python 3.11 ou 3.12 instalado.
* Se for usar o conversor de documentos (`convert_docs.py`), tenha o **Pandoc** instalado na máquina. (O instalador Windows está incluído na raiz: `pandoc-3.10-windows-x86_64.msi`).

### 1. Configurar o Ambiente Virtual
Na pasta raiz do projeto, ative o ambiente virtual existente:

* **No PowerShell:**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **No CMD:**
  ```cmd
  .\venv\Scripts\activate.bat
  ```

Se precisar reinstalar as dependências:
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente
Copie o modelo de ambiente `.env.example` para `.env` e preencha as variáveis de ambiente necessárias (principalmente suas chaves de API da Google e da Groq):

```env
# Google Gemini API Credentials
GEMINI_API_KEY=sua-chave-api-gemini-aqui
GEMINI_MODEL=gemini-2.5-flash

# Groq API Credentials
GROQ_API_KEY=sua-chave-api-groq-aqui
GROQ_MODEL=llama-3.3-70b-versatile

# Database Settings
DATABASE_URL=sqlite:///./app.db

# Qdrant Settings (Local)
QDRANT_PATH=./qdrant_data
QDRANT_URL=

# Configurações do Servidor
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Senha do Painel Administrativo
ADMIN_PASSWORD=admin
```

### 3. Rodar o Servidor FastAPI
Com o ambiente virtual ativado, inicie o servidor de backend:

```bash
python -m app.main
```
Ou usando Uvicorn diretamente:
```bash
uvicorn app.main:app --reload
```

O banco SQLite (`app.db`) e os dados iniciais do seeder serão gerados automaticamente no primeiro startup.

### 4. Acessar a Interface Gráfica
* **Área do Cliente (Chat):** Acesse [http://localhost:8000/](http://localhost:8000/) no seu navegador.
* **Painel Administrativo (Ingestão/Remoção de Manuais):** Acesse [http://localhost:8000/admin](http://localhost:8000/admin).
  * *Chave de Acesso Admin:* `admin` (ou conforme configurado na chave `ADMIN_PASSWORD` no `.env`).

---

## 🗂️ Conversão e Ingestão de Grandes Volumes de Documentos

Se você tiver uma pasta contendo uma grande árvore de documentação do sistema ERP (no formato `.rst` do Sphinx), você pode rodar o pipeline automatizado de ingestão:

### Passo 1: Converter os arquivos `.rst` para `.md` e `.txt`
Abra o arquivo [`scripts/convert_docs.py`](file:///d:/MAYCON/AGENTES/support/scripts/convert_docs.py) e ajuste os caminhos nas variáveis `SOURCE_DIR`, `TARGET_MD_DIR` e `TARGET_TXT_DIR`. Em seguida, execute:

```bash
python scripts/convert_docs.py
```

### Passo 2: Ingerir os documentos no Qdrant
Para indexar os documentos convertidos na base de dados vetorial de um tenant específico, execute:

```bash
python scripts/ingest_converted_docs.py --subdir pasta-dos-documentos --tenant quantum_corp
```

#### ⚠️ Nota importante sobre concorrência e o Qdrant Local:
Como o Qdrant está configurado em modo embutido local (`QDRANT_PATH=./qdrant_data`), **apenas uma instância/processo** pode ler e escrever no diretório do banco de dados por vez.
* Se o script `ingest_converted_docs.py` estiver rodando, o servidor FastAPI (`app.main`) gerará erros `500 (Internal Server Error)` se você tentar consultar documentos na interface web, pois o script bloqueia o acesso exclusivo.
* **Solução:** Aguarde o script finalizar ou use um container Docker para o Qdrant configurando `QDRANT_URL=http://localhost:6333` no `.env`.
