import os
import re

import psycopg
from dotenv import load_dotenv

load_dotenv()


def obter_conexao():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def testar_conexao():
    try:
        with obter_conexao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()

        return True, "Sistema conectado e pronto para uso."

    except psycopg.Error:
        return False, "Não foi possível conectar ao banco de dados. Tente novamente."


def listar_cursos():
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, codigo, nome
                FROM curso
                ORDER BY nome;
            """)
            return cursor.fetchall()


def listar_matrizes_por_curso(curso_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, curso_id, codigo
                FROM matriz
                WHERE curso_id = %s
                ORDER BY codigo;
            """, (curso_id,))
            return cursor.fetchall()


def listar_matrizes():
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT m.id, m.codigo, c.codigo, c.nome
                FROM matriz m
                JOIN curso c ON c.id = m.curso_id
                ORDER BY c.nome, m.codigo;
            """)
            return cursor.fetchall()


def listar_disciplinas_por_matriz(matriz_id):
    if matriz_id is None:
        return []
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, codigo, nome, carga_horaria, periodo
                FROM disciplina
                WHERE matriz_id = %s
                ORDER BY periodo, nome, codigo;
            """, (matriz_id,))
            return cursor.fetchall()


def criar_disciplina(codigo, nome, carga_horaria, periodo, matriz_id):
    codigo = (codigo or "").strip()
    nome = (nome or "").strip()
    if not codigo:
        raise ValueError("O código da disciplina é obrigatório.")
    if not nome:
        raise ValueError("O nome da disciplina é obrigatório.")
    try:
        carga_horaria = int(carga_horaria)
    except (TypeError, ValueError):
        raise ValueError("Informe uma carga horária inteira maior que zero.") from None
    if carga_horaria <= 0:
        raise ValueError("Informe uma carga horária inteira maior que zero.")
    try:
        periodo = int(periodo)
    except (TypeError, ValueError):
        raise ValueError("Informe um período inteiro maior que zero.") from None
    if periodo <= 0:
        raise ValueError("Informe um período inteiro maior que zero.")
    if matriz_id is None:
        raise ValueError("Selecione uma matriz curricular.")
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO disciplina (matriz_id, codigo, nome, carga_horaria, periodo)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (matriz_id, codigo, nome, carga_horaria, periodo))
            return cursor.fetchone()[0]


def listar_disciplinas():
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT d.id, d.codigo, d.nome, m.codigo, c.nome
                FROM disciplina d
                JOIN matriz m ON m.id = d.matriz_id
                JOIN curso c ON c.id = m.curso_id
                ORDER BY c.nome, m.codigo, d.nome, d.codigo;
            """)
            return cursor.fetchall()


def obter_plano_ensino(disciplina_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, disciplina_id, ementa, conteudo_programatico,
                       objetivos, bibliografia
                FROM plano_ensino
                WHERE disciplina_id = %s;
            """, (disciplina_id,))
            return cursor.fetchone()


