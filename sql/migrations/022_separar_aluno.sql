-- Executar uma única vez sobre o schema do card #021, com a aplicação parada.
-- Não unifica pessoas por nome/RA: cada análise antiga recebe um aluno.
BEGIN;

LOCK TABLE analise IN ACCESS EXCLUSIVE MODE;

CREATE TABLE aluno (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL CONSTRAINT ck_aluno_nome CHECK (nome ~ '[^[:space:]]'),
    ra VARCHAR(30),
    CONSTRAINT ck_aluno_ra CHECK (ra IS NULL OR ra ~ '[^[:space:]]')
);

ALTER TABLE analise ADD COLUMN aluno_id INTEGER REFERENCES aluno(id);

DO $$
DECLARE
    registro RECORD;
    novo_aluno_id INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM analise WHERE nome_aluno IS NULL
               OR nome_aluno !~ '[^[:space:]]') THEN
        RAISE EXCEPTION 'Existem análises sem nome válido. Corrija os nomes antes de migrar.';
    END IF;

    FOR registro IN SELECT id, nome_aluno, ra FROM analise ORDER BY id LOOP
        INSERT INTO aluno (nome, ra)
        VALUES (registro.nome_aluno,
                CASE WHEN registro.ra ~ '[^[:space:]]' THEN registro.ra ELSE NULL END)
        RETURNING id INTO novo_aluno_id;

        UPDATE analise SET aluno_id = novo_aluno_id WHERE id = registro.id;
    END LOOP;
END $$;

ALTER TABLE analise ALTER COLUMN aluno_id SET NOT NULL;
CREATE INDEX idx_analise_aluno_id ON analise (aluno_id);

-- Os valores já estão na tabela aluno; os demais dados da análise são mantidos.
ALTER TABLE analise DROP COLUMN nome_aluno, DROP COLUMN ra;

COMMIT;
