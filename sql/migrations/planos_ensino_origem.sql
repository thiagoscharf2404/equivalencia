-- Permite vários planos de ensino de origem por análise, preservando um histórico por análise.
BEGIN;

ALTER TABLE documento DROP CONSTRAINT IF EXISTS documento_tipo_check;
ALTER TABLE documento DROP CONSTRAINT IF EXISTS ck_documento_tipo;
ALTER TABLE documento
    ADD CONSTRAINT ck_documento_tipo
    CHECK (tipo IN ('historico', 'plano_ensino_origem'));

ALTER TABLE documento DROP CONSTRAINT IF EXISTS documento_analise_id_tipo_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_documento_historico
    ON documento (analise_id) WHERE tipo = 'historico';

COMMIT;
