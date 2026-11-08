CREATE TABLE unidade (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL UNIQUE CHECK (nome ~ '[^[:space:]]'),
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    criada_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO unidade (nome) VALUES ('Unidade principal');

CREATE TABLE coordenador (
    id SERIAL PRIMARY KEY,
    unidade_id INTEGER NOT NULL REFERENCES unidade(id),
    nome VARCHAR(150) NOT NULL CHECK (nome ~ '[^[:space:]]'),
    email VARCHAR(254) NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil VARCHAR(30) NOT NULL DEFAULT 'coordenador' CHECK (perfil IN ('coordenador', 'administrador')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_coordenador_unidade_email UNIQUE (unidade_id, email)
);

CREATE TABLE curso (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(150) NOT NULL,
    unidade_id INTEGER NOT NULL REFERENCES unidade(id) DEFAULT 1
);

CREATE TABLE matriz (
    id SERIAL PRIMARY KEY,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    codigo VARCHAR(10) NOT NULL,
    UNIQUE (curso_id, codigo)
);

CREATE TABLE disciplina (
    id SERIAL PRIMARY KEY,
    matriz_id INTEGER NOT NULL REFERENCES matriz(id),
    codigo VARCHAR(30) NOT NULL CONSTRAINT ck_disciplina_codigo CHECK (codigo ~ '[^[:space:]]'),
    nome VARCHAR(200) NOT NULL CONSTRAINT ck_disciplina_nome CHECK (nome ~ '[^[:space:]]'),
    carga_horaria INTEGER NOT NULL CONSTRAINT ck_disciplina_carga_horaria CHECK (carga_horaria > 0),
    periodo INTEGER NOT NULL CONSTRAINT ck_disciplina_periodo CHECK (periodo > 0),
    CONSTRAINT uq_disciplina_matriz_codigo UNIQUE (matriz_id, codigo)
);

CREATE INDEX idx_disciplina_matriz_id ON disciplina (matriz_id);

CREATE TABLE plano_ensino (
    id SERIAL PRIMARY KEY,
    disciplina_id INTEGER NOT NULL UNIQUE REFERENCES disciplina(id),
    ementa TEXT NOT NULL CONSTRAINT ck_plano_ensino_ementa CHECK (ementa ~ '[^[:space:]]'),
    conteudo_programatico TEXT NOT NULL CONSTRAINT ck_plano_ensino_conteudo CHECK (conteudo_programatico ~ '[^[:space:]]'),
    objetivos TEXT,
    bibliografia TEXT,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE aluno (
    id SERIAL PRIMARY KEY,
    unidade_id INTEGER NOT NULL REFERENCES unidade(id) DEFAULT 1,
    nome VARCHAR(150) NOT NULL CONSTRAINT ck_aluno_nome CHECK (nome ~ '[^[:space:]]'),
    ra VARCHAR(30),
    CONSTRAINT ck_aluno_ra CHECK (ra IS NULL OR ra ~ '[^[:space:]]')
);

CREATE TABLE analise (
    id SERIAL PRIMARY KEY,
    unidade_id INTEGER NOT NULL REFERENCES unidade(id) DEFAULT 1,
    aluno_id INTEGER NOT NULL REFERENCES aluno(id),
    semestre_ano VARCHAR(20),
    curso_origem VARCHAR(150),
    situacao_origem VARCHAR(100),
    procedencia VARCHAR(150),
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE matriz
ADD CONSTRAINT uq_matriz_curso_id UNIQUE (curso_id, id);

ALTER TABLE analise
ADD COLUMN curso_id INTEGER,
ADD COLUMN matriz_id INTEGER;

ALTER TABLE analise
ADD CONSTRAINT fk_analise_curso
FOREIGN KEY (curso_id)
REFERENCES curso(id);

ALTER TABLE analise
ADD CONSTRAINT fk_analise_matriz_do_curso
FOREIGN KEY (curso_id, matriz_id)
REFERENCES matriz(curso_id, id);

ALTER TABLE analise
ADD CONSTRAINT ck_analise_curso_matriz
CHECK (
    (curso_id IS NULL AND matriz_id IS NULL)
    OR
    (curso_id IS NOT NULL AND matriz_id IS NOT NULL)
);

CREATE INDEX idx_analise_aluno_id ON analise (aluno_id);

CREATE TABLE documento (
    id SERIAL PRIMARY KEY,
    analise_id INTEGER NOT NULL REFERENCES analise(id),
    tipo VARCHAR(30) NOT NULL CONSTRAINT ck_documento_tipo
        CHECK (tipo IN ('historico', 'plano_ensino_origem')),
    nome_arquivo TEXT NOT NULL CHECK (nome_arquivo ~ '[^[:space:]]'),
    conteudo BYTEA NOT NULL,
    data_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX uq_documento_historico ON documento (analise_id) WHERE tipo = 'historico';
CREATE INDEX idx_documento_analise_id ON documento (analise_id);

CREATE TABLE extracao_historico (
    id SERIAL PRIMARY KEY,
    analise_id INTEGER NOT NULL UNIQUE REFERENCES analise(id) ON DELETE CASCADE,
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    aviso TEXT,
    confirmado_em TIMESTAMP
);

CREATE TABLE disciplina_extraida (
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

CREATE INDEX idx_disciplina_extraida_extracao ON disciplina_extraida (extracao_id);
