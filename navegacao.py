import streamlit as st
import psycopg

from database import (
    normalizar_semestre_ano_ingresso,
    obter_analise,
    obter_extracao_historico,
    obter_historico,
)


SITUACOES_ORIGEM = ("Concluído", "Incompleto", "Trancado")


ETAPAS = (
    ("Aluno e documentos", "pages/2_Iniciar_Analise.py"),
    ("Curso de origem", "pages/4_Origem_do_Aproveitamento.py"),
    ("Curso e matriz de destino", "pages/3_Curso_e_Matriz.py"),
    ("Análise de equivalência", "pages/5_Continuacao_da_Analise.py"),
)


def inicializar_fluxo():
    st.session_state.setdefault("aluno_id", None)
    st.session_state.setdefault("analise_id", None)
    st.session_state.setdefault("etapa_atual", 0)


def ativar_analise(analise_id):
    st.session_state.pop("confirmacao_salvamento", None)
    st.session_state.analise_id = analise_id
    st.session_state.etapa_atual = 0


def ir_para_etapa(etapa):
    st.session_state.etapa_atual = etapa
    st.switch_page(ETAPAS[etapa][1])


def confirmar_salvamento(mensagem, etapa):
    st.session_state.confirmacao_salvamento = (
        st.session_state.analise_id, etapa, mensagem
    )


def apresentar_etapa(etapa):
    inicializar_fluxo()
    # Consumida uma única vez, inclusive se a leitura seguinte falhar.
    confirmacao = st.session_state.pop("confirmacao_salvamento", None)
    st.session_state.etapa_atual = etapa
    dados = None
    if st.session_state.analise_id is not None:
        try:
            dados = obter_analise(st.session_state.analise_id)
        except psycopg.Error:
            # Widgets não renderizados por st.stop seriam removidos da sessão.
            for chave in list(st.session_state):
                if chave.startswith(("analise_", "curso_", "matriz_", "situacao_origem_", "procedencia_")):
                    st.session_state[chave] = st.session_state[chave]
            st.error("Não foi possível carregar a análise ativa. Tente novamente.")
            if st.button("Tentar novamente"):
                st.rerun()
            st.stop()
        if dados is None:
            ativar_analise(None)
            st.warning("A análise ativa não foi encontrada. Crie ou selecione outra análise.")

    if dados:
        st.session_state.aluno_id = dados[9]
        st.write(f"Aproveitamento em andamento: {dados[1]} — nº {dados[0]}")
    st.caption(f"Etapa {etapa + 1} de {len(ETAPAS)}")
    st.title(ETAPAS[etapa][0])
    st.caption(" → ".join(nome for nome, _ in ETAPAS))
    if etapa > 0 and dados is None:
        st.warning("Crie ou selecione uma análise para continuar.")
        if st.button("Ir para aluno e documentos"):
            ir_para_etapa(0)
        st.stop()

    pendencia = None
    mensagem = None
    if etapa > 0 and dados:
        try:
            historico = obter_historico(dados[0])
        except psycopg.Error:
            st.error("Não foi possível verificar o histórico acadêmico. Tente novamente.")
            if st.button("Tentar novamente"):
                st.rerun()
            st.stop()
        if historico is None:
            pendencia = 0
            mensagem = "Anexe o histórico acadêmico na etapa Aluno e documentos antes de continuar."
        try:
            if pendencia is None:
                normalizar_semestre_ano_ingresso(dados[3])
        except ValueError:
            pendencia = 0
            mensagem = "Corrija o semestre/ano de ingresso na etapa Aluno e documentos (por exemplo, 1/2027) ou deixe o campo vazio."
        if pendencia is None and etapa > 1 and dados[4] not in SITUACOES_ORIGEM:
            pendencia = 1
            mensagem = "Informe a situação do curso de origem antes de continuar."
        if pendencia is None and etapa > 2 and (dados[7] is None or dados[8] is None):
            pendencia = 2
            mensagem = "Selecione o curso e a matriz curricular de destino antes de continuar."
        if pendencia is None and etapa > 3:
            try:
                extracao, disciplinas = obter_extracao_historico(dados[0])
            except psycopg.Error:
                st.error("Não foi possível verificar a confirmação dos dados extraídos. Tente novamente.")
                if st.button("Tentar novamente"):
                    st.rerun()
                st.stop()
            if (
                extracao is None
                or extracao[4] is None
                or not disciplinas
                or any(not disciplina[8] for disciplina in disciplinas)
            ):
                pendencia = 3
                mensagem = "Revise e confirme as disciplinas identificadas no histórico antes de continuar."
    if pendencia is not None:
        st.session_state.etapa_atual = pendencia
        st.warning(mensagem)
        if st.button(f"Ir para {ETAPAS[pendencia][0]}"):
            ir_para_etapa(pendencia)
        st.stop()

    if dados and confirmacao and confirmacao[:2] == (dados[0], etapa):
        st.success(confirmacao[2])
    return dados
