# ADR 005 — Topologia de três pacotes validada por métricas

- **Status:** Aceito
- **Relaciona-se com:** ADR 004

## Contexto

O ADR 004 estabeleceu a separação entre domínio e infraestrutura com base em argumentação qualitativa. Era necessário verificar numericamente se a topologia resultante respeita o Princípio das Dependências Estáveis e identificar seu afastamento em relação à Sequência Principal antes que o sistema cresça e eventuais correções se tornem mais custosas.

## Decisão

Manter a topologia composta pelos três pacotes avaliados e adotar três invariantes verificáveis ao final de cada sprint:

1. o pacote de domínio deve permanecer com Ce = 0 e, consequentemente, I = 0, representando numericamente a regra de importação já automatizada no ADR 004;
2. nenhuma dependência deve apontar para um pacote cuja instabilidade seja maior que a sua;
3. a distância do pacote de domínio deve cair para 0,50 após a extração de `RotearChamado` e `FilaDeTriagemManual`, e as métricas devem ser recalculadas ao final de cada sprint.

## Trade-offs estruturais da topologia

O valor D = 0,62 do domínio decorre da decisão de manter entidades e serviço no mesmo pacote. Separar contratos e modelo em dois pacotes levaria o pacote de contratos a D = 0,00, mas manteria o pacote de modelo em torno de 0,55 e fragmentaria o núcleo em dois artefatos, produzindo um ganho predominantemente numérico nas métricas. Por esse motivo, a fragmentação foi descartada.

Em infra, I = 0,83 com Ca = 1 é intencional, pois esse é o pacote que deve permanecer substituível; um crescimento de Ca nesse ponto indicaria vazamento de dependências tecnológicas para o restante do sistema. Em apresentação, D = 0,00 é compatível com o comportamento esperado de uma borda concreta e descartável.

O risco residual consiste em otimizar a métrica em detrimento do projeto arquitetural, criando abstrações sem consumidores e aproximando o pacote da Zona de Inutilidade. Por isso, a governança avalia D em conjunto com Ca, e nunca de forma isolada.

## Governança

As métricas devem ser recalculadas ao final de cada sprint. O import-linter definido no ADR 004 garante Ce = 0 no domínio ao interromper o build em caso de violação. A topologia deverá ser revista se o Ca de infra ultrapassar 1 ou se a distância do domínio voltar a aumentar.

## Onde está no código

| Invariante | Verificação automática |
|---|---|
| Recalcular Nc, Na, Ca, Ce, I, A e D | [`tools/metricas.py`](../../tools/metricas.py) |
| 1. Domínio com Ce = 0 e I = 0 | `test_dominio_tem_ce_zero_e_instabilidade_zero` em [`tests/test_arquitetura.py`](../../tests/test_arquitetura.py) |
| 2. Dependências apontam para pacotes mais estáveis | `test_dependencias_apontam_para_pacotes_mais_estaveis` |
| Ca de infra não passa de 1 | `test_infra_so_e_instanciada_pela_composicao` |
| 3. Distância do domínio cai para 0,50 | `test_distancia_do_dominio_cai_para_0_50`, marcado como falha esperada até a extração das duas portas. Quando a extração for feita, o teste passa e o marcador deve ser retirado. |
