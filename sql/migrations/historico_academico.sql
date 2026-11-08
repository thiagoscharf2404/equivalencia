-- Armazena o arquivo original do histórico junto à análise correspondente.
BEGIN;

CREATE TABLE IF NOT EXISTS documento (
    id SERIAL PRIMARY KEY,
    analise_id INTEGER NOT NULL REFERENCES analise(id),
    tipo VARCHAR(30) NOT NULL CONSTRAINT ck_documento_tipo
        CHECK (tipo IN ('historico', 'plano_ensino_origem')),
    nome_arquivo TEXT NOT NULL CHECK (nome_arquivo ~ '[^[:space:]]'),
    conteudo BYTEA NOT NULL,
    data_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documento_historico ON documento (analise_id) WHERE tipo = 'historico';
CREATE INDEX IF NOT EXISTS idx_documento_analise_id ON documento (analise_id);

COMMIT;
