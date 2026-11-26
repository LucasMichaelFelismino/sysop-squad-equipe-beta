-- Esquema usado pelos adaptadores PostgreSQL/PostGIS (ADR 003 da Sprint 1 e ADR 006 da Sprint 3).
-- Cada módulo escreve só nas próprias tabelas (soberania dos dados).

CREATE EXTENSION IF NOT EXISTS postgis;

-- Módulo Disponibilidade de Consultores (lido pelo Roteamento).
CREATE TABLE IF NOT EXISTS consultores (
    id          text PRIMARY KEY,
    nome        text NOT NULL,
    ativo       boolean NOT NULL DEFAULT true,
    habilidades text[] NOT NULL DEFAULT '{}',
    posicao     geography(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS consultores_posicao_idx ON consultores USING gist (posicao);
CREATE INDEX IF NOT EXISTS consultores_habilidades_idx ON consultores USING gin (habilidades);

-- Módulo Gestão de Chamados (ciclo de vida - padrão State).
CREATE TABLE IF NOT EXISTS chamados (
    id            text PRIMARY KEY,
    id_externo    text NOT NULL UNIQUE,          -- idempotência do POST /chamados (HTTP 409)
    estado        text NOT NULL,
    consultor_id  text,
    dados         jsonb NOT NULL,
    historico     jsonb NOT NULL DEFAULT '[]',
    criado_em     timestamptz NOT NULL DEFAULT now(),
    atualizado_em timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chamados_estado_idx ON chamados (estado);
