# 🤖 ERP Support Assistant — Copilot de Suporte Nível 1 com IA Generativa

**Área:** Inteligência Artificial Aplicada · Processamento de Linguagem Natural  
**Instituição:** UniRV — Universidade de Rio Verde  
**Disciplina:** Workshop de Inteligência Artificial  

---

## 👤 Autor

**Maycon Garcia Silva**  
📧 seuemail@academico.unirv.edu.br

---

## 🎯 Introdução

O atendimento de suporte de nível 1 em empresas que utilizam sistemas ERP (*Enterprise Resource Planning*) representa um gargalo operacional significativo: usuários com dúvidas básicas de operação demandam tempo de analistas qualificados, gerando filas, atrasos e aumento de custo.

Este projeto propõe um **assistente inteligente de suporte** baseado em Modelos de Linguagem de Grande Escala (LLM), capaz de responder perguntas operacionais diretamente a partir da documentação técnica do ERP, dispensando a intervenção humana para questões de primeiro nível. Como caso de estudo e base de conhecimento prática, o projeto utiliza a documentação oficial do **Odoo ERP** (uma das principais plataformas de gestão empresarial do mundo).

O sistema demonstra como técnicas modernas de **RAG (Retrieval-Augmented Generation)**, **agentes autônomos** e **banco de dados vetorial** podem ser combinadas para criar um copilot de suporte especializado, contextualizado e auditável — sem compartilhar dados sensíveis com serviços externos.

---

## 🛠️ Metodologia

A solução é alimentada pelo repositório de documentação oficial do **Odoo ERP** e construída sobre uma arquitetura em camadas que integra quatro tecnologias-chave:

### 1. Arquitetura de Agente com LangGraph
O fluxo de atendimento é modelado como uma **máquina de estados** (grafo dirigido) utilizando o framework **LangGraph**. Um nó roteador classifica a intenção do usuário e direciona o fluxo para:

| Nó | Ação |
|---|---|
| **Vision Node** | Analisa prints de erro enviados pelo usuário via OCR multimodal |
| **RAG Node** | Busca contexto na base vetorial e gera resposta com o LLM |
| **Action Node** | Simula abertura de chamado técnico (integração Nível 2) |

### 2. RAG Híbrido com Fusão de Rankings (RRF)
A busca de contexto combina dois mecanismos complementares:
- **Busca Semântica (Dense):** vetores gerados pelo modelo `gemini-embedding-001` (3.072 dimensões) armazenados no **Qdrant** (banco vetorial local)
- **Busca por Palavras-Chave (BM25):** índice esparso em memória via `BM25Retriever`
- **Reranking:** os resultados das duas buscas são fundidos pelo algoritmo **Reciprocal Rank Fusion (RRF)**, que combina rankings sem depender de escores absolutos

### 3. Memória Persistente com Sumarização
O histórico de cada conversa é armazenado em **SQLite** (via SQLAlchemy). Quando o histórico ultrapassa 5 mensagens, o LLM sumariza automaticamente o excedente e compacta em um único texto, preservando o contexto sem estourar a janela de tokens.

### 4. Stack Tecnológico

```
Backend:     Python 3.12 · FastAPI · LangGraph · LangChain
LLM:         Google Gemini 2.0 Flash (via API Key)
Embeddings:  models/gemini-embedding-001 (3.072 dims)
Vetorial:    Qdrant (modo local, armazenamento em disco)
Relacional:  SQLite + SQLAlchemy ORM
Conversão:   Pandoc / pypandoc (Sphinx RST para MD/TXT)
Frontend:    HTML5 · CSS3 (Glassmorphism) · JavaScript (Vanilla)
```

---

## 📊 Resultados

O sistema demonstra as seguintes capacidades funcionais:

