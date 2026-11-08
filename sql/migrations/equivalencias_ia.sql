CREATE TABLE IF NOT EXISTS equivalencia_sugestao (
    id BIGSERIAL PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analise(id) ON DELETE CASCADE,
    discipline_extra_id INTEGER NOT NULL REFERENCES disciplina_extraida(id) ON DELETE CASCADE,
    target_discipline_id INTEGER NOT NULL REFERENCES disciplina(id),
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    rationale TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision VARCHAR(16) NOT NULL DEFAULT 'pending'
        CHECK (decision IN ('pending', 'approved', 'rejected', 'edited')),
        
    coordinator_note TEXT NOT NULL DEFAULT '',
    provider VARCHAR(80),
    model VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    UNIQUE (analysis_id, discipline_extra_id, target_discipline_id)
);

CREATE INDEX IF NOT EXISTS idx_equivalencia_sugestao_analysis
    ON equivalencia_sugestao (analysis_id, decision);
