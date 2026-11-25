# Sprint 4 — Evolução, Governança e Tendências (entrega final)

**Projeto:** Sysop Squad · **Equipe Beta:** Rhuan, Lucas Michael, Lucas Delles e Felipe Pampu · **Linguagem:** Python

O desafio final do Sysop Squad pede: triagem e roteamento inteligente de chamados com IA multi-agente integrada a sistemas legados, entregando:
- Diagrama C4 Nível 2;
- pipeline RabbitMQ com DLQ e retry exponencial;
- ADR do ecossistema de agentes;
- padrão GoF State no ciclo de vida do chamado.

Esta sprint evolui o código da [Sprint 2](../sprint-2) e implementa o que a [Sprint 3](../sprint-3) decidiu.

## Entregas do desafio

| Entrega pedida | Onde está |
|---|---|
| Diagrama C4 Nível 2 | [docs/c4-nivel2.md](docs/c4-nivel2.md) (e o [Nível 3](docs/c4-nivel3.md)) |
| Pipeline RabbitMQ com DLQ e retry exponencial | [ADR 010](docs/adr/ADR-010-rabbitmq-dlq-e-retry-exponencial.md) · [infra/mensageria.py](src/sysop_squad/infra/mensageria.py) · [apresentacao/consumidor.py](src/sysop_squad/apresentacao/consumidor.py) |
| ADR do ecossistema de agentes de IA | [ADR 011](docs/adr/ADR-011-ecossistema-de-agentes-de-ia.md) |
| Padrão GoF State no ciclo de vida do chamado | [ADR 012](docs/adr/ADR-012-padrao-state-ciclo-de-vida-do-chamado.md) · [chamados/ciclo_de_vida.py](src/sysop_squad/chamados/ciclo_de_vida.py) |

## O que a Sprint 3 decidiu e agora está no código

| Decisão da Sprint 3 | Implementação |
|---|---|
| Contrato de Dados (OpenAPI do `POST /chamados`): 202, 400, 409 e 422 | [apresentacao/api.py](src/sysop_squad/apresentacao/api.py), [apresentacao/servidor_http.py](src/sysop_squad/apresentacao/servidor_http.py) |
| Política de Retry e Fallback: 3 tentativas, backoff 1 s e 2 s com jitter, Circuit Breaker, triagem manual | [apresentacao/consumidor.py](src/sysop_squad/apresentacao/consumidor.py), [infra/circuit_breaker.py](src/sysop_squad/infra/circuit_breaker.py) |
| ADR 004: Gestão de Chamados como contexto separado do Roteamento | pacote [chamados](src/sysop_squad/chamados) |
| ADR 005: Content-Based Router por prioridade | [infra/mensageria.py](src/sysop_squad/infra/mensageria.py) |
| ADR 006: Monólito Modular (API e worker no mesmo código) | [apresentacao/composicao.py](src/sysop_squad/apresentacao/composicao.py) |
| ADR 007: Factory Method | `ComposicaoDeDependencias.criar_provedor_de_rotas` |
| ADR 008: Adapter | [infra/](src/sysop_squad/infra) |
| ADR 009: Strategy | [dominio/estrategias.py](src/sysop_squad/dominio/estrategias.py) |
| ADR 005 da Sprint 2: extrair `RotearChamado` e `FilaDeTriagemManual` | [dominio/portas.py](src/sysop_squad/dominio/portas.py); a distância do domínio caiu de 0,62 para 0,50 |

## ADRs da Sprint 4

| ADR | Decisão | Status |
|---|---|---|
| [010](docs/adr/ADR-010-rabbitmq-dlq-e-retry-exponencial.md) | Mensageria RabbitMQ com Content-Based Router, Retry Exponencial e DLQ | Aceito (implementado) |
| [011](docs/adr/ADR-011-ecossistema-de-agentes-de-ia.md) | Ecossistema de Agentes de IA para Triagem e Classificação | Proposto (projetado) |
| [012](docs/adr/ADR-012-padrao-state-ciclo-de-vida-do-chamado.md) | Padrão State no Ciclo de Vida do Chamado | Aceito (implementado) |

## Pacotes

```
src/sysop_squad/
├── dominio/        Roteamento (Core Domain): motor, portas, estratégia - não importa tecnologia
├── chamados/       Gestão de Chamados (Supporting): ciclo de vida com State
├── infra/          Adaptadores: PostGIS, Redis, Mapas + Circuit Breaker, RabbitMQ, PostgreSQL
└── apresentacao/   API (POST /chamados), consumidor AMQP e composição
```

As dependências seguem `apresentacao → infra → (dominio | chamados)`. `dominio` e `chamados` são independentes entre si.

## Como rodar

Requer Python 3.11 ou mais novo. Os testes não precisam de banco, Redis nem RabbitMQ.

```bash
cd sprint-4
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,infra]"

pytest                          # 96 testes: unidade, contrato, consumidor, State, fitness functions
lint-imports                    # contratos de camadas
python tools/metricas.py        # Ca, Ce, I, A e D por pacote
```

Para subir de verdade é preciso PostgreSQL com PostGIS (esquema em [sql/schema.sql](sql/schema.sql)), Redis e RabbitMQ. A configuração vem de variáveis de ambiente (veja `PADROES` em [composicao.py](src/sysop_squad/apresentacao/composicao.py)). Com `SYSOP_MAPAS=local`, a API de Mapas não é usada.

```bash
python -m sysop_squad.apresentacao.composicao api          # POST /chamados na porta 8000
python -m sysop_squad.apresentacao.composicao consumidor   # worker de roteamento
```

## Métricas (governança - ADR 005 da Sprint 2)

| Pacote | Nc | Na | Ca | Ce | I | A | D |
|---|---|---|---|---|---|---|---|
| dominio | 12 | 6 | 9 | 0 | 0,00 | 0,50 | 0,50 |
| chamados | 11 | 2 | 3 | 0 | 0,00 | 0,18 | 0,82 |
| infra | 7 | 0 | 1 | 9 | 0,90 | 0,00 | 0,10 |
| apresentacao | 3 | 0 | 0 | 16 | 1,00 | 0,00 | 0,00 |

- **dominio:** cumpriu as três invariantes do ADR 005 (Ce = 0, dependências estáveis e D ≤ 0,50).
- **chamados:** fica perto da Zona de Dor por ser concreto e estável. A justificativa e o critério de revisão estão no [ADR 012](docs/adr/ADR-012-padrao-state-ciclo-de-vida-do-chamado.md).
