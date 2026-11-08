import streamlit as st

from navegacao import inicializar_fluxo, ir_para_etapa


st.set_page_config(
    page_title="equivalencIA",
    page_icon="🎓",
    layout="wide",
)


def pagina_inicio():
    tema = st.context.theme.type
    logo = "assets/logo_dark.png" if tema == "dark" else "assets/logo_light.png"
    st.image(logo, width=260)

    st.title("Veja quais disciplinas podem ser aproveitadas")
    st.write(
        "Envie o histórico acadêmico, informe o curso de origem e selecione o "
        "curso e a matriz curricular de destino. O sistema prepara uma análise "
        "de equivalência para o professor revisar e decidir."
    )

    inicializar_fluxo()
    analise_ativa = st.session_state.analise_id is not None
    botao = "Continuar de onde parei" if analise_ativa else "Começar análise"
    if st.button(botao, type="primary", key="acao_principal"):
        etapa = st.session_state.etapa_atual if analise_ativa else 0
        ir_para_etapa(etapa)

    st.subheader("O que você vai fazer")
    colunas = st.columns(3)
    etapas = [
        ("1. Envie os documentos", "Anexe o histórico acadêmico e, se disponíveis, os planos de ensino."),
        ("2. Informe os cursos", "Registre o curso de origem e selecione o curso e a matriz de destino."),
        ("3. Valide a equivalência", "O professor confere a correspondência entre disciplinas e decide sobre o aproveitamento."),
    ]
    for coluna, (titulo, descricao) in zip(colunas, etapas):
        with coluna, st.container(border=True):
            st.markdown(f"**{titulo}**")
            st.caption(descricao)

    st.info(
        "A leitura dos arquivos e a comparação de carga horária já estão disponíveis. "
        "A comparação de ementas com IA e a geração do documento final ainda estão "
        "em desenvolvimento."
    )


paginas = {
    "Analisar um aluno": [
        st.Page(pagina_inicio, title="Início", icon="🏠", default=True),
        st.Page("pages/2_Iniciar_Analise.py", title="Enviar documentos", icon="📤"),
        st.Page("pages/4_Origem_do_Aproveitamento.py", title="Curso de origem", icon="🏫"),
        st.Page("pages/3_Curso_e_Matriz.py", title="Curso e matriz de destino", icon="🎓"),
        st.Page("pages/5_Continuacao_da_Analise.py", title="Análise de equivalência", icon="✨"),
    ],
    "Configurações": [
        st.Page("pages/1_Cursos_e_Matrizes.py", title="Cursos e matrizes", icon="📚"),
        st.Page("pages/6_Disciplinas.py", title="Disciplinas", icon="📖"),
        st.Page("pages/7_Planos_de_Ensino.py", title="Planos de ensino", icon="📑"),
    ],
}

navegacao = st.navigation(paginas, position="top")
navegacao.run()
