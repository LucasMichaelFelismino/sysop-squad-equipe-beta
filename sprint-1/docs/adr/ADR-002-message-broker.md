# ADR 002 — Adoção de Message Broker para Desacoplamento e Fallback

- **Status:** Aceito
- **Sprint:** 1

## Contexto

Picos próximos de 200 RPS e falhas temporárias no Motor de Roteamento não podem impedir que as lojas registrem incidentes, conforme os drivers P1 e P2.

## Decisão

Será utilizado um Message Broker com persistência/durabilidade de mensagens (ex.: RabbitMQ ou Kafka, a ser validado pela pesquisa tecnológica) entre a API de Recepção e o Motor de Roteamento. A API publica o chamado e responde HTTP 202 (Accepted). O roteamento é processado posteriormente por consumidor assíncrono.

## Alternativas Rejeitadas

Comunicação síncrona direta entre API e Motor de Roteamento no caminho crítico, pois uma falha do motor propagaria indisponibilidade para a abertura de chamados.

## Consequências

- **Positivo:** desacoplamento temporal, absorção de burst e reprocessamento controlado.
- **Negativo:** consistência eventual e necessidade de monitorar filas e consumidores.

## Governança

As filas críticas devem ser duráveis; o processamento deve ser idempotente; haverá política de retry com backoff. Após o limite de tentativas ou quando o roteamento permanecer indisponível, o ticket será encaminhado para uma fila de triagem manual. Mensagens irrecuperáveis seguirão para Dead Letter Queue (DLQ) com alerta operacional.