def salvar_plano_ensino(
    disciplina_id, ementa, conteudo_programatico, objetivos="", bibliografia=""
):
    if disciplina_id is None:
        raise ValueError("Selecione uma disciplina.")
    ementa = (ementa or "").strip()
    conteudo_programatico = (conteudo_programatico or "").strip()
    objetivos = (objetivos or "").strip() or None
    bibliografia = (bibliografia or "").strip() or None
    if not ementa:
        raise ValueError("A ementa é obrigatória.")
    if not conteudo_programatico:
        raise ValueError("O conteúdo programático é obrigatório.")
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO plano_ensino (
                    disciplina_id, ementa, conteudo_programatico, objetivos, bibliografia
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (disciplina_id) DO UPDATE SET
                    ementa = EXCLUDED.ementa,
                    conteudo_programatico = EXCLUDED.conteudo_programatico,
                    objetivos = EXCLUDED.objetivos,
                    bibliografia = EXCLUDED.bibliografia,
                    atualizado_em = CURRENT_TIMESTAMP
                RETURNING id;
            """, (
                disciplina_id, ementa, conteudo_programatico, objetivos, bibliografia
            ))
            return cursor.fetchone()[0]


def _normalizar_dados_aluno(nome, ra):
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("O nome do aluno é obrigatório.")
    ra = (ra or "").strip() or None
    return nome, ra


def criar_aluno(nome, ra=None, unidade_id=None):
    nome, ra = _normalizar_dados_aluno(nome, ra)
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            if unidade_id is None:
                cursor.execute(
                    "INSERT INTO aluno (nome, ra) VALUES (%s, %s) RETURNING id;",
                    (nome, ra),
                )
            else:
                cursor.execute(
                    "INSERT INTO aluno (nome, ra, unidade_id) VALUES (%s, %s, %s) RETURNING id;",
                    (nome, ra, unidade_id),
                )
            return cursor.fetchone()[0]


def atualizar_aluno(aluno_id, nome, ra=None):
    nome, ra = _normalizar_dados_aluno(nome, ra)
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                "UPDATE aluno SET nome = %s, ra = %s WHERE id = %s RETURNING id;",
                (nome, ra, aluno_id),
            )
            return cursor.fetchone() is not None


def obter_aluno(aluno_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT id, nome, ra FROM aluno WHERE id = %s;", (aluno_id,))
            return cursor.fetchone()


def listar_alunos():
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT id, nome, ra FROM aluno ORDER BY nome, id;")
            return cursor.fetchall()


def buscar_alunos_por_nome(termo):
    termo = (termo or "").strip()
    if not termo:
        return []
    # Trata curingas do LIKE como texto digitado, mantendo a busca por substring.
    termo = termo.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, nome, ra
                FROM aluno
                WHERE nome ILIKE %s ESCAPE '!'
                ORDER BY nome, id;
            """, (f"%{termo}%",))
            return cursor.fetchall()


def normalizar_semestre_ano_ingresso(valor):
    valor = (valor or "").strip()
    if valor and re.fullmatch(r"[12]/[0-9]{4}", valor) is None:
        raise ValueError(
            "Informe o Semestre/Ano de ingresso no formato 1/2027 ou 2/2027 "
            "(semestre 1 ou 2 e ano com quatro dígitos)."
        )
    return valor


def criar_analise(aluno_id, semestre_ano=""):
    semestre_ano = normalizar_semestre_ano_ingresso(semestre_ano)
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO analise (
                    aluno_id,
                    semestre_ano
                )
                VALUES (%s, %s)
                RETURNING id;
            """, (
                aluno_id,
                semestre_ano
            ))

            return cursor.fetchone()[0]


def criar_analise_com_historico(
    aluno_id, semestre_ano, nome_arquivo, conteudo, planos_origem=()
):
    semestre_ano = normalizar_semestre_ano_ingresso(semestre_ano)
    if not nome_arquivo or not conteudo:
        raise ValueError("Anexe o histórico acadêmico para iniciar a análise.")
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO analise (aluno_id, semestre_ano)
                VALUES (%s, %s)
                RETURNING id;
            """, (aluno_id, semestre_ano))
            analise_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO documento (analise_id, tipo, nome_arquivo, conteudo)
                VALUES (%s, 'historico', %s, %s);
            """, (analise_id, nome_arquivo, conteudo))
            if planos_origem:
                cursor.executemany("""
                    INSERT INTO documento (analise_id, tipo, nome_arquivo, conteudo)
                    VALUES (%s, 'plano_ensino_origem', %s, %s);
                """, [
                    (analise_id, plano_nome, plano_conteudo)
                    for plano_nome, plano_conteudo in planos_origem
                ])
            return analise_id


def obter_historico(analise_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, nome_arquivo, data_envio, octet_length(conteudo)
                FROM documento
                WHERE analise_id = %s AND tipo = 'historico';
            """, (analise_id,))
            return cursor.fetchone()