### ✅ Funcionalidades Implementadas
- **Upload de Documentação:** Ingestão de manuais ERP em `.txt` / `.md` com chunking semântico automático
- **Conversão de Documentos:** Pipeline automatizado de conversão em lote de repositórios Sphinx RST para formatos amigáveis (MD e TXT) via Pandoc
- **Ingestão em Massa:** Script robusto para carregar pastas inteiras de documentação na base do Qdrant
- **Chat Inteligente:** Respostas contextualizadas exclusivamente baseadas na documentação carregada
- **Análise de Prints:** Upload de screenshots de erros com análise visual pelo Gemini (multimodal)
- **Abertura de Chamados:** Escalação automática para suporte humano com geração de ID de ticket
- **Monitoramento de Tokens:** Widget em tempo real que exibe o consumo da janela de contexto do LLM com alerta visual quando >80% é consumido
- **Memória de Conversa:** Sumarização automática do histórico para manter coerência em longas sessões

### 🏗️ Complexidade Técnica
- **LLM como Roteador:** O próprio Gemini classifica a intenção antes de responder (`TICKET` vs `SUPPORT`)
- **Busca Híbrida RRF:** Fusão de busca semântica densa + lexical esparsa — técnica de estado da arte em RAG
- **Semantic Chunker:** Divisão do documento por coerência semântica em vez de tamanho fixo
- **Multimodalidade:** Imagens são processadas via Vision API do Gemini e convertidas em contexto textual para a busca RAG
- **Tolerância a Falhas e Rate Limiting:** Ingestor resiliente com retentativas (exponential backoff) para lidar com limites de cota de requisições de API (`ResourceExhausted` / `429`)
- **Resolução de Concurrence Lock:** Diagnóstico e contorno de limitações de trava de arquivos no SQLite/Qdrant local (modo embarcado) sob escrita e leitura concorrentes

### 📈 Métricas de Qualidade
| Critério | Abordagem |
|---|---|
| Rastreabilidade | Trechos recuperados exibidos ao usuário (seção expansível "Ver Contexto RAG") |
| Isolamento | Filtro obrigatório por `tenant_id` em 100% das queries ao Qdrant |
| Transparência | Uso de tokens (input/output/total) exibido após cada resposta |
| Robustez | Fallback manual se LLM de roteamento falhar |

---

## 📚 Referências

- **LangGraph Documentation** — Orchestration of LLM agents as stateful graphs. LangChain AI, 2024. Disponível em: https://langchain-ai.github.io/langgraph
- **Qdrant Vector Database** — High-performance vector similarity search engine. Qdrant, 2024. Disponível em: https://qdrant.tech/documentation
- **Lewis, P. et al.** Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS*, 2020. arXiv:2005.11401
- **Cormack, G. V.; Clarke, C. L. A.; Buettcher, S.** Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. *SIGIR*, 2009.
- **Google DeepMind.** Gemini 2.0 Flash — Technical Report. Google, 2025. Disponível em: https://ai.google.dev/gemini-api/docs
- **FastAPI** — Modern, fast web framework for building APIs with Python 3.8+. Tiangolo, 2024. Disponível em: https://fastapi.tiangolo.com

---

## 📐 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUÁRIO (Navegador Web)                       │
│              Upload de Doc · Chat · Anexo de Print              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (FastAPI)
┌───────────────────────────▼─────────────────────────────────────┐
│                      LANGGRAPH AGENT                            │
│                                                                 │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────────┐   │
│  │ Router Edge  │───▶│ Vision Node │───▶│    RAG Node      │   │
│  │  (Gemini)    │    │ (Multimod.) │    │ Embed → Qdrant   │   │
│  └──────┬───────┘    └─────────────┘    │ BM25 + RRF       │   │
│         │                               │ Gemini → Resposta│   │
│         └──────────────────────────────▶└──────────────────┘   │
│         │                                                       │
│         └──────────────────────────────▶ Action Node (Ticket)  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
┌───────▼───────┐          ┌─────────▼──────┐
│   Qdrant DB   │          │   SQLite DB    │
│ (Vetorial,    │          │ (Conversas,    │
│  Local Disk)  │          │  Mensagens,    │
│               │          │  Tickets)      │
└───────────────┘          └────────────────┘
```

---

> *"O ERP Support Assistant demonstra que é possível construir assistentes de suporte técnico especializado, rastreável e transparente, combinando LLMs modernos com técnicas avançadas de recuperação de informação — sem depender de infraestrutura externa complexa."*
