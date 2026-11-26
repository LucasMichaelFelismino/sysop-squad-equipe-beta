# Registro de Decisão Arquitetural — Retry e Fallback

**Sprint 3 — Tópico 4** · Trade-offs, vantagens, desvantagens e revisão · Equipe Beta

Documento original: [Registro_Decisao_Arquitetural_Equipe_Beta.docx](../../entregas/Registro_Decisao_Arquitetural_Equipe_Beta.docx)

> **Número do ADR:** a confirmar pela equipe (ver seção 8).

## 1. Objetivo

Registrar formalmente a decisão sobre retentativas e fallback do sistema, documentando contexto, decisão, alternativas, trade-offs, vantagens, desvantagens e critérios de revisão.

## 2. Contexto

A Equipe Beta usa mensageria AMQP e integrações com PostgreSQL/PostGIS, Redis e API externa de mapas/rotas. A arquitetura anterior descreve portas e adaptadores e prevê triagem manual para chamados sem roteamento. A Sprint 3 solicita formalizar a decisão no ADR 003/004. Como o material anterior já cita ADR 004, 005 e 006, o número oficial deste registro precisa ser confirmado pela equipe antes da entrega.

## 3. Decisão arquitetural

Propor retry limitado com backoff exponencial e jitter para falhas transitórias, Circuit Breaker para a dependência externa sujeita a indisponibilidade e fallback para triagem manual quando não for possível concluir o roteamento. A política deve respeitar idempotência e a configuração real do broker AMQP. Erros permanentes não devem ser repetidos automaticamente.

## 4. Alternativas consideradas

- **Sem retry automático:** simples e previsível, mas vulnerável a falhas transitórias curtas.
- **Retry imediato e ilimitado:** rejeitado por poder aumentar a carga durante uma indisponibilidade, elevar a latência e repetir operações excessivamente.
- **Retry limitado sem Circuit Breaker:** reduz repetição agressiva, mas pode continuar enviando chamadas a um provedor degradado.
- **Retry limitado + Circuit Breaker + fallback:** recomendado por combinar recuperação de falhas transitórias, interrupção temporária de chamadas e caminho de contingência.
- **Falhar sem triagem manual:** reduz a complexidade operacional, mas não aproveita o caminho de contingência descrito para chamados sem roteamento.

## 5. Trade-offs, vantagens e desvantagens

- **Disponibilidade versus latência:** retries podem recuperar operações, mas aumentam o tempo de conclusão.
- **Resiliência versus complexidade:** o Circuit Breaker evita insistir em serviço degradado, mas adiciona estados e parâmetros a monitorar.
- **Automação versus operação manual:** a triagem mantém o chamado rastreável, mas exige equipe e processo de atendimento.
- **Consistência versus reprocessamento:** mensagens podem ser entregues novamente; idempotência é necessária para evitar efeitos duplicados.
- **Configuração versus previsibilidade:** limites e tempos devem ser ajustados com testes e métricas, não tratados como valores definitivos sem validação.

## 6. Consequências e responsabilidades

- **Aplicação:** classificar falhas e aplicar retry somente às falhas transitórias.
- **Adaptador de mapas:** definir timeout e expor erros de forma consistente; o Circuit Breaker pode ficar na fronteira da integração.
- **Mensageria:** definir ack/nack, redelivery e dead-letter queue conforme o broker real.
- **Domínio:** manter o contrato de encaminhamento para triagem sem importar bibliotecas de infraestrutura.
- **Operação:** monitorar retries, circuitos abertos, mensagens reprocessadas e tamanho da fila de triagem.

## 7. Critérios de aceitação e revisão

- Limites de retry e tempos de espera configuráveis e documentados.
- Falhas permanentes não geram retry automático sem regra explícita.
- Circuit Breaker impede chamadas enquanto aberto e permite teste controlado de recuperação.
- Uma mensagem repetida não gera múltiplos encaminhamentos à triagem.
- Revisar parâmetros após testes de carga e análise de métricas reais.
- Revisar a decisão se a integração de mapas, o fluxo assíncrono ou a estratégia de mensageria mudar.

## 8. Status e histórico

**Status:** Proposto — aguarda validação da equipe e confirmação do número ADR exigido na atividade. Este documento não afirma que retry, Circuit Breaker, dead-letter queue ou fallback já estejam implementados.

## 9. Referência documental

Equipe Beta. Relatório de Arquitetura Sprint 2: monólito em camadas, integração assíncrona por eventos, portas/adaptadores e FilaDeTriagemManual. Sprint 3 — instrução do Tópico 4: decisão arquitetural ADR 003/004 com trade-offs, vantagens e desvantagens.
