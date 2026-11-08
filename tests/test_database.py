"""Integração opt-in: TEST_POSTGRES=1 usa o .env em schema isolado e faz rollback."""

from contextlib import contextmanager
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql

import database


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "sql/schema.sql").read_text(encoding="utf-8")
MIGRACAO = (ROOT / "sql/migrations/022_separar_aluno.sql").read_text(encoding="utf-8")
# A transação externa do teste substitui BEGIN/COMMIT do script de produção.
MIGRACAO_TESTE = "\n".join(
    linha for linha in MIGRACAO.splitlines() if linha.strip() not in ("BEGIN;", "COMMIT;")
)
MIGRACAO_ORIGEM = (ROOT / "sql/migrations/023_origem_aproveitamento.sql").read_text(encoding="utf-8")
MIGRACAO_ORIGEM_TESTE = "\n".join(
    linha for linha in MIGRACAO_ORIGEM.splitlines()
    if linha.strip() not in ("BEGIN;", "COMMIT;")
)

SCHEMA_021 = """
CREATE TABLE curso (id SERIAL PRIMARY KEY, codigo VARCHAR(10) UNIQUE NOT NULL,
                    nome VARCHAR(150) NOT NULL);
CREATE TABLE matriz (id SERIAL PRIMARY KEY, curso_id INTEGER NOT NULL REFERENCES curso(id),
                     codigo VARCHAR(10) NOT NULL, UNIQUE(curso_id, codigo), UNIQUE(curso_id, id));
CREATE TABLE analise (
    id SERIAL PRIMARY KEY, nome_aluno VARCHAR(150) NOT NULL, ra VARCHAR(30),
    semestre_ano VARCHAR(20), situacao VARCHAR(100), procedencia VARCHAR(150),
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    curso_id INTEGER REFERENCES curso(id), matriz_id INTEGER,
    FOREIGN KEY(curso_id, matriz_id) REFERENCES matriz(curso_id, id),
    CHECK ((curso_id IS NULL AND matriz_id IS NULL)
           OR (curso_id IS NOT NULL AND matriz_id IS NOT NULL))
);
"""


class ValidacaoIngressoTest(unittest.TestCase):
    def test_formato_invalido_nao_acessa_banco(self):
        with patch("database.obter_conexao") as conexao:
            for valor in ("0/2027", "3/2027", "2027/1", "01/2027", "1/27",
                          "2/20270", "1-2027", "1/abcd", "1/２０２７", "x" * 21):
                for operacao in (database.criar_analise, database.atualizar_analise):
                    with self.subTest(valor=valor, operacao=operacao.__name__):
                        with self.assertRaisesRegex(ValueError, "1/2027 ou 2/2027"):
                            operacao(1, valor)
            conexao.assert_not_called()

    def test_formatos_validos_e_campo_opcional(self):
        for valor, esperado in (("1/2027", "1/2027"), (" 2/2027 ", "2/2027"),
                                (None, ""), ("", ""), ("   ", "")):
            with self.subTest(valor=valor):
                self.assertEqual(database.normalizar_semestre_ano_ingresso(valor), esperado)


class ValidacaoAlunoTest(unittest.TestCase):
    def test_erro_conexao_nao_expoe_detalhes(self):
        with patch("database.obter_conexao", side_effect=psycopg.OperationalError("password=SEGREDO")):
            sucesso, mensagem = database.testar_conexao()
        self.assertFalse(sucesso)
        self.assertNotIn("SEGREDO", mensagem)
        self.assertIn("Tente novamente", mensagem)

    def test_busca_vazia_nao_acessa_banco(self):
        with patch("database.obter_conexao") as conexao:
            for termo in (None, "", " \t\n"):
                self.assertEqual(database.buscar_alunos_por_nome(termo), [])
            conexao.assert_not_called()

    def test_nome_obrigatorio_antes_de_acessar_banco(self):
        with patch("database.obter_conexao") as conexao:
            for nome in (None, "", " \t\n"):
                with self.subTest(nome=nome), self.assertRaises(ValueError):
                    database.criar_aluno(nome)
            conexao.assert_not_called()


