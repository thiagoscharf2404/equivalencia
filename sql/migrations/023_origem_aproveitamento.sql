-- Executar uma única vez em bancos que já usam o schema anterior.
-- Origem do aproveitamento pertence à análise, não ao cadastro do aluno.
BEGIN;

ALTER TABLE analise
    ADD COLUMN curso_origem VARCHAR(150);

ALTER TABLE analise
    RENAME COLUMN situacao TO situacao_origem;

COMMIT;
