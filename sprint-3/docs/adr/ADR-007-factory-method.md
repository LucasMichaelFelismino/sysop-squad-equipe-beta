# ADR 007 — Padrão Criacional: Factory Method

**Equipe Beta:** Rhuan, Lucas Michael, Lucas Delles e Felipe Pampu · **Linguagem:** Python

Documento original: [ADR_007_Criacional_Equipe_Beta.docx](../../entregas/ADR_007_Criacional_Equipe_Beta.docx)

| Campo | Descrição |
|---|---|
| Status | Proposta para avaliação da equipe |
| Categoria | Padrão Criacional |

## 1. Contexto

O sistema de roteamento de chamados utiliza componentes de apresentação, domínio e infraestrutura. Entre os componentes de infraestrutura estão adaptadores para PostGIS, Redis e APIs HTTP. A criação desses objetos deve permanecer separada das regras de negócio, para que a seleção de implementações concretas não obrigue o domínio a conhecer tecnologias específicas. A documentação da Sprint 2 já identifica a `ComposicaoDeDependencias` como ponto de composição dos componentes.

## 2. Decisão

Adotar Factory Method nos pontos em que a criação de um componente precisar variar conforme o ambiente ou a configuração. A fábrica deverá retornar objetos compatíveis com os contratos definidos pelo domínio. A `ComposicaoDeDependencias` continuará sendo responsável por montar e conectar as dependências da aplicação; a fábrica não deverá ser criada apenas para encapsular instanciações simples que não variam.

## 3. Alternativas consideradas

- **Factory Method — selecionado.** Centraliza a criação de uma implementação por meio de uma operação de fábrica. É adequado quando o sistema precisa selecionar entre implementações compatíveis, como um adaptador real ou um objeto de teste.
- **Abstract Factory — não selecionado nesta etapa.** É indicado para criar famílias de objetos relacionados. A documentação analisada não demonstra, por enquanto, a necessidade de várias famílias complexas de componentes.
- **Builder — não selecionado nesta etapa.** É indicado quando a construção de um objeto exige várias etapas ou muitas opções. Não há evidência suficiente no material da Sprint 2 de que esse seja um problema atual.

## 4. Como utilizar no projeto

Definir uma fábrica somente para o contrato que possua mais de uma implementação relevante. Por exemplo, uma `FabricaDeRepositorios` pode retornar um adaptador PostGIS em produção ou uma implementação simulada nos testes. A fábrica deve ficar na camada de composição/infraestrutura, e o domínio deve depender apenas do contrato `RepositorioDeConsultores`.

### Exemplo ilustrativo em Python

```python
class FabricaDeRepositorios:
    @staticmethod
    def criar(ambiente, cliente_banco=None):
        if ambiente == "teste":
            return RepositorioDeTeste()
        return RepositorioPostGIS(cliente_banco)
```

## 5. Consequências

- **Positivas:** centraliza a criação nos pontos variáveis; facilita substituir implementações; permite fornecer objetos de teste; reduz a exposição dos detalhes de infraestrutura ao código cliente.
- **Custos e riscos:** acrescenta uma abstração e precisa ser mantido; uma fábrica genérica demais pode dificultar o entendimento; as implementações retornadas devem respeitar o mesmo contrato.
- **Governança:** manter a instanciação e a composição na borda da aplicação; impedir que o domínio importe drivers de infraestrutura; revisar a necessidade de cada fábrica durante mudanças arquiteturais.

## 6. Critérios de validação

Após a implementação, verificar se o objeto retornado satisfaz o contrato esperado, testar a seleção para cada ambiente e confirmar que o domínio não importa módulos concretos de infraestrutura. O exemplo é ilustrativo; o PDF Sprint 2 não comprova que essa fábrica já exista no código.

## 7. Referência documental

Sysop Squad. Relatório de Arquitetura Sprint 2. Documento fornecido pela equipe. Seções sobre pacotes, adaptadores, inversão de dependências e macroarquitetura.

---

> **Implementação (Sprint 4):** Factory Method parametrizado em `ComposicaoDeDependencias.criar_provedor_de_rotas` ([`sprint-4/src/sysop_squad/apresentacao/composicao.py`](../../../sprint-4/src/sysop_squad/apresentacao/composicao.py)). Ele escolhe entre a API de Mapas protegida por Circuit Breaker e a estimativa local, conforme a variável `SYSOP_MAPAS`. Testes em [`sprint-4/tests/test_composicao.py`](../../../sprint-4/tests/test_composicao.py).
