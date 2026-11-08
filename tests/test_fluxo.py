"""Testes da interface com persistência simulada, sem acessar PostgreSQL."""

from pathlib import Path
import unittest
from unittest.mock import patch
import psycopg

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class FluxoTest(unittest.TestCase):
    def setUp(self):
        self.alunos = {1: (1, "Ana", "123"), 2: (2, "Bruno", "456")}
        self.analises = {
            1: (1, "Ana", "123", "2/2026", "Concluído", "Externa", None, 10, 100, 1, "Engenharia"),
            2: (2, "Bruno", "456", "1/2026", "Incompleto", "Interna", None, 20, 200, 2, "Sistemas"),
        }
        self.cursos = [(10, "ADS", "Sistemas"), (20, "ENG", "Engenharia")]
        self.matrizes = {10: [(100, 10, "2024"), (101, 10, "2025")], 20: [(200, 20, "2026")]}
        funcoes = {
            "obter_analise": lambda ident: self.analises.get(ident),
            "listar_analises": lambda: list(self.analises.values()),
            "listar_alunos": lambda: self.fail("A tela não deve carregar todos os alunos"),
            "obter_aluno": lambda ident: self.alunos.get(ident),
            "buscar_alunos_por_nome": lambda termo: [
                aluno for aluno in self.alunos.values() if termo.lower() in aluno[1].lower()
            ],
            "criar_aluno": self.criar_aluno,
            "criar_analise": self.criar,
            "atualizar_analise": self.atualizar,
            "salvar_origem_aproveitamento": self.salvar_origem,
            "listar_cursos": lambda: self.cursos,
            "listar_matrizes_por_curso": lambda ident: self.matrizes[ident],
            "salvar_curso_e_matriz": self.salvar_matriz,
        }
        for nome, funcao in funcoes.items():
            mock = patch(f"database.{nome}", side_effect=funcao)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch("navegacao.obter_analise", side_effect=funcoes["obter_analise"])
        mock.start()
        self.addCleanup(mock.stop)
        self.app = AppTest.from_file(str(ROOT / "app.py")).run()

    def criar_aluno(self, nome, ra):
        ident = max(self.alunos) + 1
        self.alunos[ident] = (ident, nome.strip(), (ra or "").strip() or None)
        return ident

    def criar(self, aluno_id, *valores):
        ident = max(self.analises) + 1
        self.analises[ident] = (ident, *self.alunos[aluno_id][1:], *valores, None, None, None, None, None, aluno_id, None)
        return ident

    def atualizar(self, ident, *valores):
        if ident not in self.analises:
            return False
        self.analises[ident] = (*self.analises[ident][:3], *valores, *self.analises[ident][4:])
        return True

    def salvar_origem(self, ident, curso_origem, situacao, procedencia):
        if ident not in self.analises:
            return False
        dados = list(self.analises[ident])
        dados[4:6] = (situacao, procedencia)
        dados[10] = curso_origem
        self.analises[ident] = tuple(dados)
        return True

    def salvar_matriz(self, ident, curso, matriz):
        if ident not in self.analises:
            return False
        self.analises[ident] = (*self.analises[ident][:7], curso, matriz, *self.analises[ident][9:])
        return True

    def clicar(self, label):
        next(b for b in self.app.button if b.label == label).click().run()
        self.assertFalse(self.app.exception)
        # AppTest executa st.switch_page, mas não retém seu destino para
        # a próxima interação; sincronize com a página realmente renderizada.
        from navegacao import ETAPAS
        for titulo, pagina in ETAPAS:
            if self.app.title and self.app.title[0].value == titulo:
                self.app.switch_page(pagina)
                break

    def etapa(self, numero, analise_id):
        self.assertEqual(self.app.session_state["etapa_atual"], numero)
        self.assertEqual(self.app.session_state["analise_id"], analise_id)
        self.assertEqual(self.app.caption[0].value, f"Etapa {numero + 1} de 4")

    def ativar(self, ident=1):
        self.clicar("Iniciar análise")
        self.app.selectbox[0].select(self.analises[ident])
        self.clicar("Ativar análise selecionada")

    def conferir_erro_banco(self):
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.success)
        self.assertNotIn("SEGREDO", " ".join(e.value for e in self.app.error))

    def test_analise_ausente_na_atualizacao_preserva_ingresso(self):
        self.ativar()
        self.app.text_input(key="analise_1_semestre_ano").input("1/2027")
        with patch("database.atualizar_analise", return_value=False):
            for botao in ("Salvar alterações", "Avançar"):
                self.clicar(botao)
                self.conferir_erro_banco()
                self.assertIn("não foram salvas porque a análise não foi encontrada", self.app.error[0].value)
                self.etapa(0, 1)
                self.assertEqual(self.app.text_input(key="analise_1_semestre_ano").value, "1/2027")
                self.assertNotIn("confirmacao_salvamento", self.app.session_state)
        self.app.selectbox[0].select(self.analises[2])
        self.clicar("Ativar análise selecionada")
        self.etapa(0, 2)

    def test_analise_removida_ao_salvar_origem_preserva_campos(self):
        self.ativar()
        self.clicar("Avançar")
        self.app.text_input(key="curso_origem_1").input("Rascunho")
        self.app.text_input(key="procedencia_1").input("Instituição nova")
        def remover(*args):
            del self.analises[1]
            return False
        with patch("database.salvar_origem_aproveitamento", side_effect=remover):
            self.clicar("Avançar")
            self.conferir_erro_banco()
            self.assertIn("análise não foi encontrada", self.app.error[0].value)
            self.etapa(1, 1)
            self.assertEqual(self.app.text_input(key="curso_origem_1").value, "Rascunho")
            self.assertEqual(self.app.text_input(key="procedencia_1").value, "Instituição nova")
            self.assertTrue(self.app.get("page_link"))
        self.app.switch_page("pages/2_Nova_Analise.py").run()
        self.assertFalse(self.app.exception)
        self.app.selectbox[0].select(self.analises[2])
        self.clicar("Ativar análise selecionada")
        self.etapa(0, 2)

    def test_analise_removida_ao_salvar_destino_preserva_selecao(self):
        self.ativar()
        self.clicar("Avançar")
        self.clicar("Avançar")
        self.app.selectbox[1].select(self.matrizes[10][1])
        def remover(*args):
            del self.analises[1]
            return False
        with patch("database.salvar_curso_e_matriz", side_effect=remover):
            self.clicar("Avançar")
            self.conferir_erro_banco()
            self.assertIn("análise não foi encontrada", self.app.error[0].value)
            self.etapa(2, 1)
            self.assertEqual(self.app.selectbox[1].value[0], 101)
            self.assertTrue(self.app.get("page_link"))
        self.app.switch_page("pages/2_Nova_Analise.py").run()
        self.assertFalse(self.app.exception)
        self.clicar("Ativar análise selecionada")
        self.etapa(0, 2)

    def test_avisos_de_descarte_e_rotulos(self):
        self.ativar()
        self.assertIn("Situação do curso de origem", self.app.dataframe[0].value.columns)
        for etapa in range(3):
            self.assertTrue(any("Salve antes de voltar, trocar de análise ou navegar" in c.value for c in self.app.caption))
            if etapa < 2:
                self.clicar("Avançar")
        self.assertTrue(any("versão da grade" in c.value for c in self.app.caption))

    def test_menu_bloqueia_origem_nao_salva_mesmo_com_sessao_preenchida(self):
        dados = list(self.analises[1])
        dados[4] = None
        self.analises[1] = tuple(dados)
        self.ativar()
        for pagina in ("3_Selecionar_Curso_e_Matriz", "5_Proxima_Etapa"):
            self.app.session_state["etapa_atual"] = 3
            self.app.session_state["situacao_origem_1"] = "Concluído"
            self.app.switch_page(f"pages/{pagina}.py").run()
            self.assertFalse(self.app.exception)
            self.assertTrue(self.app.warning)
            self.assertFalse(self.app.success)
            self.assertFalse(self.app.selectbox)
            self.assertFalse(self.app.info)
            self.assertEqual(self.app.session_state["etapa_atual"], 1)
        self.clicar("Ir para Origem do Aproveitamento")
        self.etapa(1, 1)
        self.app.selectbox(key="situacao_origem_1").select("Incompleto")
        self.clicar("Salvar alterações")
        self.assertTrue(self.app.success)
        self.app.switch_page("pages/3_Selecionar_Curso_e_Matriz.py").run()
        self.etapa(2, 1)
        self.assertTrue(self.app.selectbox)
        self.assertFalse(self.app.warning)

    def test_menu_exige_destino_salvo_e_permite_retorno(self):
        dados = list(self.analises[1])
        dados[7:9] = (None, None)
        self.analises[1] = tuple(dados)
        self.ativar()
        self.app.switch_page("pages/3_Selecionar_Curso_e_Matriz.py").run()
        self.app.selectbox[1].select(self.matrizes[10][0]).run()
        self.app.switch_page("pages/5_Proxima_Etapa.py").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.warning)
        self.assertFalse(self.app.info)
        self.assertEqual(self.app.session_state["etapa_atual"], 2)
        self.clicar("Ir para Curso e Matriz")
        self.app.selectbox[1].select(self.matrizes[10][1])
        self.clicar("Avançar")
        self.etapa(3, 1)
        self.assertTrue(self.app.success)
        self.assertTrue(self.app.info)
        self.clicar("Voltar")
        self.assertEqual(self.app.selectbox[1].value[0], 101)
        self.clicar("Voltar")
        self.assertEqual(self.app.text_input(key="curso_origem_1").value, "Engenharia")

    def test_retomada_menu_aceita_campos_opcionais_vazios(self):
        self.alunos[1] = (1, "Ana", None)
        dados = list(self.analises[1])
        dados[2:4] = (None, "")
        dados[5] = None
        dados[10] = None
        self.analises[1] = tuple(dados)
        self.ativar()
        # Os dados salvos liberam a etapa, mesmo sem percorrer o wizard nesta sessão.
        self.app.switch_page("pages/5_Proxima_Etapa.py").run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.warning)
        self.assertTrue(self.app.info)
        self.app.switch_page("pages/4_Origem_do_Aproveitamento.py").run()
        self.etapa(1, 1)
        self.assertEqual(self.app.text_input(key="curso_origem_1").value, "")
        self.clicar("Voltar")
        self.etapa(0, 1)
        self.assertEqual(self.app.text_input(key="analise_1_semestre_ano").value, "")

    def test_menu_bloqueia_situacao_legada_e_ingresso_invalido(self):
        self.ativar()
        dados = list(self.analises[1])
        dados[4] = "Regular"
        self.analises[1] = tuple(dados)
        self.app.switch_page("pages/3_Selecionar_Curso_e_Matriz.py").run()
        self.assertTrue(self.app.warning)
        self.assertEqual(self.app.session_state["etapa_atual"], 1)
        dados[3] = "2026/2"
        self.analises[1] = tuple(dados)
        self.app.switch_page("pages/4_Origem_do_Aproveitamento.py").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.warning)
        self.assertEqual(self.app.session_state["etapa_atual"], 0)
        self.clicar("Ir para Nova Análise")
        self.assertEqual(self.app.text_input(key="analise_1_semestre_ano").value, "2026/2")

    def test_menu_falha_leitura_nao_libera_etapas(self):
        self.ativar()
        for pagina in ("4_Origem_do_Aproveitamento", "3_Selecionar_Curso_e_Matriz", "5_Proxima_Etapa"):
            with self.subTest(pagina=pagina):
                with patch("navegacao.obter_analise", side_effect=psycopg.OperationalError("SEGREDO")):
                    self.app.switch_page(f"pages/{pagina}.py").run()
                    self.conferir_erro_banco()
                    self.assertFalse(self.app.text_input)
                    self.assertFalse(self.app.selectbox)
                    self.assertFalse(self.app.info)
                    self.assertEqual(self.app.session_state["analise_id"], 1)
                self.clicar("Tentar novamente")
                self.assertFalse(self.app.error)

    def test_confirmacoes_salvar_e_avancar_aparecem_uma_vez(self):
        self.ativar()
        self.clicar("Salvar alterações")
        self.assertEqual([m.value for m in self.app.success], ["Dados da análise salvos com sucesso."])
        self.app.run()
        self.assertFalse(self.app.success)
        self.clicar("Avançar")
        self.etapa(1, 1)
        self.assertEqual([m.value for m in self.app.success], ["Dados da análise salvos com sucesso."])
        self.clicar("Salvar alterações")
        self.etapa(1, 1)
        self.assertEqual([m.value for m in self.app.success], ["Origem do aproveitamento salva com sucesso."])
        self.clicar("Avançar")
        self.etapa(2, 1)
        self.assertEqual([m.value for m in self.app.success], ["Origem do aproveitamento salva com sucesso."])
        self.clicar("Avançar")
        self.etapa(3, 1)
        self.assertEqual([m.value for m in self.app.success], ["Curso e matriz salvos com sucesso."])
        self.clicar("Voltar")
        self.assertFalse(self.app.success)

    def test_confirmacao_criacao_nao_reaparece_em_outra_analise(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="busca_aluno").input("Ana").run()
        self.app.button(key="selecionar_aluno_1").click().run()
        self.clicar("Salvar análise")
        self.assertEqual([m.value for m in self.app.success], ["Dados da análise salvos com sucesso."])
        self.app.selectbox[0].select(self.analises[2])
        self.clicar("Ativar análise selecionada")
        self.etapa(0, 2)
        self.assertFalse(self.app.success)
        self.app.run()
        self.assertFalse(self.app.success)

    def test_validacao_apos_sucesso_nao_exibe_confirmacao_antiga(self):
        self.ativar()
        self.clicar("Salvar alterações")
        self.assertTrue(self.app.success)
        self.app.text_input(key="analise_1_semestre_ano").input("3/2027")
        self.clicar("Salvar alterações")
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.success)
        self.app.text_input(key="analise_1_semestre_ano").input("1/2027")
        dados = list(self.analises[1])
        dados[4] = None
        self.analises[1] = tuple(dados)
        self.clicar("Avançar")
        self.assertIsNone(self.app.selectbox(key="situacao_origem_1").value)
        self.clicar("Salvar alterações")
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.success)

    def test_confirmacao_pendente_descartada_em_erro_de_leitura(self):
        self.ativar()
        self.app.session_state["confirmacao_salvamento"] = (1, 0, "Dados da análise salvos com sucesso.")
        with patch("navegacao.obter_analise", side_effect=psycopg.OperationalError("SEGREDO")):
            self.app.run()
            self.conferir_erro_banco()
        self.clicar("Tentar novamente")
        self.assertFalse(self.app.success)

    def test_confirmacao_pendente_nao_aparece_em_outro_contexto(self):
        self.ativar()
        for analise_id, etapa in ((2, 0), (1, 2)):
            with self.subTest(analise_id=analise_id, etapa=etapa):
                self.app.session_state["confirmacao_salvamento"] = (analise_id, etapa, "Mensagem antiga")
                self.app.run()
                self.assertFalse(self.app.success)
                self.assertNotIn("confirmacao_salvamento", self.app.session_state)

    def test_falha_leitura_analise_preserva_contexto_e_formulario(self):
        self.ativar()
        self.app.text_input(key="analise_1_semestre_ano").input("1/2027")
        with patch("navegacao.obter_analise", side_effect=psycopg.OperationalError("SEGREDO")):
            self.clicar("Avançar")
            self.conferir_erro_banco()
            self.assertEqual(self.app.session_state["analise_id"], 1)
            self.assertEqual(self.app.session_state["aluno_id"], 1)
            self.assertEqual(self.app.session_state["etapa_atual"], 0)
        self.clicar("Tentar novamente")
        self.assertEqual(self.app.text_input(key="analise_1_semestre_ano").value, "1/2027")
        self.clicar("Avançar")
        self.etapa(1, 1)

    def test_falha_criar_analise_preserva_ingresso_e_permite_repetir(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="busca_aluno").input("Ana").run()
        self.app.button(key="selecionar_aluno_1").click().run()
        self.app.text_input(key="analise_nova_semestre_ano").input("2/2027")
        with patch("database.criar_analise", side_effect=psycopg.OperationalError("SEGREDO")):
            self.clicar("Avançar")
            self.conferir_erro_banco()
            self.etapa(0, None)
            self.assertEqual(len(self.analises), 2)
            self.assertEqual(self.app.text_input(key="analise_nova_semestre_ano").value, "2/2027")
        self.clicar("Avançar")
        self.etapa(1, 3)
        self.assertEqual(self.analises[3][3], "2/2027")

    def test_falha_atualizar_analise_nao_avanca(self):
        self.ativar()
        self.app.text_input(key="analise_1_semestre_ano").input("1/2027")
        with patch("database.atualizar_analise", side_effect=psycopg.IntegrityError("SEGREDO")):
            for botao in ("Salvar alterações", "Avançar"):
                self.clicar(botao)
                self.conferir_erro_banco()
                self.etapa(0, 1)
                self.assertEqual(self.analises[1][3], "2/2026")
                self.assertEqual(self.app.text_input(key="analise_1_semestre_ano").value, "1/2027")
        self.clicar("Avançar")
        self.etapa(1, 1)
        self.assertEqual(self.analises[1][3], "1/2027")

    def test_falha_salvar_origem_nao_avanca_e_permite_repetir(self):
        self.ativar()
        self.clicar("Avançar")
        self.app.text_input(key="curso_origem_1").input("Novo curso")
        self.app.text_input(key="procedencia_1").input("Nova instituição")
        self.app.selectbox(key="situacao_origem_1").select("Trancado")
        with patch("database.salvar_origem_aproveitamento", side_effect=psycopg.OperationalError("SEGREDO")):
            for botao in ("Salvar alterações", "Avançar"):
                self.clicar(botao)
                self.conferir_erro_banco()
                self.etapa(1, 1)
                self.assertEqual(self.analises[1][10], "Engenharia")
                self.assertEqual(self.app.text_input(key="curso_origem_1").value, "Novo curso")
                self.assertEqual(self.app.text_input(key="procedencia_1").value, "Nova instituição")
                self.assertEqual(self.app.selectbox(key="situacao_origem_1").value, "Trancado")
        self.clicar("Avançar")
        self.etapa(2, 1)
        self.assertEqual(self.analises[1][10], "Novo curso")

    def test_falha_salvar_destino_nao_avanca_e_permite_repetir(self):
        self.ativar()
        self.clicar("Avançar")
        self.clicar("Avançar")
        self.app.selectbox[1].select(self.matrizes[10][1])
        with patch("database.salvar_curso_e_matriz", side_effect=psycopg.IntegrityError("SEGREDO")):
            self.clicar("Avançar")
            self.conferir_erro_banco()
            self.etapa(2, 1)
            self.assertEqual(self.analises[1][8], 100)
            self.assertEqual(self.app.selectbox[1].value[0], 101)
        self.clicar("Avançar")
        self.etapa(3, 1)
        self.assertEqual(self.analises[1][8], 101)

    def test_falha_cadastro_aluno_preserva_campos(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="cadastro_nome").input("Carla")
        self.app.text_input(key="cadastro_ra").input("789")
        with patch("database.criar_aluno", side_effect=psycopg.OperationalError("SEGREDO")):
            self.clicar("Salvar aluno")
            self.conferir_erro_banco()
            self.assertEqual(len(self.alunos), 2)
            self.assertEqual(self.app.text_input(key="cadastro_nome").value, "Carla")
            self.assertEqual(self.app.text_input(key="cadastro_ra").value, "789")
        self.clicar("Salvar aluno")
        self.assertEqual(self.alunos[3], (3, "Carla", "789"))
        self.assertEqual(self.app.text_input(key="cadastro_nome").value, "")

    def test_falha_edicao_aluno_preserva_campos(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="busca_aluno").input("Ana").run()
        self.app.button(key="editar_aluno_1").click().run()
        self.app.text_input(key="nome_edicao_1").input("Ana atualizada")
        with patch("database.atualizar_aluno", side_effect=psycopg.OperationalError("SEGREDO")):
            self.clicar("Salvar alterações")
            self.conferir_erro_banco()
            self.assertEqual(self.app.text_input(key="nome_edicao_1").value, "Ana atualizada")
            self.assertEqual(self.app.session_state["editando_aluno_id"], 1)
        with patch("database.atualizar_aluno", return_value=True) as atualizar:
            self.clicar("Salvar alterações")
            atualizar.assert_called_once_with(1, "Ana atualizada", "123")
            self.assertTrue(self.app.success)

    def test_falhas_leitura_cursos_e_matrizes_permitem_repetir(self):
        self.ativar()
        for pagina in ("1_Cursos_e_Matrizes", "3_Selecionar_Curso_e_Matriz"):
            for funcao in ("listar_cursos", "listar_matrizes_por_curso"):
                with self.subTest(pagina=pagina, funcao=funcao):
                    with patch(f"database.{funcao}", side_effect=psycopg.OperationalError("SEGREDO")):
                        self.app.switch_page(f"pages/{pagina}.py").run()
                        self.conferir_erro_banco()
                        self.assertEqual(self.app.session_state["analise_id"], 1)
                    self.clicar("Tentar novamente")
                    self.assertFalse(self.app.error)

    def test_falhas_busca_aluno_e_listagem_nao_limpam_selecao(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="busca_aluno").input("Ana").run()
        self.app.button(key="selecionar_aluno_1").click().run()
        for funcao in ("buscar_alunos_por_nome", "obter_aluno", "listar_analises"):
            with self.subTest(funcao=funcao):
                with patch(f"database.{funcao}", side_effect=psycopg.OperationalError("SEGREDO")):
                    self.app.run()
                    self.conferir_erro_banco()
                    self.assertEqual(self.app.session_state["aluno_id"], 1)
                    self.assertFalse(self.app.info)
                self.clicar("Tentar novamente")
                self.assertFalse(self.app.error)

    def test_ingresso_invalido_nao_cria_analise_e_permite_corrigir(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="busca_aluno").input("Ana").run()
        self.app.button(key="selecionar_aluno_1").click().run()
        campo = self.app.text_input(key="analise_nova_semestre_ano")
        self.assertEqual(campo.label, "Semestre/Ano de ingresso")
        with patch("database.criar_analise") as criar:
            for botao in ("Salvar análise", "Avançar"):
                self.app.text_input(key="analise_nova_semestre_ano").input("3/2027")
                self.clicar(botao)
                self.assertIn("1/2027 ou 2/2027", self.app.error[0].value)
                self.assertIsNone(self.app.session_state["analise_id"])
            criar.assert_not_called()
        self.app.text_input(key="analise_nova_semestre_ano").input("2/2027")
        self.clicar("Salvar análise")
        self.assertEqual(self.analises[3][3], "2/2027")
        self.assertEqual(self.app.dataframe[0].value.iloc[2]["Semestre/Ano de ingresso"], "2/2027")

    def test_ingresso_legado_preservado_ate_correcao_explicita(self):
        original = list(self.analises[1])
        original[3] = "2026/2"
        self.analises[1] = tuple(original)
        self.ativar()
        self.assertEqual(self.app.text_input(key="analise_1_semestre_ano").value, "2026/2")
        with patch("database.atualizar_analise") as atualizar:
            for botao in ("Salvar alterações", "Avançar"):
                self.clicar(botao)
                self.assertTrue(self.app.error)
                self.assertEqual(self.analises[1], tuple(original))
                self.etapa(0, 1)
            atualizar.assert_not_called()
        self.app.text_input(key="analise_1_semestre_ano").input("2/2026")
        self.clicar("Avançar")
        self.etapa(1, 1)
        self.assertEqual(self.analises[1][3], "2/2026")
        self.assertEqual(self.analises[1][4:], tuple(original[4:]))

    def test_criar_avancar_voltar_e_retomar(self):
        self.clicar("Iniciar análise")
        self.clicar("Avançar")
        self.assertTrue(self.app.error)
        self.assertEqual(len(self.analises), 2)
        self.app.text_input[0].input("Carla")
        self.clicar("Salvar aluno")
        self.assertEqual(len(self.analises), 2)
        self.assertEqual(self.alunos[3], (3, "Carla", None))
        self.clicar("Avançar")
        self.etapa(1, 3)
        self.app.text_input(key="curso_origem_3").input("Engenharia")
        self.app.selectbox(key="situacao_origem_3").select("Incompleto")
        self.app.text_input(key="procedencia_3").input("Outra instituição")
        self.clicar("Avançar")
        self.etapa(2, 3)
        self.clicar("Avançar")
        self.assertTrue(self.app.error)
        self.app.selectbox[1].select(self.matrizes[10][1])
        self.clicar("Avançar")
        self.etapa(3, 3)
        self.assertEqual(self.analises[3][7:], (10, 101, 3, "Engenharia"))
        self.assertTrue(next(b for b in self.app.button if b.label == "Avançar").disabled)
        self.clicar("Voltar")
        self.assertEqual(self.app.selectbox[1].value[0], 101)
        self.app.switch_page("app.py").run()
        self.clicar("Continuar análise ativa")
        self.etapa(2, 3)
        self.clicar("Voltar")
        self.clicar("Voltar")
        self.etapa(0, 3)
        self.assertEqual(self.analises[3][5], "Outra instituição")
        self.assertEqual(self.analises[3][10], "Engenharia")
        self.assertTrue(any("Carla" in m.value for m in self.app.markdown))
        self.clicar("Avançar")
        self.assertEqual(len(self.analises), 3)

    def test_trocar_analise_e_editar_sem_misturar_dados(self):
        self.ativar()
        self.app.text_input[0].input("1/2027")
        self.clicar("Salvar alterações")
        self.assertEqual(self.analises[1][3], "1/2027")
        self.assertEqual(self.alunos[1], (1, "Ana", "123"))
        self.app.selectbox[0].select(self.analises[2])
        self.clicar("Ativar análise selecionada")
        self.etapa(0, 2)
        self.assertEqual(self.app.text_input[0].value, "1/2026")
        self.assertTrue(any("Bruno" in m.value for m in self.app.markdown))
        self.clicar("Avançar")
        self.clicar("Avançar")
        self.assertEqual(self.app.selectbox[0].value[0], 20)
        self.assertEqual(self.app.selectbox[1].value[0], 200)
        self.app.selectbox[0].select(self.cursos[0]).run()
        self.assertIsNone(self.app.selectbox[1].value)
        self.app.selectbox[1].select(self.matrizes[10][0])
        self.clicar("Avançar")
        self.assertEqual(self.analises[2][7:], (10, 100, 2, "Sistemas"))
        self.assertEqual(self.analises[1][7:], (10, 100, 1, "Engenharia"))
        self.clicar("Voltar")
        self.clicar("Voltar")
        self.clicar("Voltar")
        self.clicar("Cadastrar outra análise")
        self.assertIsNone(self.app.session_state["analise_id"])
        self.assertEqual(self.app.text_input[0].value, "")

    def test_cadastro_com_ra_nome_obrigatorio_e_duas_analises(self):
        self.clicar("Iniciar análise")
        self.app.text_input[0].input("   ")
        self.clicar("Salvar aluno")
        self.assertTrue(self.app.error)
        self.assertEqual(len(self.alunos), 2)
        self.app.text_input[0].input("Daniela")
        self.app.text_input[1].input("789")
        self.clicar("Salvar aluno")
        self.assertEqual(self.alunos[3], (3, "Daniela", "789"))
        self.assertEqual(len(self.analises), 2)
        self.clicar("Salvar análise")
        self.etapa(0, 3)
        self.clicar("Cadastrar outra análise")
        self.assertEqual(self.app.session_state["aluno_id"], 3)
        self.clicar("Avançar")
        self.etapa(1, 4)
        self.assertEqual(self.analises[3][9], self.analises[4][9])
        self.assertEqual(len(self.alunos), 3)

    def test_acesso_direto_sem_analise_e_analise_removida(self):
        for pagina in ("3_Selecionar_Curso_e_Matriz", "4_Origem_do_Aproveitamento", "5_Proxima_Etapa"):
            self.app.switch_page(f"pages/{pagina}.py").run()
            self.assertFalse(self.app.exception)
            self.assertTrue(self.app.warning)
            self.clicar("Ir para Nova Análise")
        self.app.session_state["analise_id"] = 999
        self.app.switch_page("pages/3_Selecionar_Curso_e_Matriz.py").run()
        self.assertIsNone(self.app.session_state["analise_id"])
        self.assertFalse(self.app.exception)

    def test_busca_seleciona_homonimo_por_id_e_preserva_contexto(self):
        self.alunos[3] = (3, "Matheus Freitas", None)
        self.alunos[4] = (4, "Matheus Freitas", "987")
        self.clicar("Iniciar análise")
        self.assertFalse([b for b in self.app.button if b.label == "Selecionar"])
        self.app.text_input(key="busca_aluno").input("mAtHeUs").run()
        self.assertEqual(len([b for b in self.app.button if b.label == "Selecionar"]), 2)
        self.assertTrue(any(m.value == "RA não informado" for m in self.app.markdown))
        self.assertTrue(any(m.value == "RA: 987" for m in self.app.markdown))
        self.app.button(key="selecionar_aluno_4").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["aluno_id"], 4)
        self.app.text_input(key="busca_aluno").input("Inexistente").run()
        self.assertTrue(any(i.value == "Nenhum aluno encontrado." for i in self.app.info))
        self.assertFalse([b for b in self.app.button if b.label == "Selecionar"])
        self.assertEqual(self.app.session_state["aluno_id"], 4)
        self.app.switch_page("app.py").run()
        self.clicar("Iniciar análise")
        self.assertEqual(self.app.session_state["aluno_id"], 4)
        self.clicar("Avançar")
        self.etapa(1, 3)
        self.assertEqual(self.analises[3][9], 4)
        self.clicar("Voltar")
        self.assertEqual(self.app.session_state["aluno_id"], 4)
        self.clicar("Cadastrar outra análise")
        self.clicar("Limpar seleção")
        self.assertIsNone(self.app.session_state["aluno_id"])
        self.clicar("Avançar")
        self.assertTrue(self.app.error)

    def test_busca_sem_resultado_e_aluno_removido(self):
        self.clicar("Iniciar análise")
        self.app.text_input(key="busca_aluno").input("Ninguém").run()
        self.assertTrue(any(i.value == "Nenhum aluno encontrado." for i in self.app.info))
        self.app.text_input(key="busca_aluno").input("Ana").run()
        self.app.button(key="selecionar_aluno_1").click().run()
        del self.alunos[1]
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.warning)
        self.assertIsNone(self.app.session_state["aluno_id"])

    def test_selecionar_aluno_existente_cria_apenas_analises(self):
        alunos_antes = self.alunos.copy()
        with patch("database.criar_aluno") as criar_aluno:
            self.clicar("Iniciar análise")
            self.app.text_input(key="busca_aluno").input("Bruno").run()
            self.app.button(key="selecionar_aluno_2").click().run()
            self.assertEqual(self.app.session_state["aluno_id"], 2)
            self.clicar("Salvar análise")
            self.etapa(0, 3)
            self.assertEqual(self.analises[3][9], 2)
            self.assertEqual(self.alunos, alunos_antes)
            tabela = self.app.dataframe[0].value
            linha = tabela[tabela["ID da análise"] == 3].iloc[0]
            self.assertEqual(linha["ID do aluno"], 2)
            self.clicar("Cadastrar outra análise")
            self.clicar("Avançar")
            self.etapa(1, 4)
            self.assertEqual(self.analises[4][9], 2)
            self.assertEqual(self.alunos, alunos_antes)
            criar_aluno.assert_not_called()

    def test_sem_cursos_ou_matrizes_permite_voltar(self):
        self.ativar()
        self.clicar("Avançar")
        self.cursos = []
        self.clicar("Avançar")
        self.assertTrue(self.app.warning)
        self.assertTrue(next(b for b in self.app.button if b.label == "Avançar").disabled)
        self.clicar("Voltar")
        self.cursos = [(10, "ADS", "Sistemas")]
        self.matrizes[10] = []
        self.clicar("Avançar")
        self.assertTrue(self.app.warning)
        self.assertTrue(next(b for b in self.app.button if b.label == "Avançar").disabled)
        self.clicar("Voltar")
        self.etapa(1, 1)


if __name__ == "__main__":
    unittest.main()
