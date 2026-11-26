# C4 Nível 2 — Contêineres (arquitetura final)

Convenção da Sprint 3: **linha contínua = síncrono**, **linha tracejada = assíncrono**. Cada seta tem protocolo e finalidade.

```mermaid
flowchart LR
    loja["Loja<br/>[Pessoa]"]
    consultor["Consultor de TI<br/>[Pessoa]"]
    operador["Operação / Triagem<br/>[Pessoa]"]

    subgraph sysop["Sistema Sysop Squad"]
        app["Web/Mobile App e Painel Operacional<br/>[Contêiner]"]
        kong["API Gateway<br/>[Contêiner: Kong]<br/>TLS, JWT, rate limiting"]
        api["API de Recepção<br/>[Contêiner: Python/WSGI]<br/>POST /chamados"]
        ia["Orquestrador de Agentes de IA<br/>[Contêiner: Python]<br/>projetado no ADR 011"]
        worker["Worker de Roteamento<br/>[Contêiner: Python]<br/>Motor de Roteamento, retry, Circuit Breaker"]
        mq[("RabbitMQ<br/>[Contêiner: broker AMQP]<br/>roteamento, prioritária, espera, triagem, DLQ")]
        pg[("PostgreSQL + PostGIS + pgvector<br/>[Contêiner: banco]<br/>chamados, consultores")]
        redis[("Redis<br/>[Contêiner: cache]<br/>reservas de consultor")]
        s3[("Object Storage<br/>[Contêiner]<br/>anexos")]
    end

    mapas["API de Mapas<br/>[Externo: OSRM]"]
    llm["Provedor de LLM<br/>[Externo]"]
    inventario["Inventário legado<br/>[Externo]"]
    erp["ERP/RH<br/>[Externo]"]
    idp["Provedor de identidade<br/>[Externo: JWKS]"]

    loja -->|"HTTPS — abre e acompanha"| app
    consultor -->|"HTTPS — atualiza status"| app
    operador -->|"HTTPS — triagem manual"| app
    app -->|"HTTPS/JSON + JWT"| kong
    kong -->|"HTTP — POST /chamados"| api
    kong -->|"HTTPS — chaves JWKS"| idp
    app -->|"HTTPS — URL assinada"| s3
    api -->|"SQL — registra chamado"| pg
    api -.->|"AMQP — chamado.recebido"| mq
    mq -.->|"AMQP — entrega"| ia
    ia -->|"XML/HTTP via ACL"| inventario
    ia -->|"HTTPS — sem PII"| llm
    ia -->|"SQL/pgvector — casos parecidos"| pg
    ia -.->|"AMQP — chamado.registrado.prioridade"| mq
    mq -.->|"AMQP — entrega"| worker
    worker -->|"SQL/PostGIS — candidatos e ciclo de vida"| pg
    worker -->|"RESP — SET NX (reserva)"| redis
    worker -->|"HTTPS — rota, timeout 1,5 s"| mapas
    worker -.->|"AMQP — atribuído, espera, triagem"| mq
    mq -.->|"AMQP — atribuições e triagem"| app
    erp -.->|"sincronização — consultores e habilidades"| pg
```

> **Implementado x projetado.** O código da Sprint 4 implementa a API de Recepção, o Worker de Roteamento, a topologia do RabbitMQ e os adaptadores de PostgreSQL/PostGIS, Redis e Mapas. Nele, a API publica direto em `chamado.registrado.<prioridade>`. O Orquestrador de IA, o inventário legado e o `pgvector` estão projetados no [ADR 011](adr/ADR-011-ecossistema-de-agentes-de-ia.md); quando entrarem, a API passa a publicar em `chamado.recebido`.

## Contêineres

| Contêiner | Tecnologia | Responsabilidade | Decisão |
|---|---|---|---|
| Web/Mobile App e Painel | SPA / app móvel | Abrir e acompanhar chamados; painel de triagem manual | Sprint 1 |
| API Gateway | Kong | Entrada única HTTPS; JWT, TLS, rate limiting, limite de upload | ADR 005 (Sprint 3), ADR 001 |
| API de Recepção | Python (WSGI) | Valida o Contrato de Dados, registra e publica; responde 202 | ADR 000, ADR 002, Contrato de Dados |
| Orquestrador de Agentes de IA | Python | Classifica e enriquece o chamado antes do roteamento | ADR 011 (projetado) |
| Worker de Roteamento | Python | Motor de Roteamento, retry exponencial, Circuit Breaker, ciclo de vida | ADR 010, ADR 012 |
| RabbitMQ | AMQP 0-9-1 | Filas duráveis, Content-Based Router, espera do retry, DLQ | ADR 010 |
| PostgreSQL + PostGIS + pgvector | SQL | Chamados (ciclo de vida), consultores e posição; vetores para RAG | ADR 003, ADR 006 (Sprint 3) |
| Redis | RESP | Reserva atômica de consultor (`SET NX` com expiração) | ADR 003 |
| Object Storage | S3 ou equivalente | Anexos fotográficos | ADR 001 |

## Monólito modular

Seguindo o ADR 006 da Sprint 3, a API de Recepção e o Worker de Roteamento são **o mesmo código** ([`src/sysop_squad`](../src/sysop_squad)) iniciado em dois modos:
- `python -m sysop_squad.apresentacao.composicao api`;
- `python -m sysop_squad.apresentacao.composicao consumidor`.

Assim cada parte pode ser escalada separadamente sem virar microsserviço. Os componentes internos estão no [C4 Nível 3](c4-nivel3.md).
