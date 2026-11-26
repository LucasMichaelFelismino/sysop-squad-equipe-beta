# ADR 000 — Adoção de Arquitetura Orientada a Eventos no Fluxo Crítico

- **Status:** Aceito
- **Sprint:** 1

## Contexto

Os drivers P1 (Disponibilidade) e P2 (Resiliência) exigem que a abertura de chamados continue funcionando durante picos de aproximadamente 200 RPS e mesmo quando o Motor de Roteamento estiver degradado ou indisponível.

## Decisão

Adotaremos Arquitetura Orientada a Eventos (Event-Driven Architecture — EDA) no fluxo crítico de criação e roteamento. A borda do sistema continuará expondo APIs síncronas para clientes, mas a confirmação de abertura será desacoplada do processamento interno: após validação mínima, o chamado será persistido/publicado no Message Broker e processado assincronamente pelo Motor de Roteamento.

## Alternativas Rejeitadas

Fluxo integralmente síncrono em cadeia (API → Motor de Roteamento → persistência → resposta), pois aumenta o acoplamento temporal e transforma falhas ou lentidão do roteamento em indisponibilidade percebida pelas lojas.

## Consequências

- **Positivo:** maior absorção de picos, isolamento de falhas e suporte à degradação graciosa.
- **Negativo:** consistência eventual, necessidade de idempotência, rastreabilidade distribuída e maior complexidade operacional.

## Governança

Eventos devem possuir identificador de correlação e chave de idempotência; consumidores devem tolerar reprocessamento; métricas de lag, retries e filas de erro devem ser observáveis.
