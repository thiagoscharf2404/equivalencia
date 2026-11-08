import streamlit as st
import psycopg

from database import (
    listar_cursos,
    listar_matrizes_por_curso,
    salvar_curso_e_matriz,
)
from navegacao import apresentar_etapa, confirmar_salvamento, ir_para_etapa


dados_analise = apresentar_etapa(2)
st.write("Selecione o curso da UNIPAR para o qual o aluno solicita aproveitamento.")
if st.button("Voltar"):
    ir_para_etapa(1)
try:
    cursos = listar_cursos()
except psycopg.Error:
    # Preserva os campos quando a leitura impede renderizar o restante da tela.
    for chave in list(st.session_state):
        if chave.startswith(('curso_', 'matriz_')):
            st.session_state[chave] = st.session_state[chave]
    st.error("Não foi possível carregar os cursos. Tente novamente.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()

if not cursos:
    st.warning("Nenhum curso foi encontrado no banco de dados.")
    st.button("Avançar", disabled=True)
    st.stop()

curso_atual_id = dados_analise[7]
matriz_atual_id = dados_analise[8]

indice_curso = next(
    (
        indice
        for indice, curso in enumerate(cursos)
        if curso[0] == curso_atual_id
    ),
    0
)

curso_selecionado = st.selectbox(
    "Curso de destino",
    cursos,
    index=indice_curso,
    format_func=lambda curso: f"{curso[1]} — {curso[2]}",
    key=f"curso_{dados_analise[0]}"
)

try:
    matrizes = listar_matrizes_por_curso(curso_selecionado[0])
except psycopg.Error:
    # Preserva os campos quando a leitura impede renderizar o restante da tela.
    for chave in list(st.session_state):
        if chave.startswith(('matriz_',)):
            st.session_state[chave] = st.session_state[chave]
    st.error("Não foi possível carregar as matrizes. Tente novamente.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()

if not matrizes:
    st.warning("Não há matrizes cadastradas para este curso.")

indice_matriz = next(
    (
        indice
        for indice, matriz in enumerate(matrizes)
        if matriz[0] == matriz_atual_id
        and curso_selecionado[0] == curso_atual_id
    ),
    None
)

matriz_selecionada = st.selectbox(
    "Matriz curricular de destino",
    matrizes,
    index=indice_matriz,
    placeholder="Selecione uma matriz",
    help="A matriz curricular é a grade do curso: a lista de disciplinas usada para comparar com o histórico de origem.",
    format_func=lambda matriz: matriz[2],
    key=f"matriz_{dados_analise[0]}_{curso_selecionado[0]}"
)

if st.button("Avançar", type="primary", disabled=not matrizes):
    if matriz_selecionada is None:
        st.error("A matriz curricular é obrigatória para continuar.")
    else:
        try:
            salvo = salvar_curso_e_matriz(
                dados_analise[0],
                curso_selecionado[0],
                matriz_selecionada[0]
            )
        except psycopg.Error:
            st.error("Não foi possível confirmar o salvamento do curso e da matriz. Tente salvar novamente.")
        else:
            if not salvo:
                st.error("As alterações não foram salvas porque a análise não foi encontrada. Selecione outra análise na listagem.")
                st.page_link("pages/2_Nova_Analise.py", label="Ir para a listagem de análises")
            else:
                confirmar_salvamento("Curso e matriz salvos com sucesso.", 3)
                ir_para_etapa(3)
