# Sprint 2 — Isolamento do domínio (DIP) e validação quantitativa

**Projeto:** Sysop Squad · **Equipe Beta** · **Linguagem:** Python

| Integrante | Papel na Sprint 2 |
|---|---|
| Lucas Michael | Líder da Sprint |
| Rhuan | Pesquisador |
| Lucas Delles | Executor |
| Felipe Pampu | Executor |

Na Sprint 1 a equipe definiu o C4 (níveis 1 e 2) e os ADRs 000 a 003. Nesta sprint, o Motor de Roteamento, que guarda a regra estável do sistema (escolher o consultor por localização, habilidade e disponibilidade), foi separado das tecnologias que ele usa (PostGIS, Redis e API de Mapas) por meio de interfaces. Depois, as métricas de acoplamento mostraram numericamente se essa separação ficou boa.

## Entregas

| Entrega | Onde está |
|---|---|
| Barreiras de SOLID no Diagrama de Contêineres | [docs/01-barreiras-solid-dip.md](docs/01-barreiras-solid-dip.md) |
| Interfaces de isolamento (DIP) | [src/sysop_squad/dominio/portas.py](src/sysop_squad/dominio/portas.py) |
| Diagrama de classes | [docs/img/diagrama-de-classes.png](docs/img/diagrama-de-classes.png) |
| ADR 004 — Isolamento do domínio por interfaces | [docs/adr/ADR-004-isolamento-do-dominio-por-interfaces.md](docs/adr/ADR-004-isolamento-do-dominio-por-interfaces.md) |
| Validação quantitativa (Ca, Ce, I, A e D) | [docs/02-validacao-quantitativa.md](docs/02-validacao-quantitativa.md) |
| ADR 005 — Topologia validada por métricas | [docs/adr/ADR-005-topologia-validada-por-metricas.md](docs/adr/ADR-005-topologia-validada-por-metricas.md) |
| Fitness functions (regras de arquitetura como testes) | [tests/test_arquitetura.py](tests/test_arquitetura.py) e contratos do import-linter em [pyproject.toml](pyproject.toml) |
| Documentos originais entregues | [Sysop Squad - Sprint 2.docx](entregas/Sysop%20Squad%20-%20Sprint%202.docx) · [Atividade de Validação Quantitativa.docx](entregas/Atividade%20de%20Valida%C3%A7%C3%A3o%20Quantitativa.docx) |

> O código desta pasta é o estado da Sprint 2 e corresponde aos números da validação quantitativa. A evolução (State, retry, DLQ, Circuit Breaker) está na [Sprint 4](../sprint-4).

## Pacotes e contêineres

```
src/sysop_squad/
├── dominio/          Motor de Roteamento - regra estável, não importa tecnologia
│   ├── modelo.py       Chamado, ConsultorCandidato, Reserva, Resultado
│   ├── portas.py       RepositorioDeConsultores, RegistroDeDisponibilidade, ProvedorDeRotas
│   ├── motor.py        MotorDeRoteamento
│   └── erros.py        RoteamentoIndisponivelError
├── infra/            Adaptadores - implementam as portas
│   ├── consultores_postgis.py     Banco Geoespacial (PostgreSQL/PostGIS)
│   ├── disponibilidade_redis.py   Cache de disponibilidade (Redis)
│   └── rotas_maps_http.py         API de Mapas (HTTP)
└── apresentacao/     Borda - API de Recepção, consumidor AMQP e composição
    ├── api.py          RecepcaoDeChamadosAPI (responde 202 e publica no broker)
    ├── consumidor.py   ConsumidorDeChamadosAMQP
    ├── composicao.py   ComposicaoDeDependencias (único lugar que instancia adaptadores)
    └── topologia.py    filas e exchanges do RabbitMQ
```

As dependências seguem um só sentido: `apresentacao → infra → dominio`.

## Como rodar

Requer Python 3.11 ou mais novo. Os testes não precisam de banco, Redis nem RabbitMQ.

```bash
cd sprint-2
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,infra]"

pytest                          # testes de unidade, de contrato e fitness functions
lint-imports                    # contratos de camadas (ADR 004)
python tools/metricas.py        # recalcula Ca, Ce, I, A e D (ADR 005)
```

## Métricas atuais

Saída de `python tools/metricas.py`:

| Pacote | Nc | Na | Ca | Ce | I | A | D |
|---|---|---|---|---|---|---|---|
| dominio | 8 | 3 | 6 | 0 | 0,00 | 0,38 | 0,62 |
| infra | 3 | 0 | 1 | 5 | 0,83 | 0,00 | 0,17 |
| apresentacao | 3 | 0 | 0 | 5 | 1,00 | 0,00 | 0,00 |

## Referências

- MARTIN, Robert C. *Clean Architecture*. Prentice Hall, 2017.
- COCKBURN, Alistair. *Hexagonal Architecture (Ports and Adapters)*, 2005.
- RICHARDS, Mark; FORD, Neal. *Fundamentals of Software Architecture*. O'Reilly, 2020.
