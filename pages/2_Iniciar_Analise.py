import streamlit as st
import psycopg

from database import (
    atualizar_aluno, atualizar_analise, buscar_alunos_por_nome, criar_aluno,
    criar_analise_com_historico, listar_analises, obter_aluno, obter_historico,
    listar_planos_origem, remover_plano_origem, salvar_historico,
    salvar_planos_origem,
    normalizar_semestre_ano_ingresso,
)
from navegacao import apresentar_etapa, ativar_analise, confirmar_salvamento, ir_para_etapa
from services.documentos import validar_historico, validar_plano_origem


dados = apresentar_etapa(0)
st.write("Primeiro, identifique o aluno. Depois, anexe o histórico acadêmico; os planos de ensino da instituição de origem são opcionais.")
st.caption("Salve antes de sair desta etapa. Alterações não salvas podem ser descartadas.")

if dados and st.button("Cadastrar outra análise"):
    ativar_analise(None)
    st.rerun()

aluno_id = dados[9] if dados else None
if dados:
    st.write(f"Aluno: {dados[1]} — cadastro nº {aluno_id}")
    st.write(f"RA: {dados[2] or 'Não informado'}")
else:
    if st.session_state.pop("limpar_cadastro_aluno", False):
        st.session_state.cadastro_nome = ""
        st.session_state.cadastro_ra = ""
    with st.expander("Cadastrar aluno", expanded=st.session_state.aluno_id is None):
        with st.form("form_aluno"):
            nome = st.text_input("Nome do aluno *", max_chars=150, key="cadastro_nome")
            ra = st.text_input("RA (opcional)", max_chars=30, key="cadastro_ra")
            cadastrar = st.form_submit_button("Salvar aluno")
        if cadastrar:
            nome = nome.strip()
            ra = ra.strip() or None
            if not nome:
                st.error("O nome do aluno é obrigatório.")
            else:
                try:
                    st.session_state.aluno_id = criar_aluno(nome, ra)
                except psycopg.Error:
                    st.error("Não foi possível confirmar o cadastro do aluno. Consulte a busca antes de tentar salvar novamente.")
                else:
                    st.session_state.limpar_cadastro_aluno = True
                    st.session_state.aluno_cadastrado = True
                    st.rerun()
        if st.session_state.pop("aluno_cadastrado", False):
            st.success("Aluno cadastrado. Você já pode iniciar uma análise para ele.")

    st.subheader("Ou localize um aluno já cadastrado")
    termo = st.text_input(
        "Nome do aluno",
        placeholder="Digite o nome ou parte do nome",
        key="busca_aluno",
    ).strip()
    if termo:
        try:
            resultados = buscar_alunos_por_nome(termo)
        except psycopg.Error:
            # Preserva os campos quando a leitura impede renderizar o restante da tela.
            for chave in list(st.session_state):
                if chave.startswith(('nome_edicao_', 'ra_edicao_', 'analise_')):
                    st.session_state[chave] = st.session_state[chave]
            st.error("Não foi possível carregar os resultados da busca. Tente novamente.")
            if st.button("Tentar novamente"):
                st.rerun()
            st.stop()
        st.subheader("Resultados")
        if not resultados:
            st.info("Nenhum aluno encontrado.")
        for ident, nome, ra in resultados:
            with st.container(border=True):
                st.write(f"**{nome}**")
                st.write(f"RA: {ra}" if ra else "RA não informado")
                st.caption(f"Cadastro nº {ident}")
                selecionar, editar = st.columns(2)
                if selecionar.button("Selecionar", key=f"selecionar_aluno_{ident}"):
                    st.session_state.aluno_id = ident
                    st.session_state.editando_aluno_id = None
                    st.rerun()
                if editar.button("Editar", key=f"editar_aluno_{ident}"):
                    st.session_state.editando_aluno_id = ident
                    st.rerun()

    editando_aluno_id = st.session_state.get("editando_aluno_id")
    if editando_aluno_id is not None:
        try:
            aluno_edicao = obter_aluno(editando_aluno_id)
        except psycopg.Error:
            # Preserva os campos quando a leitura impede renderizar o restante da tela.
            for chave in list(st.session_state):
                if chave.startswith(('nome_edicao_', 'ra_edicao_', 'analise_')):
                    st.session_state[chave] = st.session_state[chave]
            st.error("Não foi possível carregar o aluno para editar. Tente novamente.")
            if st.button("Tentar novamente"):
                st.rerun()
            st.stop()
        if aluno_edicao is None:
            st.session_state.editando_aluno_id = None
            st.warning("O aluno não foi encontrado. Atualize a busca e tente novamente.")
        else:
            st.subheader(f"Editar aluno nº {aluno_edicao[0]}")
            with st.form(f"form_editar_aluno_{aluno_edicao[0]}"):
                nome_edicao = st.text_input(
                    "Nome do aluno *",
                    value=aluno_edicao[1],
                    max_chars=150,
                    key=f"nome_edicao_{aluno_edicao[0]}",
                )
                ra_edicao = st.text_input(
                    "RA (opcional)",
                    value=aluno_edicao[2] or "",
                    max_chars=30,
                    key=f"ra_edicao_{aluno_edicao[0]}",
                )
                salvar_edicao, cancelar_edicao = st.columns(2)
                salvar_aluno = salvar_edicao.form_submit_button("Salvar alterações")
                cancelar_aluno = cancelar_edicao.form_submit_button("Cancelar edição")

            if cancelar_aluno:
                st.session_state.editando_aluno_id = None
                st.rerun()
            if salvar_aluno:
                nome_edicao = nome_edicao.strip()
                ra_edicao = ra_edicao.strip() or None
                if not nome_edicao:
                    st.error("O nome do aluno é obrigatório.")
                else:
                    try:
                        atualizado = atualizar_aluno(editando_aluno_id, nome_edicao, ra_edicao)
                    except psycopg.Error:
                        st.error("Não foi possível confirmar as alterações do aluno. Tente salvar novamente.")
                    else:
                        if atualizado:
                            st.session_state.aluno_id = editando_aluno_id
                            st.session_state.editando_aluno_id = None
                            st.session_state.aluno_atualizado = True
                            st.rerun()
                        else:
                            st.error("O aluno não foi encontrado. Atualize a busca e tente novamente.")

    aluno_id = st.session_state.aluno_id
    try:
        aluno = obter_aluno(aluno_id) if aluno_id is not None else None
    except psycopg.Error:
        # Preserva os campos quando a leitura impede renderizar o restante da tela.
        for chave in list(st.session_state):
            if chave.startswith(('analise_',)):
                st.session_state[chave] = st.session_state[chave]
        st.error("Não foi possível carregar o aluno selecionado. Tente novamente.")
        if st.button("Tentar novamente"):
            st.rerun()
        st.stop()
    if aluno:
        if st.session_state.pop("aluno_atualizado", False):
            st.success("Cadastro atualizado.")
        st.write(f"Aluno selecionado: {aluno[1]} — cadastro nº {aluno[0]}")
        st.write(f"RA: {aluno[2]}" if aluno[2] else "RA não informado")
        if st.button("Limpar seleção"):
            st.session_state.aluno_id = None
            st.rerun()
    elif aluno_id is not None:
        st.session_state.aluno_id = aluno_id = None
        st.warning("O aluno selecionado não foi encontrado. Selecione outro aluno.")

