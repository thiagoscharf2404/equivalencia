import streamlit as st
import psycopg
import pandas as pd

from database import (
    listar_disciplinas_elegiveis_para_aproveitamento,
    listar_disciplinas_por_matriz,
    obter_conteudo_historico,
    obter_extracao_historico,
    salvar_extracao_historico,
    salvar_revisao_disciplinas,
)
from navegacao import apresentar_etapa, ir_para_etapa
from services.extracao_historico import extrair_disciplinas
from services.comparacao_carga_horaria import comparar_carga_horaria
from services.situacao_academica import classificar_situacao


dados = apresentar_etapa(3)
st.subheader("Disciplinas identificadas no histórico")
st.write("Confira os dados que foram lidos no documento. Corrija o que for necessário e confirme para continuar a análise.")

try:
    extracao, disciplinas = obter_extracao_historico(dados[0])
except psycopg.Error:
    st.error("Não foi possível carregar os dados extraídos. Confira se a migração da extração foi aplicada.")
    st.stop()

if not extracao:
    if st.button("Ler histórico e identificar disciplinas", type="primary"):
        try:
            documento = obter_conteudo_historico(dados[0])
            if documento is None:
                st.error("Anexe o histórico acadêmico antes de executar a extração.")
            else:
                resultado, aviso = extrair_disciplinas(documento[1], documento[2])
                salvar_extracao_historico(dados[0], documento[0], resultado, aviso)
                st.rerun()
        except ValueError as erro:
            st.error(str(erro))
        except psycopg.Error:
            st.error("Não foi possível salvar o resultado da extração no PostgreSQL.")
    st.info("Execute a extração para identificar as disciplinas presentes no histórico.")
else:
    st.caption(f"Processado em {extracao[2]}")
    if extracao[3]:
        st.warning(extracao[3])

    if extracao[4]:
        st.success(f"Dados confirmados pelo coordenador em {extracao[4]}.")
    elif disciplinas:
        st.warning("Os dados continuam pendentes até salvar a revisão e confirmar todas as disciplinas.")

    if disciplinas:
        registros_editor = [
            {
                "ID": registro[0],
                "Código": registro[1] or "",
                "Disciplina": registro[2] or "",
                "Nota": registro[3] or "",
                "Carga horária": registro[4] or "",
                "Ano/semestre": registro[5] or "",
                "Situação": registro[6] or "",
            "Trecho do histórico": registro[7],
            }
            for registro in disciplinas
        ]
        with st.form(f"form_revisao_historico_{extracao[0]}"):
            dados_editados = st.data_editor(
                pd.DataFrame(registros_editor),
                hide_index=True,
                num_rows="fixed",
                disabled=["ID", "Trecho do histórico"],
                column_config={
                    "ID": st.column_config.NumberColumn("ID", format="%d"),
                    "Código": st.column_config.TextColumn("Código"),
                    "Disciplina": st.column_config.TextColumn("Disciplina"),
                    "Nota": st.column_config.TextColumn("Nota"),
                    "Carga horária": st.column_config.TextColumn("Carga horária"),
                    "Ano/semestre": st.column_config.TextColumn("Ano/semestre"),
                    "Situação": st.column_config.TextColumn("Situação"),
                    "Trecho do histórico": st.column_config.TextColumn(
                        "Trecho do histórico", width="large"
                    ),
                },
                key=f"editor_revisao_historico_{extracao[0]}",
                use_container_width=True,
            )
            confirma_revisao = st.checkbox(
                "Confirmo que revisei os dados de todas as disciplinas.",
                key=f"checkbox_confirmacao_historico_{extracao[0]}",
            )
            salvar, confirmar = st.columns(2)
            salvar_clicked = salvar.form_submit_button("Salvar alterações")
            confirmar_clicked = confirmar.form_submit_button(
                "Salvar e confirmar dados",
                type="primary",
                disabled=not confirma_revisao,
            )

        if salvar_clicked or confirmar_clicked:
            try:
                alteracoes = dados_editados.to_dict("records")
                salvou = salvar_revisao_disciplinas(
                    dados[0], alteracoes, confirmar=confirmar_clicked
                )
            except ValueError as erro:
                st.error(str(erro))
            except psycopg.Error:
                st.error("Não foi possível salvar a revisão no PostgreSQL.")
            else:
                if salvou:
                    st.session_state.mensagem_revisao_salva = (
                        "Dados salvos e confirmados." if confirmar_clicked
                        else "Alterações salvas. Os dados ainda precisam ser confirmados."
                    )
                    st.rerun()
                st.error("A extração não foi encontrada. Execute a leitura do histórico novamente.")
    else:
        st.info("Nenhuma disciplina foi identificada com segurança. Não há dados para confirmar.")

    if extracao[4] and disciplinas:
        st.subheader("Validação da situação acadêmica")
        st.caption("Somente disciplinas aprovadas serão fornecidas como candidatas ao aproveitamento.")
        st.dataframe(
            [
                {
                    "Código": registro[1] or "Não identificado",
                    "Disciplina": registro[2] or "Não identificada",
                    "Situação": registro[6] or "Não identificada",
                    "Resultado": classificar_situacao(registro[6])[0],
                    "Motivo": classificar_situacao(registro[6])[1],
                }
                for registro in disciplinas
            ],
            hide_index=True,
            use_container_width=True,
        )

    if extracao[4]:
        st.subheader("Conferência da carga horária")
        try:
            candidatas_origem = listar_disciplinas_elegiveis_para_aproveitamento(dados[0])
            disciplinas_destino = listar_disciplinas_por_matriz(dados[8])
        except psycopg.Error:
            st.error("Não foi possível carregar as disciplinas para comparar as cargas horárias.")
        else:
            if not candidatas_origem:
                st.info("Não há disciplinas aprovadas e confirmadas para comparar.")
            elif not disciplinas_destino:
                st.info("Não há disciplinas cadastradas na matriz selecionada.")
            else:
                origem_selecionada = st.selectbox(
                    "Disciplina de origem aprovada",
                    candidatas_origem,
                    format_func=lambda disciplina: (
                        f"{disciplina[2] or 'Nome não identificado'}"
                        f" ({disciplina[1] or 'Código não identificado'})"
                    ),
                    key=f"carga_origem_{dados[0]}",
                )
                destino_selecionado = st.selectbox(
                    "Disciplina da UNIPAR",
                    disciplinas_destino,
                    format_func=lambda disciplina: (
                        f"{disciplina[2]} ({disciplina[1]}) — {disciplina[3]} h"
                    ),
                    key=f"carga_destino_{dados[0]}_{dados[8]}",
                )
                resultado_carga = comparar_carga_horaria(
                    origem_selecionada[4], destino_selecionado[3]
                )
                if resultado_carga["atendido"] is True:
                    st.success(
                        f"Critério atendido: {resultado_carga['origem']} h de origem "
                        f"para {resultado_carga['destino']} h na UNIPAR."
                    )
                elif resultado_carga["atendido"] is False:
                    st.error(
                        f"Critério não atendido: {resultado_carga['origem']} h de origem "
                        f"para {resultado_carga['destino']} h na UNIPAR. "
                        f"{resultado_carga['motivo']}"
                    )
                else:
                    st.warning(resultado_carga["motivo"])

mensagem = st.session_state.pop("mensagem_revisao_salva", None)
if mensagem:
    st.success(mensagem)

voltar, avancar = st.columns(2)
if voltar.button("Voltar"):
    ir_para_etapa(2)
avancar.button("Avançar", disabled=True)
