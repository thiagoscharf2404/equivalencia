import psycopg
import streamlit as st

from database import listar_disciplinas, obter_plano_ensino, salvar_plano_ensino


st.title("Planos de Ensino")
st.caption("Cadastre e mantenha os planos de ensino vinculados às disciplinas da UNIPAR.")

try:
    disciplinas = listar_disciplinas()
except psycopg.Error:
    st.error("Não foi possível carregar as disciplinas. Tente novamente.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()

if not disciplinas:
    st.warning("Cadastre uma disciplina antes de incluir um plano de ensino.")
    st.stop()

disciplina = st.selectbox(
    "Disciplina *",
    disciplinas,
    format_func=lambda d: f"{d[2]} ({d[1]}) — {d[4]} · matriz {d[3]}",
    key="plano_disciplina",
)

try:
    plano = obter_plano_ensino(disciplina[0])
except psycopg.Error:
    st.error("Não foi possível carregar o plano de ensino. Tente novamente.")
    st.stop()

if plano:
    st.info("Esta disciplina já possui um plano cadastrado. Salvar atualizará as informações.")
    valores = plano[2:6]
else:
    valores = ("", "", "", "")

with st.form(f"form_plano_ensino_{disciplina[0]}"):
    st.subheader("Editar plano de ensino" if plano else "Cadastrar plano de ensino")
    ementa = st.text_area("Ementa *", value=valores[0] or "", height=140)
    conteudo = st.text_area(
        "Conteúdo programático *", value=valores[1] or "", height=200
    )
    objetivos = st.text_area("Objetivos (opcional)", value=valores[2] or "", height=120)
    bibliografia = st.text_area(
        "Bibliografia (opcional)", value=valores[3] or "", height=120
    )
    salvar = st.form_submit_button("Salvar plano" if not plano else "Salvar alterações", type="primary")

if salvar:
    try:
        salvar_plano_ensino(disciplina[0], ementa, conteudo, objetivos, bibliografia)
    except ValueError as erro:
        st.error(str(erro))
    except psycopg.Error:
        st.error("Não foi possível salvar o plano. Confira os dados e tente novamente.")
    else:
        st.success("Plano de ensino salvo com sucesso.")