st.subheader("Documentos do aproveitamento")
st.caption("Ao continuar, os documentos ficam vinculados ao aluno e a esta solicitação de aproveitamento.")

historico = None
planos_origem = []
if dados:
    try:
        historico = obter_historico(dados[0])
        planos_origem = listar_planos_origem(dados[0])
    except psycopg.Error:
        st.error("Não foi possível verificar o histórico acadêmico. Tente novamente.")
        if st.button("Tentar novamente"):
            st.rerun()
        st.stop()

if historico:
    st.success(f"Histórico anexado: {historico[1]}")
    st.caption("O arquivo original está preservado nesta análise e não pode ser substituído.")

if planos_origem:
    st.subheader("Planos de ensino da instituição de origem")
    st.caption("Arquivos anexados a esta análise.")
    for plano_origem in planos_origem:
        coluna_nome, coluna_remover = st.columns([5, 1])
        coluna_nome.write(f"📄 {plano_origem[1]}")
        if coluna_remover.button("Remover", key=f"remover_plano_origem_{plano_origem[0]}"):
            try:
                removido = remover_plano_origem(dados[0], plano_origem[0])
            except psycopg.Error:
                st.error("Não foi possível remover o plano. Tente novamente.")
            else:
                if removido:
                    st.rerun()
                st.warning("O arquivo não foi encontrado nesta análise.")

