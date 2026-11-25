# Desenho do Contrato de Dados — Payload central para recebimento de chamados

**Sprint 3 — Tópico 2** · Formato: OpenAPI 3.0.3 / Swagger · Payload JSON · Equipe Beta

Documento original: [Contrato_de_Dados_Equipe_Beta.docx](../entregas/Contrato_de_Dados_Equipe_Beta.docx)
Especificação OpenAPI: [openapi/chamados.yaml](openapi/chamados.yaml)

## 1. Objetivo

Definir um contrato padronizado para a troca de dados mais crítica da Equipe Beta: o envio de um chamado pela loja ou sistema de origem para o sistema central, para registro e início do processo de roteamento. O contrato estabelece os campos esperados, seus tipos, as validações básicas e as respostas da API.

## 2. Justificativa da escolha

Foi escolhido YAML com OpenAPI para descrever uma API HTTP/REST, pois a arquitetura da Sprint 2 menciona uma API de recepção e integrações HTTP. OpenAPI permite documentar o endpoint, o payload, os campos obrigatórios e as respostas em um formato legível e utilizável por ferramentas Swagger. O documento não escolhe gRPC porque o material de referência não estabelece que a comunicação central seja baseada em RPC.

## 3. Fluxo coberto pelo contrato

1. A loja ou sistema de origem envia os dados do incidente para `POST /chamados`.
2. A API valida os campos e registra o chamado, atribuindo um identificador interno.
3. O sistema responde com HTTP 202 quando o chamado é aceito para processamento.
4. O fluxo de roteamento pode continuar de forma assíncrona, conforme a arquitetura orientada a eventos descrita para o projeto.

## 4. Contrato OpenAPI (YAML)

A especificação completa está em [openapi/chamados.yaml](openapi/chamados.yaml). Ela é uma proposta de contrato para o projeto. Os nomes dos campos, enumerações e códigos de resposta devem ser confirmados com a equipe e alinhados à implementação existente.

## 5. Explicação dos campos

| Campo | Obrigatório | Finalidade |
|---|---|---|
| `idExterno` | Sim | Identifica a solicitação no sistema de origem e ajuda a prevenir registros duplicados. |
| `loja.id` | Sim | Identifica a loja que abriu o chamado. |
| `loja.latitude` / `longitude` | Sim | Fornece a localização necessária para critérios geográficos do roteamento. É dado de localização e deve ter acesso restrito. |
| `incidente.categoria` | Sim | Classifica o tipo geral do problema para apoiar a triagem. |
| `incidente.descricao` | Sim | Descreve o problema relatado pela loja. |
| `incidente.equipamentoId` | Não | Identifica o equipamento afetado quando essa informação estiver disponível. |
| `prioridade` | Sim | Informa a prioridade inicial, limitada a valores definidos no contrato. |
| `habilidadesNecessarias` | Não | Lista habilidades relevantes para selecionar um consultor compatível. |
| `criadoEm` | Sim | Registra a data e hora de criação com fuso horário. |
| `chamadoId` | Resposta | Identificador interno do chamado na Equipe Beta. |
| `status` | Resposta | Indica que a solicitação foi recebida, não que já foi atribuída a um consultor. |

## 6. Exemplo de requisição

```http
POST /chamados
Content-Type: application/json

{
  "idExterno": "LOJA-00821-2026-000145",
  "loja": {
    "id": "LOJA-00821",
    "latitude": -25.5352,
    "longitude": -49.2034
  },
  "incidente": {
    "categoria": "PDV",
    "descricao": "Caixa 02 não inicia após reinicialização"
  },
  "prioridade": "alta",
  "habilidadesNecessarias": ["suporte_pdv", "hardware"],
  "criadoEm": "2026-10-21T18:40:00-03:00"
}
```

## 7. Respostas esperadas

- **202 Accepted** — Chamado aceito para processamento. A resposta não afirma que um consultor já foi selecionado.
- **400 Bad Request** — Campos obrigatórios ausentes ou valores em formato inválido.
- **409 Conflict** — Identificador externo já registrado, conforme a política de idempotência adotada.
- **422 Unprocessable Entity** — Dados recebidos corretamente, mas incompatíveis com regras de validação do negócio.

## 8. Regras e cuidados

- **Idempotência:** `idExterno` deve ser único por sistema de origem. A implementação deve definir como responder a reenvios da mesma solicitação.
- **Localização e LGPD:** coordenadas da loja devem ser usadas apenas para a finalidade operacional prevista, com controles de acesso e retenção adequados. Evitar incluir dados pessoais desnecessários no payload.
- **Validação:** latitude e longitude devem respeitar seus intervalos; prioridade deve usar apenas os valores permitidos; descrição deve ter limite de tamanho.
- **Assincronia:** HTTP 202 indica aceitação para processamento. O status de roteamento e a atribuição do consultor devem ser comunicados por um mecanismo definido separadamente, se necessário.
- **Compatibilidade:** alterações futuras no contrato devem ser versionadas e avaliadas para não quebrar clientes existentes.

## 9. Limites e premissas

O material da Sprint 2 indica API de recepção, roteamento por localização, habilidade e disponibilidade, integrações de infraestrutura e processamento orientado a eventos. Entretanto, não define no conteúdo disponível o esquema exato do payload, os nomes oficiais dos campos, a rota HTTP final ou os códigos de resposta. Por isso, esta especificação é um desenho proposto, e não uma transcrição de um contrato já existente. Os campos foram escolhidos para representar os dados mínimos necessários ao recebimento e ao início do roteamento.

## 10. Referências

- Equipe Beta — Relatório de Arquitetura Sprint 2, documento fornecido pela equipe.
- OpenAPI Specification 3.0.3 — formato utilizado para descrever o endpoint HTTP e seus esquemas de dados.
