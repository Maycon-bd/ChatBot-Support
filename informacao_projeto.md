# 🤖 Guia de Informações e Apresentação do Projeto (Live Demo)

Este documento centraliza todas as informações estratégicas, stack tecnológica, escopo e possíveis perguntas da banca avaliadora para facilitar a sua apresentação na feira universitária da UniRV.

---

## 🎯 O que é o Projeto?
O **ERP Support Assistant** é um **Copiloto de Suporte Nível 1 Inteligente** voltado para o ecossistema do **Odoo ERP**.
Ele foi desenhado para atuar na triagem e resolução automatizada de dúvidas e problemas de usuários do ERP, reduzindo filas de atendimento humano e automatizando tarefas repetitivas. A base de conhecimento do assistente é alimentada diretamente pela documentação técnica e manuais de treinamento do ERP.

O sistema demonstra como técnicas de **RAG Híbrido Avançado**, **Agentes Autônomos (LangGraph)**, **Banco de Dados Vetorial** e **Guardrails de Segurança** podem ser orquestrados de forma moderna, mantendo isolamento de dados e custos de infraestrutura reduzidos.

---

## 🛠️ Stack Tecnológica & Arquitetura
A arquitetura do sistema foi projetada de forma modular e focada em escalabilidade e privacidade:

* **Orquestrador de Agente:** `LangGraph` + `LangChain` (Orquestração baseada em máquina de estados e grafos).
* **Modelos de Linguagem (LLMs):**
  * **Groq (`llama-3.3-70b-versatile`):** Modelo principal de chat, classificação de intenções e sumarização de memória, oferecendo latência ultrabaixa (< 1 segundo por resposta).
  * **Google Gemini (`gemini-2.5-flash`):** Utilizado como **fallback de texto** e como modelo principal do **Vision Node** para leitura multimodal de imagens.
* **Modelo de Embeddings (Offline):** `sentence-transformers/all-MiniLM-L6-v2` executado localmente via PyTorch (dimensão de 384 vetores). Garante 100% de privacidade e custo zero na geração de embeddings.
* **Banco de Dados Vetorial:** `Qdrant` (modo local/embarcado persistido em disco).
* **Banco de Dados Relacional:** `SQLite` (com SQLAlchemy ORM) para gerenciar conversas, usuários, mensagens e chamados.
* **Backend Framework:** `FastAPI` (Python 3.12).
* **Frontend:** `HTML5`, `CSS3 (Vanilla Glassmorphism)` e `JavaScript (Vanilla)`.

---

## 📈 Funcionalidades Principais (O que o Chatbot PODE fazer)
* **Responder Dúvidas Operacionais (RAG):** Responde a perguntas sobre como usar o Odoo ERP baseando-se estritamente nos manuais indexados no banco.
* **Análise Multimodal de Erros (Vision Node):** O usuário pode anexar um print/screenshot de uma tela de erro do ERP. O assistente lê o erro da imagem, extrai o texto técnico e sugere a solução.
* **Abertura Automática de Chamados (Action Node):** Se o usuário solicitar falar com um humano, expressar insatisfação extrema, ou se o assistente não encontrar a resposta na base, ele gera um ticket real de suporte (ex: `TK-3FA28C`) no banco SQLite para o suporte Nível 2.
* **Isolamento Estrito de Tenants (Multi-tenant):** Separação total de dados e históricos de conversas entre clientes do ERP através do header `X-Tenant-ID`.
* **Memória Inteligente por Sumarização:** Limita a janela a 5 mensagens ativas. O excedente anterior é compactado automaticamente em um resumo coeso pelo LLM, economizando tokens e mantendo a coerência.
* **Sanitização e Guardrails de Entrada:** Proteção contra injeções de prompt comuns, vazamento de instruções de sistema e tratamento automático de palavras ofensivas.
* **Proteção de Dados Sensíveis:** Bloqueia proativamente o processamento ou extração de senhas, credenciais administrativas ou segredos de API.
* **Widget de Monitoramento de Contexto:** Exibe na tela a porcentagem atual da janela de contexto consumida pelo LLM, com Toasts dinâmicos que alertam ao atingir as cotas de 10%, 30%, 50%, 80%, 100% e fim de sessão.
* **Plano de Contingência de Rede:** Se a API de nuvem cair ou falhar por conexões instáveis de internet na feira, o backend aciona o plano de contingência e abre automaticamente um ticket local (`TK-CONTINGENCIA`).

---

