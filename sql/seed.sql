INSERT INTO curso (codigo, nome)
VALUES
('61385', 'Análise e Desenvolvimento de Sistemas'),
('61927', 'Engenharia de Software');

INSERT INTO matriz (curso_id, codigo)
VALUES
(
    (SELECT id FROM curso WHERE codigo = '61385'),
    '2024/1'
),
(
    (SELECT id FROM curso WHERE codigo = '61385'),
    '2024/2'
),
(
    (SELECT id FROM curso WHERE codigo = '61927'),
    '2025/1'
),
(
    (SELECT id FROM curso WHERE codigo = '61927'),
    '2025/2'
);