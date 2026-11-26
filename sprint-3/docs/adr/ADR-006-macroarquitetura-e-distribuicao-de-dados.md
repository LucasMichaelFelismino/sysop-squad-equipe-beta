# ADR 006 — Definição da Macroarquitetura e Distribuição de Dados

**Equipe Beta** · Projeto-base: Sysop Squad | Architectural Kata — Roteamento de Chamados e Gestão de Incidentes

Documento original: [ADR_006_Equipe_Beta_Sysop_Squad.docx](../../entregas/ADR_006_Equipe_Beta_Sysop_Squad.docx)

## 1. Identificação e status

| Campo | Descrição |
|---|---|
| Identificador | ADR 006 |
| Título | Definição da Macroarquitetura e Distribuição de Dados |
| Equipe | Equipe Beta |
| Projeto-base | Sysop Squad |
| Status | Proposta para validação da equipe |
| Escopo | Macroarquitetura, organização modular, distribuição de dados e soberania dos dados |

## 2. Contexto e problema

A arquitetura documentada precisa definir uma macroarquitetura coerente com essas propostas e com o contexto técnico e financeiro da Kata. Também precisa estabelecer como os dados serão distribuídos entre os módulos, evitando que diferentes contextos alterem diretamente informações sob responsabilidade de outros módulos.

A escolha deve equilibrar custo operacional, manutenção, desempenho, disponibilidade e possibilidade de evolução. Uma aplicação sem separação modular tende a concentrar responsabilidades; serviços e bancos independentes desde o início podem elevar a complexidade de implantação, comunicação e monitoramento.

## 3. Decisão arquitetural

A Equipe Beta propõe adotar o **Monólito Modular em Camadas**, com módulos delimitados por responsabilidade e contratos explícitos. Os módulos de negócio compartilharão inicialmente a aplicação principal, enquanto a comunicação assíncrona por AMQP será utilizada nos fluxos que se beneficiam de filas.

A aplicação será organizada em quatro camadas: apresentação e entrada, para receber e validar solicitações; aplicação, para coordenar os casos de uso; domínio, para manter as regras de negócio; e infraestrutura, para implementar persistência, cache, mensageria e integrações externas. As regras de negócio dependerão de interfaces, e não diretamente das tecnologias utilizadas.

Os módulos e os dados sob sua responsabilidade serão organizados da seguinte forma:

| Módulo responsável | Dados persistentes propostos | Armazenamento |
|---|---|---|
| Gestão de Chamados | Chamado; Incidente; referência à Loja por identificador. | PostgreSQL |
| Roteamento | Atribuição; histórico e resultado das decisões de roteamento. | PostgreSQL |
| Disponibilidade de Consultores | Consultor; agenda; disponibilidade; capacidade; Região de Atendimento e dados geográficos. | PostgreSQL + PostGIS |
| Triagem | Registro, motivo, status e histórico do tratamento manual. | PostgreSQL |

O PostgreSQL será o armazenamento persistente principal. O PostGIS será utilizado para os dados geográficos necessários às consultas de localização e região de atendimento. Inicialmente, os módulos compartilharão a infraestrutura do banco, com separação lógica de responsabilidades; não será exigida uma instância independente para cada módulo.

O Redis será utilizado como cache temporário de informações de disponibilidade, sem substituir o armazenamento persistente como fonte oficial. O AMQP transportará eventos e mensagens de processamento; filas não serão utilizadas como fonte definitiva dos dados de negócio.

A soberania dos dados será garantida pela propriedade de escrita: cada módulo poderá criar e atualizar os dados sob sua responsabilidade. Os demais módulos acessarão essas informações por interfaces ou contratos definidos, sem alterar diretamente as tabelas de outro módulo.

## 4. Alternativas consideradas

- **Monólito tradicional:** não selecionado, pois a concentração de responsabilidades e o compartilhamento indiscriminado de estruturas poderiam aumentar o acoplamento e dificultar a evolução dos contextos.
- **Microsserviço desde o início:** não adotado como decisão inicial. Embora permita implantação e escalabilidade independentes, acrescenta comunicação de rede, configuração, monitoramento, segurança e custos operacionais. Os limites de domínio não exigem, por si só, serviços separados.
- **Arquitetura totalmente orientada a eventos:** não selecionada como mecanismo exclusivo de comunicação, pois nem toda operação precisa ser assíncrona. AMQP será mantido nos fluxos em que o desacoplamento temporal e o processamento em filas oferecem benefício.
- **Monólito Modular em Camadas:** selecionado por combinar separação lógica dos módulos, comunicação interna simples e menor complexidade inicial de infraestrutura, mantendo a possibilidade de extração futura de módulos quando houver justificativa.

## 5. Consequências, trade-offs e custos