def obter_conteudo_historico(analise_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, nome_arquivo, conteudo
                FROM documento
                WHERE analise_id = %s AND tipo = 'historico';
            """, (analise_id,))
            return cursor.fetchone()


def salvar_extracao_historico(analise_id, documento_id, disciplinas, aviso=None):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("DELETE FROM extracao_historico WHERE analise_id = %s;", (analise_id,))
            cursor.execute("""
                INSERT INTO extracao_historico (analise_id, documento_id, aviso)
                VALUES (%s, %s, %s)
                RETURNING id;
            """, (analise_id, documento_id, aviso))
            extracao_id = cursor.fetchone()[0]
            if disciplinas:
                cursor.executemany("""
                    INSERT INTO disciplina_extraida (
                        extracao_id, codigo, nome, nota, carga_horaria,
                        periodo, situacao, texto_origem
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, [
                    (
                        extracao_id,
                        disciplina.get("codigo"),
                        disciplina.get("nome"),
                        disciplina.get("nota"),
                        disciplina.get("carga_horaria"),
                        disciplina.get("periodo"),
                        disciplina.get("situacao"),
                        disciplina.get("texto_origem") or "",
                    )
                    for disciplina in disciplinas
                ])
            return extracao_id


def salvar_revisao_disciplinas(analise_id, alteracoes, confirmar=False):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM extracao_historico WHERE analise_id = %s;",
                (analise_id,),
            )
            extracao = cursor.fetchone()
            if extracao is None:
                return False
            extracao_id = extracao[0]
            for item in alteracoes:
                cursor.execute("""
                    UPDATE disciplina_extraida
                    SET codigo = %s, nome = %s, nota = %s, carga_horaria = %s,
                        periodo = %s, situacao = %s, revisado = FALSE
                    WHERE id = %s AND extracao_id = %s;
                """, (
                    (item.get("Código") or "").strip() or None,
                    (item.get("Disciplina") or "").strip() or None,
                    (item.get("Nota") or "").strip() or None,
                    (item.get("Carga horária") or "").strip() or None,
                    (item.get("Ano/semestre") or "").strip() or None,
                    (item.get("Situação") or "").strip() or None,
                    item["ID"],
                    extracao_id,
                ))
                if cursor.rowcount != 1:
                    raise ValueError("Uma disciplina deixou de pertencer a esta extração. Recarregue a página.")
            if confirmar:
                if not alteracoes:
                    raise ValueError("Não há disciplinas para confirmar.")
                cursor.execute(
                    "UPDATE disciplina_extraida SET revisado = TRUE WHERE extracao_id = %s;",
                    (extracao_id,),
                )
                cursor.execute("""
                    UPDATE extracao_historico
                    SET confirmado_em = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (extracao_id,))
            else:
                cursor.execute("""
                    UPDATE extracao_historico
                    SET confirmado_em = NULL
                    WHERE id = %s;
                """, (extracao_id,))
            return True


def obter_extracao_historico(analise_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, documento_id, processado_em, aviso, confirmado_em
                FROM extracao_historico
                WHERE analise_id = %s;
            """, (analise_id,))
            extracao = cursor.fetchone()
            if extracao is None:
                return None, []
            cursor.execute("""
                SELECT id, codigo, nome, nota, carga_horaria, periodo,
                       situacao, texto_origem, revisado
                FROM disciplina_extraida
                WHERE extracao_id = %s
                ORDER BY id;
            """, (extracao[0],))
            return extracao, cursor.fetchall()


