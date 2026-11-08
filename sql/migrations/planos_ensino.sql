-- Adiciona cadastro persistente de planos de ensino, um por disciplina.
BEGIN;

CREATE TABLE IF NOT EXISTS plano_ensino (
    id SERIAL PRIMARY KEY,
    disciplina_id INTEGER NOT NULL UNIQUE REFERENCES disciplina(id),
    ementa TEXT NOT NULL CONSTRAINT ck_plano_ensino_ementa CHECK (ementa ~ '[^[:space:]]'),
    conteudo_programatico TEXT NOT NULL CONSTRAINT ck_plano_ensino_conteudo CHECK (conteudo_programatico ~ '[^[:space:]]'),
    objetivos TEXT,
    bibliografia TEXT,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
