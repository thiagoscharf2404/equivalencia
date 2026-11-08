-- Execute depois da criação do schema e das migrações existentes.
CREATE TABLE IF NOT EXISTS unidade (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL UNIQUE CHECK (nome ~ '[^[:space:]]'),
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO unidade (nome)
SELECT 'Unidade principal'
WHERE NOT EXISTS (SELECT 1 FROM unidade);

CREATE TABLE IF NOT EXISTS coordenador (
    id SERIAL PRIMARY KEY,
    unidade_id INTEGER NOT NULL REFERENCES unidade(id),
    nome VARCHAR(150) NOT NULL CHECK (nome ~ '[^[:space:]]'),
    email VARCHAR(254) NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil VARCHAR(30) NOT NULL DEFAULT 'coordenador'
        CHECK (perfil IN ('coordenador', 'administrador')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_coordenador_unidade_email UNIQUE (unidade_id, email)
);

CREATE INDEX IF NOT EXISTS idx_coordenador_email ON coordenador (lower(email));
CREATE UNIQUE INDEX IF NOT EXISTS uq_coordenador_unidade_email_casefold
    ON coordenador (unidade_id, lower(email));

-- Dados já existentes ficam sob a unidade principal; novas gravações recebem
-- a unidade escolhida pelo coordenador autenticado.
ALTER TABLE curso ADD COLUMN IF NOT EXISTS unidade_id INTEGER REFERENCES unidade(id);
ALTER TABLE aluno ADD COLUMN IF NOT EXISTS unidade_id INTEGER REFERENCES unidade(id);
ALTER TABLE analise ADD COLUMN IF NOT EXISTS unidade_id INTEGER REFERENCES unidade(id);
UPDATE curso SET unidade_id = (SELECT id FROM unidade ORDER BY id LIMIT 1) WHERE unidade_id IS NULL;
UPDATE aluno SET unidade_id = (SELECT id FROM unidade ORDER BY id LIMIT 1) WHERE unidade_id IS NULL;
UPDATE analise SET unidade_id = (SELECT id FROM unidade ORDER BY id LIMIT 1) WHERE unidade_id IS NULL;
ALTER TABLE curso ALTER COLUMN unidade_id SET NOT NULL;
ALTER TABLE aluno ALTER COLUMN unidade_id SET NOT NULL;
ALTER TABLE analise ALTER COLUMN unidade_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_curso_unidade ON curso (unidade_id);
CREATE INDEX IF NOT EXISTS idx_aluno_unidade ON aluno (unidade_id);
CREATE INDEX IF NOT EXISTS idx_analise_unidade ON analise (unidade_id);
