import streamlit as st
import psycopg

from database import salvar_origem_aproveitamento
from navegacao import SITUACOES_ORIGEM, apresentar_etapa, confirmar_salvamento, ir_para_etapa


situacoes = SITUACOES_ORIGEM
dados = apresentar_etapa(1)
st.write("Curso de origem é o curso em que o aluno concluiu ou está cursando as disciplinas que deseja aproveitar.")
st.caption("O período de ingresso na UNIPAR é informado na etapa anterior.")

with st.form(f"form_origem_{dados[0]}"):
    with st.container(border=True):
        curso_origem = st.text_input(
            "Curso de origem",
            value=dados[10] or "",
            max_chars=150,
            help="Nome do curso em que o aluno cursou as disciplinas. Exemplo: Administração.",
            key=f"curso_origem_{dados[0]}",
        )
        situacao_atual = dados[4]
        indice_situacao = situacoes.index(situacao_atual) if situacao_atual in situacoes else None
        situacao_origem = st.selectbox(
            "Situação do curso de origem *",
            situacoes,
            index=indice_situacao,
            placeholder="Selecione uma situação",
            key=f"situacao_origem_{dados[0]}",
        )
        procedencia = st.text_input(
            "Instituição de origem",
            value=dados[5] or "",
            max_chars=150,
            help="Faculdade ou universidade em que o aluno estudou esse curso.",
            key=f"procedencia_{dados[0]}",
        )

    voltar, salvar, avancar = st.columns(3)
    voltar_clicked = voltar.form_submit_button("Voltar")
    salvar_apenas = salvar.form_submit_button("Salvar alterações")
    continuar = avancar.form_submit_button("Avançar", type="primary")

if voltar_clicked:
    ir_para_etapa(0)

if salvar_apenas or continuar:
    if situacao_origem not in situacoes:
        st.error("Selecione a situação do curso de origem.")
    else:
        try:
            salvo = salvar_origem_aproveitamento(
                dados[0],
                curso_origem,
                situacao_origem,
                procedencia,
            )
        except psycopg.Error:
            st.error("Não foi possível confirmar o salvamento da origem do aproveitamento. Tente salvar novamente.")
        else:
            if not salvo:
                st.error("As alterações não foram salvas porque a análise não foi encontrada. Selecione outra análise na listagem.")
                st.page_link("pages/2_Nova_Analise.py", label="Ir para a listagem de análises")
            else:
                confirmar_salvamento("Origem do aproveitamento salva com sucesso.", 2 if continuar else 1)
                if continuar:
                    ir_para_etapa(2)
                st.rerun()
