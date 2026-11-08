import streamlit as st
import psycopg

from database import listar_cursos, listar_matrizes_por_curso


st.title("Cursos e matrizes curriculares")

try:
    cursos = listar_cursos()
except psycopg.Error:
    st.error("Não foi possível carregar os cursos. Tente novamente.")
    if st.button("Tentar novamente"):
        st.rerun()
    st.stop()

if not cursos:
    st.warning("Nenhum curso foi encontrado no banco de dados.")
else:
    curso_selecionado = st.selectbox(
        "Selecione um curso",
        cursos,
        format_func=lambda curso: f"{curso[1]} - {curso[2]}"
    )

    try:
        matrizes = listar_matrizes_por_curso(curso_selecionado[0])
    except psycopg.Error:
        st.error("Não foi possível carregar as matrizes. Tente novamente.")
        if st.button("Tentar novamente"):
            st.rerun()
        st.stop()

    st.subheader(f"Matrizes de {curso_selecionado[2]}")

    if matrizes:
        st.dataframe(
            [{"Matriz curricular": matriz[2]} for matriz in matrizes],
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Não há matrizes cadastradas para este curso.")
