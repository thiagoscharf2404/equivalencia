import psycopg
import streamlit as st

from database import criar_disciplina, listar_disciplinas_por_matriz, listar_matrizes


st.title("Disciplinas da UNIPAR")
st.caption("Cadastre disciplinas vinculadas à matriz curricular correspondente.")

try:
    matrizes = listar_matrizes()
except psycopg.Error:
    st.error("Não foi possível carregar as matrizes. Tente novamente.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()

if not matrizes:
    st.warning("Cadastre um curso e uma matriz antes de incluir disciplinas.")
    st.stop()

matriz_selecionada = st.selectbox(
    "Matriz curricular",
    matrizes,
    format_func=lambda m: f"{m[2]} — {m[3]} · {m[1]}",
    key="disciplina_matriz_cadastro",
)

with st.form("form_cadastro_disciplina", clear_on_submit=True):
    st.subheader("Cadastrar disciplina")
    codigo = st.text_input("Código *", max_chars=30)
    nome = st.text_input("Nome *", max_chars=200)
    col_carga, col_periodo = st.columns(2)
    with col_carga:
        carga_horaria = st.number_input("Carga horária (horas) *", min_value=1, step=1)
    with col_periodo:
        periodo = st.number_input("Período *", min_value=1, step=1)
    salvar = st.form_submit_button("Salvar disciplina", type="primary")

if salvar:
    try:
        criar_disciplina(codigo, nome, carga_horaria, periodo, matriz_selecionada[0])
    except ValueError as erro:
        st.error(str(erro))
    except psycopg.errors.UniqueViolation:
        st.error("Já existe uma disciplina com esse código nesta matriz.")
    except psycopg.Error:
        st.error("Não foi possível salvar a disciplina. Confira os dados e tente novamente.")
    else:
        st.success("Disciplina cadastrada com sucesso.")

st.divider()
st.subheader("Consultar disciplinas")
matriz_consulta = st.selectbox(
    "Filtrar por matriz",
    matrizes,
    format_func=lambda m: f"{m[2]} — {m[3]} · {m[1]}",
    key="disciplina_matriz_consulta",
)

try:
    disciplinas = listar_disciplinas_por_matriz(matriz_consulta[0])
except psycopg.Error:
    st.error("Não foi possível carregar as disciplinas. Tente novamente.")
    if st.button("Recarregar disciplinas"):
        st.rerun()
else:
    if disciplinas:
        st.dataframe(
            [
                {"Código": d[1], "Nome": d[2], "Carga horária": d[3], "Período": d[4]}
                for d in disciplinas
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Não há disciplinas cadastradas nesta matriz.")
