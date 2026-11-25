# C4 Nível 3 — Componentes da aplicação (API de Recepção e Worker de Roteamento)

As setas apontam no sentido da dependência de código. Nenhuma seta sai do `dominio` nem do `chamados` para fora: é a regra que o import-linter e `tests/test_arquitetura.py` verificam.

```mermaid
flowchart TB
    subgraph apresentacao["apresentacao (borda)"]
        http["servidor_http<br/>WSGI POST /chamados"]
        api["RecepcaoDeChamadosAPI<br/>ACL HTTP: DTO OpenAPI → Chamado"]
        cons["ConsumidorDeChamadosAMQP<br/>retry, triagem, DLQ"]
        comp["ComposicaoDeDependencias<br/>Factory Method criar_provedor_de_rotas"]
    end

    subgraph chamados["chamados (Gestão de Chamados — Supporting)"]
        ciclo["CicloDeVidaDoChamado<br/>+ 8 estados (State)"]
        repo["«porta» RepositorioDeChamados"]
    end

    subgraph dominio["dominio (Roteamento — Core Domain)"]
        rotear["«porta» RotearChamado"]
        motor["MotorDeRoteamento"]
        estr["«porta» EstrategiaDeSelecao<br/>MenorTempoDeDeslocamento (Strategy)"]
        portas["«portas» RepositorioDeConsultores,<br/>RegistroDeDisponibilidade, ProvedorDeRotas,<br/>FilaDeTriagemManual"]
    end

    subgraph infra["infra (adaptadores)"]
        postgis["ConsultoresPostGISAdapter"]
        redis["DisponibilidadeRedisAdapter"]
        cb["CircuitBreakerDeRotas (Proxy)"]
        maps["MapsHTTPAdapter (ACL de mapas)"]
        local["RotasEstimadasPorDistancia"]
        tri["TriagemAMQPAdapter"]
        chpg["ChamadosPostgresAdapter"]
        topo["mensageria<br/>filas, espera, DLQ"]
    end

    http --> api
    api --> ciclo
    api --> repo
    api --> topo
    cons --> rotear
    cons --> ciclo
    cons --> repo
    cons --> portas
    cons --> topo
    comp --> motor
    comp --> postgis & redis & cb & maps & local & tri & chpg
    motor -. implementa .-> rotear
    motor --> estr
    motor --> portas
    postgis -. implementa .-> portas
    redis -. implementa .-> portas
    cb -. implementa .-> portas
    cb --> maps
    maps -. implementa .-> portas
    local -. implementa .-> portas
    tri -. implementa .-> portas
    chpg -. implementa .-> repo
    chpg --> ciclo
```

| Componente | Arquivo | Padrão |
|---|---|---|
| `RecepcaoDeChamadosAPI` | [`apresentacao/api.py`](../src/sysop_squad/apresentacao/api.py) | ACL de entrada (Adapter) |
| `ConsumidorDeChamadosAMQP` | [`apresentacao/consumidor.py`](../src/sysop_squad/apresentacao/consumidor.py) | Retry exponencial + fallback |
| `ComposicaoDeDependencias` | [`apresentacao/composicao.py`](../src/sysop_squad/apresentacao/composicao.py) | Factory Method parametrizado |
| `CicloDeVidaDoChamado` | [`chamados/ciclo_de_vida.py`](../src/sysop_squad/chamados/ciclo_de_vida.py) | State |
| `MotorDeRoteamento` | [`dominio/motor.py`](../src/sysop_squad/dominio/motor.py) | DIP (recebe portas e estratégia) |
| `MenorTempoDeDeslocamento` | [`dominio/estrategias.py`](../src/sysop_squad/dominio/estrategias.py) | Strategy |
| Adaptadores | [`infra/`](../src/sysop_squad/infra) | Adapter |
| `CircuitBreakerDeRotas` | [`infra/circuit_breaker.py`](../src/sysop_squad/infra/circuit_breaker.py) | Proxy + Circuit Breaker |
