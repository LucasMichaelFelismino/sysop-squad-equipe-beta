# ADR 004 — Isolamento do domínio por interfaces (DIP)

- **Status:** Aceito
- **Autor:** Líder da Sprint 2
- **Relaciona-se com:** ADR 002 e ADR 003; Drivers P1 e P2

## Contexto

Os ADRs 001 a 003 escolheram tecnologias concretas (PostGIS, Redis, broker, API de Mapas) e essas são justamente as partes mais prováveis de mudar. A regra que decide qual consultor atende cada chamado, ao contrário, é o próprio produto. Com o Motor de Roteamento acessando as bibliotecas diretamente, trocar de tecnologia vira alteração no fluxo crítico e testar a regra exige subir banco, cache e broker.

## Decisão

Adotar o Princípio da Inversão de Dependência no fluxo de roteamento:

- o pacote `dominio` declara as portas como classes abstratas (`abc.ABC`) e não importa nada de infraestrutura;
- as dependências entram por construtor; o domínio não instancia adaptador nem lê configuração;
- os adaptadores implementam as portas e traduzem erros de biblioteca em erros de domínio (ex.: `RoteamentoIndisponivelError`), mantendo timeout e retry fora da regra.

## Alternativa rejeitada

Usar as bibliotecas diretamente no Motor de Roteamento: escreve menos código agora, mas prende a regra ao detalhe e transforma todo teste da regra em teste de integração.

## Consequências

Trocar de tecnologia passa a significar escrever um novo adaptador, sem tocar na regra (positivo); em troca, há mais arquivos e uma camada de indireção a mais para quem lê o código (negativo).

## Testabilidade (principal trade-off)

Com as interfaces, cenários exigidos pelos drivers — como "se o provedor de rotas cair, o chamado vai para triagem manual" (P2) ou "dois chamados não podem reservar o mesmo consultor" (P1) — viram testes de unidade com dublês em memória, executados em milissegundos. O risco é o dublê se comportar diferente do adaptador real e mascarar defeitos; por isso cada porta terá um teste de contrato executado contra as duas implementações. A inversão também não elimina os testes de integração e de carga, que continuam necessários para validar SQL, índice geoespacial e os 200 RPS estimados no BOTE.

## Governança

O `import-linter` (contratos em [`pyproject.toml`](../../pyproject.toml)) interrompe o build se o domínio importar infraestrutura, apresentação ou bibliotecas como psycopg, redis, httpx e pika.

## Onde está no código

| Item | Arquivo |
|---|---|
| Portas | [`src/sysop_squad/dominio/portas.py`](../../src/sysop_squad/dominio/portas.py) |
| Erro de domínio | [`src/sysop_squad/dominio/erros.py`](../../src/sysop_squad/dominio/erros.py) |
| Testes de unidade com dublês (P1 e P2) | [`tests/test_motor.py`](../../tests/test_motor.py) |
| Teste de contrato (dublê × Redis) | [`tests/test_contrato_disponibilidade.py`](../../tests/test_contrato_disponibilidade.py) |
