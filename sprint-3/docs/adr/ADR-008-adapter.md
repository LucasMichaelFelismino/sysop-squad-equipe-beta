# ADR 008 — Padrão Estrutural: Adapter

**Equipe Beta:** Rhuan, Lucas Michael, Lucas Delles e Felipe Pampu · **Linguagem:** Python

Documento original: [ADR_008_Estrutural_Equipe_Beta.docx](../../entregas/ADR_008_Estrutural_Equipe_Beta.docx)

| Campo | Descrição |
|---|---|
| Status | Proposta para avaliação da equipe |
| Categoria | Padrão Estrutural |

## 1. Contexto

A arquitetura documentada separa apresentação, domínio e infraestrutura. O domínio possui contratos como `RepositorioDeConsultores`, `RegistroDeDisponibilidade` e `ProvedorDeRotas`; a infraestrutura contém implementações concretas relacionadas a PostGIS, Redis e HTTP. Essa separação permite proteger as regras de negócio das interfaces e dos formatos próprios de cada tecnologia externa.

## 2. Decisão

Adotar Adapter como padrão estrutural para implementar os contratos do domínio e traduzir suas operações para as interfaces concretas das tecnologias externas. Os adaptadores deverão permanecer fora do domínio. O domínio deve continuar dependendo de abstrações, mantendo Ce = 0 como regra arquitetural documentada no material da Sprint 2.

## 3. Alternativas consideradas

- **Adapter — selecionado.** Converte uma interface externa para a interface esperada pelo domínio. É diretamente compatível com os adaptadores de PostGIS, Redis e HTTP descritos na documentação.
- **Facade — não selecionado como padrão principal.** Oferece uma interface simplificada para um conjunto de componentes, mas não substitui por si só a necessidade de adaptar interfaces externas aos contratos do domínio.
- **Proxy — não selecionado como padrão principal.** Intermedeia o acesso a outro objeto para controlar acesso, cache ou execução. Pode ser útil em necessidades específicas, mas não é a necessidade arquitetural principal identificada.

## 4. Como utilizar no projeto

Para cada integração, implementar um adaptador que cumpra o contrato do domínio e encapsule os detalhes técnicos da tecnologia. Por exemplo, `MapsHTTPAdapter` implementa `ProvedorDeRotas` e transforma a solicitação de cálculo de rota em uma chamada HTTP, convertendo a resposta externa para o formato utilizado pelo domínio.

### Exemplo ilustrativo em Python

```python
class MapsHTTPAdapter:
    def __init__(self, cliente_http):
        self.cliente_http = cliente_http

    def calcular_rota(self, origem, destino):
        resposta = self.cliente_http.get(
            "/rotas",
            params={"origem": origem, "destino": destino}
        )
        resposta.raise_for_status()
        return resposta.json()
```

## 5. Consequências

- **Positivas:** reduz o acoplamento com tecnologias externas; facilita substituir provedores; permite testar o domínio sem serviços reais; mantém a direção das dependências para os contratos.
- **Custos e riscos:** exige código de tradução e mapeamento de dados; diferenças semânticas entre o contrato e a API externa precisam ser tratadas; adaptadores podem ficar excessivamente complexos se acumularem responsabilidades.
- **Governança:** manter adaptadores no pacote de infraestrutura; preservar os contratos no domínio; revisar importações para garantir que o domínio não dependa de PostGIS, Redis ou clientes HTTP concretos.

## 6. Critérios de validação

Criar testes de contrato para cada adaptador, incluindo respostas válidas, erros de comunicação e conversão de dados. Confirmar por análise de dependências que o domínio importa somente os contratos. O exemplo é ilustrativo; a documentação identifica o adaptador `MapsHTTPAdapter`, mas não fornece evidência de que o código acima esteja implementado.

## 7. Referência documental

Sysop Squad. Relatório de Arquitetura Sprint 2. Documento fornecido pela equipe. Seções sobre pacotes, adaptadores, inversão de dependências e macroarquitetura.

---

> **Implementação:** os adaptadores existem desde a Sprint 2 ([`sprint-2/src/sysop_squad/infra`](../../../sprint-2/src/sysop_squad/infra)). Na Sprint 4 ([`sprint-4/src/sysop_squad/infra`](../../../sprint-4/src/sysop_squad/infra)) entraram também `ChamadosPostgresAdapter`, `TriagemAMQPAdapter` e `RotasEstimadasPorDistancia`. O `MapsHTTPAdapter` real implementa `ProvedorDeRotas.estimar` sobre a API do OSRM. Testes de contrato em [`sprint-4/tests/test_rotas_maps_http.py`](../../../sprint-4/tests/test_rotas_maps_http.py) e [`sprint-4/tests/test_contrato_disponibilidade.py`](../../../sprint-4/tests/test_contrato_disponibilidade.py).