## 🚫 Limitações de Escopo (O que o Chatbot NÃO PODE fazer)
* **Não Executa Ações no Odoo ERP:** Ele não cria usuários no ERP, não altera faturas, não emite notas e não altera dados internos do Odoo diretamente. Sua função é consultiva (Nível 1).
* **Não Responde Dúvidas Fora da Base (Sem Alucinações):** Se a dúvida do usuário não constar nos manuais indexados, ele não irá "inventar" ou alucinar respostas. Ele informará que não encontrou na base de dados e oferecerá a criação do chamado humano.
* **Não Processa Outros Formatos de Imagem/Arquivos Exóticos:** Suporta apenas formatos de imagem comuns (`.jpeg`, `.png`, `.webp`) no chat e arquivos `.md`, `.txt` ou `.html` no painel de ingestão.
* **Não Revela Segredos Internos:** Bloqueia qualquer tentativa do usuário de extrair senhas de administrador ou as diretrizes que definem o prompt de sistema original da IA.

---

## ❓ Prováveis Perguntas da Banca e Como Responder

### 1. "O que é RAG Híbrido e por que vocês usaram o RRF (Reciprocal Rank Fusion)?"
* **Resposta:** "A busca RAG híbrida combina duas técnicas: a **Busca Semântica (Dense Vectors)**, que entende o significado e o contexto da dúvida mesmo com palavras diferentes, e a **Busca Lexical (Sparse/BM25)**, que busca palavras-chave exatas (como códigos de erro ou nomes de botões). O **RRF** é um algoritmo matemático que junta os dois rankings de resultados e coloca os melhores textos no topo, garantindo maior precisão na resposta do LLM sem depender de pontuações absolutas de algoritmos diferentes."

### 2. "Como funciona o isolamento de tenants (Multi-tenancy) no banco vetorial?"
* **Resposta:** "Nós implementamos o isolamento a nível de metadados no Qdrant. Cada bloco de texto (chunk) ingerido possui a tag `tenant_id` no payload. Nas buscas efetuadas pelo chat, nós injetamos um filtro estrito obrigatório `FieldCondition(key='tenant_id', match=MatchValue(value=tenant_id))`. Isso garante que o banco vetorial ignore completamente os dados de outros clientes, impedindo qualquer tipo de vazamento de informações entre empresas distintas."

### 3. "Por que os embeddings são gerados localmente e offline em vez de usar uma API paga?"
* **Resposta:** "Utilizamos o modelo `sentence-transformers/all-MiniLM-L6-v2` executado localmente. Isso traz três grandes vantagens: **100% de privacidade** (os dados brutos da documentação e as perguntas não são enviados a APIs de terceiros para virarem vetores), **custo zero** (toda a indexação e pesquisa de vetores rodam sem tarifas de API de rede) e **velocidade offline** (elimina a latência da internet no processamento dos embeddings)."

### 4. "O que acontece se a internet do evento oscilar ou cair completamente na hora?"
* **Resposta:** "O sistema possui um **Protocolo de Contingência e Fallback de Rede** implementado diretamente nas rotas do agente. Caso o backend detecte uma perda de conexão com a API externa (da Groq ou Gemini), ele captura a exceção de rede de forma invisível para o usuário, ativa o fallback local e emite uma resposta informando que houve uma instabilidade, gerando automaticamente um chamado local `TK-CONTINGENCIA`. Isso evita que a tela trave ou exiba um traceback de erro feio para a banca."

### 5. "O que define a quebra de textos (chunking) dos manuais para o RAG?"
* **Resposta:** "Utilizamos o **Semantic Chunking**. Em vez de quebrar a documentação a cada 500 caracteres (o que cortaria frases importantes no meio), nós usamos o modelo de embeddings local para monitorar a variação semântica entre as sentenças. Quando a diferença de significado entre uma frase e outra ultrapassa um limiar calculado, o sistema identifica que o assunto mudou e cria a quebra. Isso mantém os tópicos do manual coesos e bem contextualizados."

### 6. "Como vocês evitam que o histórico de conversações estoure o limite de tokens do LLM em papos longos?"
* **Resposta:** "Usamos uma técnica de **Janela Deslizante com Sumarização Ativa**. Mantemos sempre as últimas 5 mensagens na sua forma original no contexto. Qualquer mensagem anterior a essas 5 é agrupada e resumida em um texto condensado pelo LLM. Esse resumo é então mantido no início do contexto do chat. Desta forma, o chatbot retém toda a memória do que aconteceu na conversa por horas, consumindo o mínimo possível de tokens."
