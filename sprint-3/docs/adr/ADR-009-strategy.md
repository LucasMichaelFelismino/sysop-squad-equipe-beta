# ADR 009 — Padrão Comportamental: Strategy

**Equipe Beta:** Rhuan, Lucas Michael, Lucas Delles e Felipe Pampu · **Linguagem:** Python

Documento original: [ADR_009_Comportamental_Equipe_Beta.docx](../../entregas/ADR_009_Comportamental_Equipe_Beta.docx)

| Campo | Descrição |
|---|---|
| Status | Proposta para avaliação da equipe |
| Categoria | Padrão Comportamental |

## 1. Contexto

O `MotorDeRoteamento` seleciona consultores considerando localização, habilidade e disponibilidade. Manter todos os critérios e algoritmos em uma única implementação pode tornar as regras difíceis de alterar e testar. A arquitetura precisa permitir a evolução dos critérios sem criar dependência direta do domínio em tecnologias externas.

## 2. Decisão

Adotar Strategy para encapsular algoritmos alternativos de seleção de consultores por trás de um contrato comum. O `MotorDeRoteamento` deverá coordenar o processo e delegar a escolha à estratégia configurada. A estratégia escolhida deverá representar uma regra de negócio explícita e ser fornecida por composição de dependências; não deverá acessar diretamente drivers de infraestrutura.

## 3. Alternativas consideradas

- **Strategy — selecionado.** Permite trocar um algoritmo por outro sem alterar a estrutura do componente que o utiliza. É adequado para separar critérios alternativos de seleção de consultores.
- **Observer — não selecionado como padrão principal.** Permite notificar componentes interessados sobre eventos. Pode complementar a arquitetura assíncrona, mas não resolve diretamente a variação dos algoritmos de roteamento.
- **Chain of Responsibility — não selecionado como padrão principal.** Encaminha uma solicitação por uma sequência de responsáveis. Pode ser útil para uma sequência de tentativas ou triagem manual, mas o material não exige que a seleção principal seja uma cadeia fixa.

## 4. Como utilizar no projeto

Definir um contrato de estratégia, como `EstrategiaDeRoteamento`, com uma operação de seleção. Implementar algoritmos concretos, por exemplo `MenorDistancia` ou `MaiorCompatibilidade`, e injetar a estratégia no `MotorDeRoteamento`. Os nomes e critérios concretos deverão ser confirmados pela equipe com base nos requisitos reais do sistema.

### Exemplo ilustrativo em Python

```python
class EstrategiaDeRoteamento:
    def selecionar(self, candidatos):
        raise NotImplementedError


class MenorDistancia(EstrategiaDeRoteamento):
    def selecionar(self, candidatos):
        if not candidatos:
            return None
        return min(candidatos, key=lambda c: c.distancia)


class MotorDeRoteamento:
    def __init__(self, estrategia):
        self.estrategia = estrategia

    def rotear(self, candidatos):
        return self.estrategia.selecionar(candidatos)
```

## 5. Consequências

- **Positivas:** cada algoritmo pode ser desenvolvido e testado isoladamente; novas regras podem ser acrescentadas com menor impacto no motor; facilita comparar políticas de seleção.
- **Custos e riscos:** aumenta a quantidade de classes; é necessário definir como a estratégia será escolhida; regras que compartilham muitas etapas podem gerar duplicação se a implementação não for planejada.
- **Governança:** manter as estratégias focadas na regra de negócio; evitar dependências de infraestrutura; testar casos sem candidatos, empates e candidatos com diferentes critérios.

## 6. Critérios de validação

Testar cada estratégia isoladamente e testar o motor com estratégias diferentes. Validar candidatos vazios, critérios de desempate e consistência dos resultados. O código é ilustrativo: o material Sprint 2 descreve o `MotorDeRoteamento` e seus critérios gerais, mas não comprova que Strategy esteja implementado.

## 7. Referência documental

Sysop Squad. Relatório de Arquitetura Sprint 2. Documento fornecido pela equipe. Seções sobre pacotes, adaptadores, inversão de dependências e macroarquitetura.

---

> **Implementação (Sprint 4):**
> - Contrato `EstrategiaDeSelecao` em [`dominio/portas.py`](../../../sprint-4/src/sysop_squad/dominio/portas.py).
> - Estratégia `MenorTempoDeDeslocamento` em [`dominio/estrategias.py`](../../../sprint-4/src/sysop_squad/dominio/estrategias.py).
> - Injeção no `MotorDeRoteamento` pela composição.
> - [`sprint-4/tests/test_estrategia.py`](../../../sprint-4/tests/test_estrategia.py) mostra uma segunda estratégia mudando a escolha sem alterar o motor.
