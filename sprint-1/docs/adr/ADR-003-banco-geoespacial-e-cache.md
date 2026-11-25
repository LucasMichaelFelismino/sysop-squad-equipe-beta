# ADR 003 — Banco Geoespacial e Cache em Memória para Roteamento

- **Status:** Aceito
- **Sprint:** 1

## Contexto

O roteamento inteligente precisa cruzar, em baixa latência, a localização do chamado, a distância dos consultores, suas habilidades técnicas e sua disponibilidade atual.

## Decisão

O Motor de Roteamento utilizará banco com suporte a índices e consultas geoespaciais (ex.: PostgreSQL/PostGIS) para localização, cadastro e habilidades, combinado com cache em memória (ex.: Redis) para o estado de disponibilidade Livre/Ocupado e reservas transitórias.

## Alternativas Rejeitadas

Realizar varreduras e cálculos de distância exclusivamente na aplicação, sem apoio de indexação geoespacial, pois o custo cresce com a quantidade de candidatos e consultas simultâneas e reduz a previsibilidade de latência em picos.

## Consequências

- **Positivo:** consultas geográficas eficientes e leitura rápida do estado operacional.
- **Negativo:** introdução de cache exige estratégia de expiração, sincronização e tratamento de inconsistências temporárias.

## Governança

Mudanças de disponibilidade devem ser propagadas ao cache em até 1 segundo. A atribuição deve utilizar operação atômica de reserva/compare-and-set para impedir que dois tickets reservem simultaneamente o mesmo consultor. O banco permanece como fonte persistente para dados cadastrais e históricos necessários.