with st.form(f"form_analise_{dados[0] if dados else 'nova'}"):
    if not historico:
        arquivo_historico = st.file_uploader(
            "Histórico acadêmico *",
            type=["pdf", "docx"],
            help="Formatos aceitos: PDF e DOCX. O arquivo original será preservado.",
            key=f"historico_{dados[0] if dados else 'nova'}",
        )
    else:
        arquivo_historico = None
    arquivos_planos = st.file_uploader(
        "Planos de ensino da instituição de origem (opcional)",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="Você pode anexar vários arquivos PDF ou DOCX. Eles serão vinculados ao salvar a análise.",
        key=(
            f"planos_origem_{dados[0] if dados else 'nova'}_"
            f"{'-'.join(str(plano[0]) for plano in planos_origem) or 'vazio'}"
        ),
    )
    semestre_ano = st.text_input(
        "Semestre/Ano de ingresso",
        value=(dados[3] or "") if dados else "",
        placeholder="1/2027 ou 2/2027",
        help="Informe quando o aluno ingressou ou ingressará na UNIPAR (por exemplo, 1/2027). Este dado é opcional.",
        key=f"analise_{dados[0] if dados else 'nova'}_semestre_ano",
    )
    voltar, salvar, avancar = st.columns(3)
    voltar.form_submit_button("Voltar", disabled=True)
    salvar_apenas = salvar.form_submit_button("Salvar alterações" if dados else "Salvar análise")
    continuar = avancar.form_submit_button("Salvar e continuar", type="primary")

if salvar_apenas or continuar:
    if aluno_id is None:
        st.error("Cadastre ou selecione um aluno para iniciar a análise.")
    elif not historico and arquivo_historico is None:
        st.error("Anexe o histórico acadêmico para salvar e continuar a análise.")
    else:
        conteudo_historico = arquivo_historico.getvalue() if arquivo_historico else None
        conteudos_planos = [
            (arquivo.name, arquivo.getvalue()) for arquivo in arquivos_planos
        ]
        try:
            if arquivo_historico:
                validar_historico(arquivo_historico.name, conteudo_historico)
            for nome_arquivo, conteudo in conteudos_planos:
                validar_plano_origem(nome_arquivo, conteudo)
            semestre_ano = normalizar_semestre_ano_ingresso(semestre_ano)
        except ValueError as erro:
            st.error(str(erro))
        else:
            try:
                if dados:
                    salvo = atualizar_analise(dados[0], semestre_ano)
                    if salvo and not historico:
                        salvar_historico(
                            dados[0], arquivo_historico.name, conteudo_historico
                        )
                    if salvo and conteudos_planos:
                        salvar_planos_origem(dados[0], conteudos_planos)
                else:
                    nova_analise_id = criar_analise_com_historico(
                        aluno_id,
                        semestre_ano,
                        arquivo_historico.name,
                        conteudo_historico,
                        conteudos_planos,
                    )
                    salvo = True
            except ValueError as erro:
                st.error(str(erro))
            except psycopg.errors.UniqueViolation:
                st.error("Esta análise já possui um histórico acadêmico anexado.")
            except psycopg.Error:
                st.error("Não foi possível salvar a análise e os documentos. Consulte as análises antes de tentar novamente.")
            else:
                if not salvo:
                    st.error("As alterações não foram salvas porque a análise não foi encontrada. Selecione outra análise na listagem.")
                else:
                    if not dados:
                        ativar_analise(nova_analise_id)
                    confirmar_salvamento("Dados da análise salvos com sucesso.", 1 if continuar else 0)
                    if continuar:
                        ir_para_etapa(1)
                    st.rerun()

st.divider()
with st.expander("Retomar uma análise existente"):
    try:
        analises = listar_analises()
    except psycopg.Error:
        st.error("Não foi possível carregar as análises cadastradas. Tente novamente.")
        if st.button("Tentar novamente"):
            st.rerun()
        st.stop()
    if not analises:
        st.info("Nenhuma análise cadastrada.")
    else:
        st.dataframe(
            [
                {
                    "ID da análise": analise[0],
                    "ID do aluno": analise[9],
                    "Aluno": analise[1],
                    "RA": analise[2],
                    "Semestre/Ano de ingresso": analise[3],
                    "Curso de origem": analise[10],
                    "Situação do curso de origem": analise[4],
                    "Procedência": analise[5],
                    "Criada em": analise[6],
                }
                for analise in analises
            ],
            hide_index=True,
            width="stretch",
        )
        selecionada = st.selectbox(
            "Selecione uma análise",
            analises,
            format_func=lambda analise: (
                f"Análise #{analise[0]} — {analise[1]} — Aluno #{analise[9]}"
            ),
        )
        if st.button("Ativar análise selecionada"):
            ativar_analise(selecionada[0])
            st.rerun()
