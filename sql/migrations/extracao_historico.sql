-- Guarda cada execução de extração e as disciplinas identificadas para revisão.
BEGIN;

CREATE TABLE IF NOT EXISTS extracao_historico (
    id SERIAL PRIMARY KEY,
    analise_id INTEGER NOT NULL UNIQUE REFERENCES analise(id) ON DELETE CASCADE,
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aviso TEXT,
    confirmado_em TIMESTAMP
);

ALTER TABLE extracao_historico
    ADD COLUMN IF NOT EXISTS confirmado_em TIMESTAMP;

CREATE TABLE IF NOT EXISTS disciplina_extraida (
    id SERIAL PRIMARY KEY,
    extracao_id INTEGER NOT NULL REFERENCES extracao_historico(id) ON DELETE CASCADE,
    codigo TEXT,
    nome TEXT,
    nota TEXT,
    carga_horaria TEXT,
    periodo TEXT,
    situacao TEXT,
    texto_origem TEXT NOT NULL,
    revisado BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_disciplina_extraida_extracao
    ON disciplina_extraida (extracao_id);

COMMIT;
