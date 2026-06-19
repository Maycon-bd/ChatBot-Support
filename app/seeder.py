import logging
from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.qdrant_service import QdrantService
from app.config import settings

logger = logging.getLogger(__name__)

MANUAL_ERP_GENERICO = """
=== MANUAL DE OPERAÇÃO E TREINAMENTO - ERP ODOO ===

MÓDULO 1: CADASTRO DE CLIENTES
1.1 Novo Cadastro de Cliente
Objetivo: Registrar clientes no banco de dados para faturamento e controle de contas a receber.
Passo a Passo:
- Acesse o menu lateral: Cadastro > Clientes.
- Clique no botão "+ Novo Cadastro" (ou pressione a tecla de atalho F4).
- Insira as informações obrigatórias: CNPJ/CPF, Razão Social/Nome Completo, Inscrição Estadual (se aplicável), Endereço de Faturamento completo, E-mail e Telefone de contato.
- Vá para a aba "Configurações Fiscais" e selecione o regime de tributação padrão (por exemplo, Simples Nacional ou Lucro Presumido).
- Clique no botão "Salvar" ou pressione CTRL+S.
Aviso Importante: O sistema fará a validação automática do CNPJ diretamente com a base da Receita Federal. Certifique-se de que a conexão com a internet esteja ativa.

MÓDULO 2: EMISSÃO DE NOTA FISCAL ELETRÔNICA (NF-e)
2.1 Fluxo de Faturamento e Emissão de NF-e
Objetivo: Emitir notas fiscais de venda de produtos ou serviços com autorização da SEFAZ.
Passo a Passo:
- Acesse Faturamento > Notas Fiscais > Emitir.
- Selecione o Cliente previamente cadastrado.
- Insira a CFOP (Código Fiscal de Operações e Prestações) apropriada (exemplo: 5.102 para venda de mercadoria adquirida de terceiros no estado, ou 6.102 para venda interestadual).
- Adicione os produtos ao carrinho de faturamento informando quantidade, valor unitário e o código NCM (Nomenclatura Comum do Mercosul).
- Clique em "Calcular Impostos" para o cálculo automático de ICMS, IPI, PIS e COFINS pelo motor fiscal do ERP.
- Clique em "Transmitir para SEFAZ" e aguarde a validação da assinatura digital.
- Se autorizada, faça o download do arquivo XML e imprima o DANFE (Documento Auxiliar da Nota Fiscal Eletrônica).
Resolução do Erro 502: Rejeição por Falha no Certificado Digital
- Caso ocorra o Erro 502 (Falha de Comunicação ou Assinatura), vá em Configurações > Certificado Digital.
- Verifique se o certificado A1 está dentro da data de validade ou se o token físico A3 está conectado à porta USB.
- Atualize a cadeia de certificados do Windows e reinicie o agente de transmissão do ERP.

MÓDULO 3: FLUXO DE CAIXA E RELATÓRIOS FINANCEIROS
3.1 Geração de Relatórios de Vendas e Faturamento
Objetivo: Analisar os resultados financeiros de vendas consolidadas do mês.
Passo a Passo:
- Acesse Financeiro > Relatórios > Fluxo de Caixa ou Vendas Mensais.
- Selecione o período desejado (Data Inicial e Data Final).
- Escolha os filtros de agrupamento: por Vendedor, por Categoria de Produto ou por Região.
- Selecione o formato de exportação (PDF, Planilha Excel ou Gráfico interativo).
- Clique em "Gerar Relatório".
Resolução de Erro de Relatório Vazio:
- Se o relatório for gerado sem dados, certifique-se de que as notas fiscais do período foram de fato "Emitidas" e "Autorizadas", e não apenas "Salvas em Rascunho".

MÓDULO 4: ABERTURA DE CHAMADOS DE SUPORTE
4.1 Suporte Humano Nível 2
Se o usuário encontrar erros persistentes de transmissão na SEFAZ (como rejeições tributárias complexas) ou inconsistências no relatório financeiro que não puderem ser resolvidos por este guia de Nível 1, o assistente inteligente poderá abrir um chamado técnico automaticamente.
O chamado será direcionado para o "Departamento de Operações Fiscais e Suporte de Sistemas ERP".
"""

def seed_database(db: Session):
    """
    Função de Seed automática executada na inicialização da aplicação.
    Configura dados padrões para a demonstração na feira de tecnologia.
    """
    logger.info("Iniciando carga de dados (Seed) para demonstração da feira...")

    # 1. Garante a criação do Tenant oficial do QuantumFlow
    tenant_id = "quantum_corp"
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        logger.info(f"Criando Tenant de demonstração: '{tenant_id}'")
        tenant = Tenant(id=tenant_id, name="ERP Corporation")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    # 2. Garante a criação do Usuário de demonstração
    user_id = "visitante_feira"
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.info(f"Criando Usuário de demonstração: '{user_id}'")
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            name="Visitante da Mostra",
            email="visitante@mostra.com"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. Garante a criação da Conversa de demonstração inicial
    conversation_id = "conversa_demonstracao"
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        logger.info(f"Criando Conversa inicial de demonstração: '{conversation_id}'")
        conversation = Conversation(
            id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            title="Demonstração Suporte ERP"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        # Adiciona mensagem de boas-vindas inicial no banco
        welcome_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="Olá! Sou o Assistente de Suporte ERP. Estou pronto para ajudar com dúvidas operacionais sobre o sistema, notas fiscais, cadastro de clientes ou abertura de chamados."
        )
        db.add(welcome_message)
        db.commit()

    # 4. Garante que os manuais do ERP estão carregados no Qdrant
    try:
        qdrant_service = QdrantService()
        
        # Vamos contar de forma simples buscando pontos específicos do nosso tenant
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        points_exist = qdrant_service.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
            ),
            limit=1
        )[0]

        if not points_exist:
            logger.info("Qdrant não possui manuais do ERP. Executando Semantic Chunking e upload...")
            qdrant_service.ingest_document(
                text=MANUAL_ERP_GENERICO,
                tenant_id=tenant_id,
                source_name="manual_treinamento_erp.txt"
            )
            logger.info("Manuais do ERP indexados com sucesso no Qdrant.")
        else:
            logger.info("Qdrant já possui os manuais do ERP carregados.")

    except Exception as e:
        logger.error(f"Erro ao seedar banco vetorial Qdrant: {str(e)}")

    logger.info("Carga de dados de demonstração (Seed) concluída.")
