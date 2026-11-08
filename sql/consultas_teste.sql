SELECT * FROM curso;

SELECT
    curso.nome AS curso,
    matriz.codigo AS matriz
FROM matriz
JOIN curso ON curso.id = matriz.curso_id
ORDER BY curso.nome, matriz.codigo;