@unittest.skipUnless(os.getenv("TEST_POSTGRES") == "1", "Defina TEST_POSTGRES=1 para testar PostgreSQL")
class PostgreSQLTest(unittest.TestCase):
    def setUp(self):
        self.conexao = psycopg.connect(
            host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"), connect_timeout=5,
        )
        self.addCleanup(self.conexao.close)
        self.addCleanup(self.conexao.rollback)
        self.schema = "teste_022_" + uuid4().hex
        self.conexao.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.conexao.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(self.schema)))
        # As funções reais usam savepoints e nunca confirmam a transação externa.
        mock = patch("database.obter_conexao", self.conexao_teste)
        mock.start()
        self.addCleanup(mock.stop)

    @contextmanager
    def conexao_teste(self):
        with self.conexao.transaction():
            yield self.conexao

    def test_alunos_e_multiplas_analises_no_postgresql(self):
        self.conexao.execute(SCHEMA)
        com_ra = database.criar_aluno("  Ana D'Ávila  ", " 123 ")
        sem_ra = database.criar_aluno("Bruno")
        vazio = database.criar_aluno("Carla", "  ")
        self.assertEqual(database.obter_aluno(com_ra), (com_ra, "Ana D'Ávila", "123"))
        self.assertIsNone(database.obter_aluno(sem_ra)[2])
        self.assertIsNone(database.obter_aluno(vazio)[2])
        self.assertIsNone(database.obter_aluno(99999))
        self.assertEqual(len(database.listar_alunos()), 3)

        primeira = database.criar_analise(com_ra, "1/2026")
        database.salvar_origem_aproveitamento(
            primeira, "Engenharia de Software", "Concluído", "Externa"
        )
        segunda = database.criar_analise(com_ra, "2/2026")
        vinculos = self.conexao.execute(
            "SELECT aluno_id, count(*) FROM analise GROUP BY aluno_id"
        ).fetchall()
        self.assertEqual(vinculos, [(com_ra, 2)])
        self.assertEqual(database.obter_analise(primeira)[1:3], ("Ana D'Ávila", "123"))
        self.assertEqual(database.obter_analise(segunda)[9], com_ra)
        self.assertEqual(len(database.listar_analises()), 2)
        database.atualizar_analise(primeira, "1/2027")
        self.assertEqual(database.obter_analise(primeira)[3:6], ("1/2027", "Concluído", "Externa"))
        self.assertEqual(database.obter_analise(primeira)[10], "Engenharia de Software")
        self.assertEqual(database.obter_analise(segunda)[3], "2/2026")
        self.assertEqual(database.obter_aluno(com_ra)[1], "Ana D'Ávila")

        for nome in (None, "", " \t\n"):
            with self.subTest(nome=nome), self.assertRaises(psycopg.IntegrityError):
                with self.conexao.transaction():
                    self.conexao.execute("INSERT INTO aluno (nome) VALUES (%s)", (nome,))
        for aluno_id in (None, 99999):
            with self.subTest(aluno_id=aluno_id), self.assertRaises(psycopg.IntegrityError):
                database.criar_analise(aluno_id)
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.conexao.transaction():
                self.conexao.execute("DELETE FROM aluno WHERE id = %s", (com_ra,))
        colunas = self.conexao.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = 'analise'",
            (self.schema,),
        ).fetchall()
        self.assertNotIn(("nome_aluno",), colunas)
        self.assertNotIn(("ra",), colunas)

    def test_busca_por_nome_no_postgresql(self):
        self.conexao.execute(SCHEMA)
        freitas = database.criar_aluno("Matheus José Freitas", "123")
        pavlak = database.criar_aluno("Matheus Pavlak")
        homonimo = database.criar_aluno("Matheus Pavlak", "456")
        database.criar_aluno("Ana")
        for termo, esperados in (
            ("Matheus José Freitas", [freitas]),
            ("  Freitas  ", [freitas]),
            ("mAtHeUs", [freitas, pavlak, homonimo]),
            ("pav", [pavlak, homonimo]),
            ("Ninguém", []),
            ("' OR 1=1 --", []),
        ):
            with self.subTest(termo=termo):
                encontrados = database.buscar_alunos_por_nome(termo)
                self.assertEqual([aluno[0] for aluno in encontrados], esperados)
        self.assertEqual(database.buscar_alunos_por_nome("Pavlak")[0], (pavlak, "Matheus Pavlak", None))

        especial = database.criar_aluno("Nome 100%_! D'Ávila")
        for termo in ("%", "_", "!", "D'Ávila"):
            with self.subTest(termo=termo):
                self.assertEqual([a[0] for a in database.buscar_alunos_por_nome(termo)], [especial])

    def test_atualizacoes_informam_se_analise_foi_encontrada(self):
        self.conexao.execute(SCHEMA)
        aluno = database.criar_aluno("Aluno de teste")
        analise = database.criar_analise(aluno)
        curso = self.conexao.execute("INSERT INTO curso (codigo, nome) VALUES ('ADS', 'Sistemas') RETURNING id").fetchone()[0]
        matriz = self.conexao.execute("INSERT INTO matriz (curso_id, codigo) VALUES (%s, '2026') RETURNING id", (curso,)).fetchone()[0]
        operacoes = (
            (database.atualizar_analise, ("1/2027",)),
            (database.salvar_origem_aproveitamento, ("Curso", "Concluído", "Instituição")),
            (database.salvar_curso_e_matriz, (curso, matriz)),
        )
        for operacao, argumentos in operacoes:
            with self.subTest(operacao=operacao.__name__):
                self.assertIs(operacao(analise, *argumentos), True)
                # Atualizar com os mesmos valores também encontra o registro.
                self.assertIs(operacao(analise, *argumentos), True)
                antes = database.obter_analise(analise)
                self.assertIs(operacao(analise + 1000, *argumentos), False)
                self.assertEqual(database.obter_analise(analise), antes)

    def test_interface_reutiliza_aluno_existente_sem_inserir_aluno(self):
        from streamlit.testing.v1 import AppTest

        self.conexao.execute(SCHEMA)
        database.criar_aluno("Outro aluno")
        aluno_id = database.criar_aluno("Matheus José Freitas")
        antes = self.conexao.execute("SELECT * FROM aluno ORDER BY id").fetchall()
        app = AppTest.from_file(str(ROOT / "app.py")).run()
        app.switch_page("pages/2_Nova_Analise.py").run()

        with patch("database.criar_aluno", wraps=database.criar_aluno) as criar_aluno:
            app.text_input(key="busca_aluno").input("matheus").run()
            app.button(key=f"selecionar_aluno_{aluno_id}").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["aluno_id"], aluno_id)
            for botao in ("Salvar análise", "Avançar"):
                with self.subTest(botao=botao):
                    next(b for b in app.button if b.label == botao).click().run()
                    self.assertFalse(app.exception)
                    analise_id = app.session_state["analise_id"]
                    vinculo = self.conexao.execute(
                        "SELECT aluno_id FROM analise WHERE id = %s", (analise_id,)
                    ).fetchone()[0]
                    self.assertEqual(vinculo, aluno_id)
                    self.assertEqual(app.session_state["aluno_id"], aluno_id)
                    depois = self.conexao.execute("SELECT * FROM aluno ORDER BY id").fetchall()
                    self.assertEqual(depois, antes)
                    if botao == "Salvar análise":
                        next(b for b in app.button if b.label == "Cadastrar outra análise").click().run()
            criar_aluno.assert_not_called()
        self.assertEqual(self.conexao.execute("SELECT count(*) FROM analise").fetchone()[0], 2)

    def test_migracao_preserva_registros_e_nao_funde_homonimos(self):
        self.conexao.execute(SCHEMA_021)
        self.conexao.execute("INSERT INTO curso (codigo, nome) VALUES ('ADS', 'Sistemas')")
        self.conexao.execute("INSERT INTO matriz (curso_id, codigo) VALUES (1, '2026')")
        self.conexao.execute("""
            INSERT INTO analise (nome_aluno, ra, semestre_ano, situacao, procedencia, curso_id, matriz_id)
            VALUES ('Ana', '123', '2026/1', 'Regular', 'Externa', 1, 1),
                   ('Ana', '123', '2026/2', 'Regular', 'Interna', NULL, NULL),
                   ('Bruno', '', NULL, NULL, NULL, NULL, NULL),
                   ('Carla', NULL, NULL, NULL, NULL, NULL, NULL)
        """)
        antes = self.conexao.execute("SELECT * FROM analise ORDER BY id").fetchall()
        self.conexao.execute(MIGRACAO_TESTE)
        self.conexao.execute(MIGRACAO_ORIGEM_TESTE)
        for original in antes:
            atual = database.obter_analise(original[0])
            self.assertEqual(atual[:2], original[:2])
            self.assertEqual(atual[2], original[2] or None)
            self.assertEqual(atual[3:9], original[3:9])
        self.assertEqual(len(database.listar_alunos()), 4)
        self.assertNotEqual(database.obter_analise(1)[9], database.obter_analise(2)[9])
        novo = database.criar_analise(database.obter_analise(1)[9])
        self.assertGreater(novo, 4)
        # Reexecução falha sem modificar registros já migrados.
        with self.assertRaises(psycopg.errors.DuplicateTable):
            with self.conexao.transaction():
                self.conexao.execute(MIGRACAO_TESTE)
        self.assertEqual(len(database.listar_analises()), 5)

    def test_migracao_vazia(self):
        self.conexao.execute(SCHEMA_021)
        self.conexao.execute(MIGRACAO_TESTE)
        self.conexao.execute(MIGRACAO_ORIGEM_TESTE)
        self.assertEqual(database.listar_analises(), [])
        ident = database.criar_aluno("Novo aluno")
        self.assertEqual(database.obter_analise(database.criar_analise(ident))[9], ident)

    def test_migracao_invalida_reverte_todas_as_alteracoes(self):
        self.conexao.execute(SCHEMA_021)
        self.conexao.execute("INSERT INTO analise (nome_aluno, ra) VALUES (' ', '123')")
        with self.assertRaises(psycopg.errors.RaiseException):
            with self.conexao.transaction():
                self.conexao.execute(MIGRACAO_TESTE)
        self.assertEqual(self.conexao.execute("SELECT nome_aluno, ra FROM analise").fetchall(), [(' ', '123')])
        self.assertIsNone(self.conexao.execute("SELECT to_regclass('aluno')").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
