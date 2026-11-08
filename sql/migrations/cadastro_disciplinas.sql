-- Migra a tabela disciplina existente para as regras atuais do sistema.
-- Executar uma única vez em bancos que já possuem a tabela disciplina.
BEGIN;

ALTER TABLE disciplina
    ALTER COLUMN matriz_id SET NOT NULL,
    ALTER COLUMN codigo SET NOT NULL,
    ALTER COLUMN nome SET NOT NULL,
    ALTER COLUMN carga_horaria SET NOT NULL,
    ALTER COLUMN periodo SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.disciplina'::regclass
          AND contype = 'f'
          AND confrelid = 'public.matriz'::regclass
          AND conkey = ARRAY[(
              SELECT attnum FROM pg_attribute
              WHERE attrelid = 'public.disciplina'::regclass
                AND attname = 'matriz_id'
          )]::smallint[]
    ) THEN
        ALTER TABLE disciplina
            ADD CONSTRAINT fk_disciplina_matriz
            FOREIGN KEY (matriz_id) REFERENCES matriz(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.disciplina'::regclass
          AND conname = 'ck_disciplina_codigo'
    ) THEN
        ALTER TABLE disciplina
            ADD CONSTRAINT ck_disciplina_codigo CHECK (codigo ~ '[^[:space:]]');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.disciplina'::regclass
          AND conname = 'ck_disciplina_nome'
    ) THEN
        ALTER TABLE disciplina
            ADD CONSTRAINT ck_disciplina_nome CHECK (nome ~ '[^[:space:]]');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.disciplina'::regclass
          AND conname = 'ck_disciplina_carga_horaria'
    ) THEN
        ALTER TABLE disciplina
            ADD CONSTRAINT ck_disciplina_carga_horaria CHECK (carga_horaria > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.disciplina'::regclass
          AND conname = 'ck_disciplina_periodo'
    ) THEN
        ALTER TABLE disciplina
            ADD CONSTRAINT ck_disciplina_periodo CHECK (periodo > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.disciplina'::regclass
          AND conname = 'uq_disciplina_matriz_codigo'
    ) THEN
        ALTER TABLE disciplina
            ADD CONSTRAINT uq_disciplina_matriz_codigo UNIQUE (matriz_id, codigo);
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_disciplina_matriz_id ON disciplina (matriz_id);

COMMIT;