def listar_disciplinas_elegiveis_para_aproveitamento(analise_id):
    """Retorna apenas disciplinas confirmadas com situação explicitamente aprovada."""
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT d.id, d.codigo, d.nome, d.nota, d.carga_horaria,
                       d.periodo, d.situacao
                FROM extracao_historico e
                JOIN disciplina_extraida d ON d.extracao_id = e.id
                WHERE e.analise_id = %s
                  AND e.confirmado_em IS NOT NULL
                  AND d.revisado = TRUE
                  AND LEFT(LOWER(BTRIM(COALESCE(d.situacao, ''))), 7) = 'aprovad'
                ORDER BY d.id;
            """, (analise_id,))
            return cursor.fetchall()


def listar_planos_origem(analise_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                SELECT id, nome_arquivo, data_envio, octet_length(conteudo)
                FROM documento
                WHERE analise_id = %s AND tipo = 'plano_ensino_origem'
                ORDER BY data_envio, id;
            """, (analise_id,))
            return cursor.fetchall()


def salvar_planos_origem(analise_id, arquivos):
    if not analise_id:
        raise ValueError("Salve a análise antes de anexar os planos.")
    if not arquivos:
        return 0
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO documento (analise_id, tipo, nome_arquivo, conteudo)
                VALUES (%s, 'plano_ensino_origem', %s, %s);
            """, [
                (analise_id, nome_arquivo, conteudo)
                for nome_arquivo, conteudo in arquivos
            ])
            return len(arquivos)


def remover_plano_origem(analise_id, documento_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                DELETE FROM documento
                WHERE id = %s AND analise_id = %s AND tipo = 'plano_ensino_origem'
                RETURNING id;
            """, (documento_id, analise_id))
            return cursor.fetchone() is not None


def salvar_historico(analise_id, nome_arquivo, conteudo):
    if not analise_id:
        raise ValueError("Salve a análise antes de anexar o histórico.")
    if not nome_arquivo or not conteudo:
        raise ValueError("Anexe o histórico acadêmico.")
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                INSERT INTO documento (analise_id, tipo, nome_arquivo, conteudo)
                VALUES (%s, 'historico', %s, %s)
                RETURNING id;
            """, (analise_id, nome_arquivo, conteudo))
            return cursor.fetchone()[0]


# Mantém os índices usados pelas páginas anteriores e acrescenta dados de origem.
_SELECT_ANALISE = """
    SELECT a.id, al.nome, al.ra, a.semestre_ano, a.situacao_origem,
           a.procedencia, a.data_criacao, a.curso_id, a.matriz_id, a.aluno_id,
           a.curso_origem
    FROM analise a
    JOIN aluno al ON al.id = a.aluno_id
"""


def listar_analises():
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(_SELECT_ANALISE + " ORDER BY a.data_criacao DESC, a.id DESC;")

            return cursor.fetchall()


def obter_analise(analise_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(_SELECT_ANALISE + " WHERE a.id = %s;", (analise_id,))

            return cursor.fetchone()


def atualizar_analise(analise_id, semestre_ano):
    semestre_ano = normalizar_semestre_ano_ingresso(semestre_ano)
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                UPDATE analise
                SET semestre_ano = %s
                WHERE id = %s RETURNING id;
            """, (
                semestre_ano,
                analise_id
            ))
            return cursor.fetchone() is not None


def salvar_origem_aproveitamento(
    analise_id,
    curso_origem,
    situacao_origem,
    procedencia
):
    curso_origem = (curso_origem or "").strip() or None
    situacao_origem = (situacao_origem or "").strip() or None
    procedencia = (procedencia or "").strip() or None
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                UPDATE analise
                SET curso_origem = %s,
                    situacao_origem = %s,
                    procedencia = %s
                WHERE id = %s RETURNING id;
            """, (
                curso_origem,
                situacao_origem,
                procedencia,
                analise_id
            ))
            return cursor.fetchone() is not None


def salvar_curso_e_matriz(analise_id, curso_id, matriz_id):
    with obter_conexao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("""
                UPDATE analise
                SET
                    curso_id = %s,
                    matriz_id = %s
                WHERE id = %s RETURNING id;
            """, (
                curso_id,
                matriz_id,
                analise_id
            ))
            return cursor.fetchone() is not None