- **Organização e manutenção:** a separação por Bounded Contexts e camadas torna mais explícitas as responsabilidades e reduz dependências entre regras de negócio e infraestrutura. Em contrapartida, exige disciplina para manter interfaces, contratos e limites de acesso, evitando que os módulos voltem a compartilhar estruturas internas indiscriminadamente.
- **Desempenho e escalabilidade:** chamadas internas entre módulos evitam parte da latência e da complexidade de comunicação de rede de uma arquitetura distribuída. Entretanto, a aplicação principal será escalada como uma unidade, o que pode levar à alocação de recursos também para módulos que não estejam sob maior demanda. Consumidores AMQP poderão ser dimensionados conforme a topologia real do broker e a implantação adotada.
- **Disponibilidade e resiliência:** a menor quantidade inicial de componentes implantáveis reduz o esforço operacional. Por outro lado, uma falha grave na aplicação principal poderá afetar mais de um contexto. A solução dependerá de monitoramento, recuperação, redundância compatível com o ambiente e tratamento de falhas nas integrações externas. O uso de AMQP, Retry, Circuit Breaker e fallback para triagem ajuda a tratar falhas específicas, mas não elimina a necessidade de alta disponibilidade da aplicação e da infraestrutura.
- **Persistência e soberania:** manter PostgreSQL/PostGIS como armazenamento principal reduz a complexidade de administrar múltiplos bancos. A propriedade lógica dos dados preserva a autonomia dos contextos, mas precisa ser reforçada por contratos, permissões e regras que impeçam escritas diretas entre módulos. Uma instância compartilhada também mantém dependência operacional do banco principal.
- **Cache e consistência:** Redis pode reduzir consultas repetitivas e acelerar a leitura de disponibilidade. Em contrapartida, exige estratégias de expiração, atualização e invalidação para evitar que informações temporárias desatualizadas influenciem decisões de roteamento. A comunicação assíncrona pode produzir consistência eventual entre contextos e requer tratamento de duplicidade e reprocessamento.
- **Custos financeiros e operacionais:** a proposta evita assumir desde o início os custos de implantação, rede, observabilidade e suporte de vários microsserviços. Não é possível estimar economia ou custo absoluto sem volume de chamados, infraestrutura, hospedagem, regiões, SLA e capacidade da equipe. O crescimento do sistema poderá alterar o equilíbrio e justificar uma revisão da decisão.

## 6. Plano de validação e critérios de aceitação

- Confirmar se a aplicação será implantada como uma única unidade modular e identificar se o consumidor AMQP será executado no mesmo processo ou como worker separado.
- Confirmar a origem oficial dos dados de Loja, Consultor, agenda e disponibilidade; identificar quais dados são mantidos internamente e quais são recebidos por integração.
- Validar o modelo lógico de dados, os responsáveis por escrita e os contratos utilizados nas consultas entre contextos.
- Confirmar a estratégia de cache do Redis, incluindo dados armazenados, expiração, atualização e invalidação.
- Confirmar o broker AMQP, sua topologia, ACK/NACK, redelivery e eventual dead-letter queue; testar idempotência dos consumidores.
- Realizar testes de carga e acompanhar latência, throughput, uso de CPU/memória, conexões com o banco, tamanho das filas e taxa de encaminhamento para triagem.
- Validar os mecanismos de backup, recuperação, monitoramento e redundância compatíveis com a infraestrutura escolhida.

## 7. Riscos e medidas de mitigação

- **Acoplamento entre módulos:** manter contratos explícitos, restringir o acesso às estruturas internas e revisar dependências entre contextos.
- **Falha da aplicação principal afetar vários módulos:** adotar health checks, monitoramento, estratégia de recuperação e redundância compatível com a infraestrutura.
- **Crescimento concentrado em um módulo:** acompanhar métricas de carga e avaliar a extração do módulo somente quando houver evidência de necessidade de escalabilidade independente.
- **Dados desatualizados no Redis:** definir política de expiração e invalidação e preservar o armazenamento persistente como fonte oficial.
- **Duplicidade ou perda no processamento AMQP:** utilizar identificadores de idempotência, registro do resultado processado, monitoramento de filas e políticas de reprocessamento compatíveis com o broker real.
- **Acesso indevido aos dados de outro contexto:** aplicar controle de acesso no nível da aplicação e, quando viável, permissões específicas no banco de dados.

## 8. Pontos em aberto e responsabilidades

A decisão não afirma que a macroarquitetura proposta ou a distribuição física de tabelas já estejam implementadas. A equipe deve confirmar a topologia de implantação, a origem dos dados mestres de Loja e Consultor, a propriedade das informações de disponibilidade, a separação física ou lógica dos esquemas e o processo de operação do Redis e do broker AMQP. Também deverá confirmar se a API HTTP externa será efetivamente exposta, condição para adoção do Kong Gateway conforme a ADR 005.

## 9. Revisão da decisão

Revisar esta ADR quando métricas demonstrarem limitações de escalabilidade ou disponibilidade da aplicação principal; quando algum Bounded Context exigir implantação independente; quando a origem ou a propriedade dos dados de Loja, Consultor ou disponibilidade for alterada; quando a estratégia de persistência/cache mudar; ou quando os custos operacionais deixarem de ser compatíveis com o contexto financeiro da Kata. **Status atual:** Proposta para validação da Equipe Beta.
