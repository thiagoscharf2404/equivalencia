"""Extração conservadora de linhas de disciplinas em históricos PDF e DOCX."""

from io import BytesIO
import re
import unicodedata
from pathlib import PurePath

from docx import Document
from pypdf import PdfReader


CAMPOS = ("codigo", "nome", "nota", "carga_horaria", "periodo", "situacao")
_CODIGO = re.compile(r"^(?P<codigo>(?=[A-Z0-9._/-]*[A-Z])[A-Z0-9][A-Z0-9._/-]{2,})\b\s*(?:[-–:]\s*)?(?P<resto>.*)$", re.I)
_PERIODO = re.compile(r"(?<!\d)(?:(?:19|20)\d{2}\s*/\s*[12]|[12]\s*/\s*(?:19|20)\d{2})(?!\d)")
_NOTA_ROTULADA = re.compile(r"\b(?:nota|m[eé]dia|conceito)\s*[:=-]?\s*(\d{1,2}(?:[,.]\d{1,2})?)\b", re.I)
_CARGA_ROTULADA = re.compile(r"\b(?:carga\s*hor[aá]ria|ch)\s*[:=-]?\s*\(?\s*(\d{1,3})\s*\)?\s*(?:h\s*/\s*a|h|hs|horas?)?\b", re.I)
_CARGA_COM_UNIDADE = re.compile(r"\b\(?\s*(\d{1,3})\s*\)?\s*(?:h\s*/\s*a|h|hs|horas?)\b", re.I)
_CARGA_NUMERICA = re.compile(r"^\s*\(?\s*(\d{1,3})\s*\)?\s*(?:h\s*/\s*a|h|hs|horas?)?\s*$", re.I)
_ROTULO_ADMINISTRATIVO = re.compile(
    r"\b(?:atividades? complementares|carga horaria exigida|carga horaria cumprida|"
    r"total de carga horaria|data de conclusao|data da colacao|data da expedicao do diploma)\b",
    re.I,
)
_CODIGOS_ADMINISTRATIVOS = {
    "aula", "carga", "cnpj", "cpf", "documento", "endereco", "nome",
    "portaria", "registro", "rua", "unidade", "universidade",
}
_SITUACAO = re.compile(
    r"\b(aprovad[oa]|reprovad[oa]|cursando|em\s+curso|dispensad[oa]|"
    r"aproveitad[oa]|trancad[oa]|cancelad[oa]|reprovad[oa]\s+por\s+nota|"
    r"rep\s+nota|a\s+cursar)\b", re.I
)
_LINHA_EQUIVALENCIA = re.compile(
    r"^\s*(?P<periodo>(?:19|20)\d{2}\s*/\s*[12]|[12]\s*/\s*(?:19|20)\d{2})"
    r"\s+(?P<codigo>\d{5,8})\s+(?P<resto>.+)$"
)
_COLUNA_DESTINO = re.compile(r"\s{2,}(?:\d{5,8}|--)\s+[A-ZÁ-Ú]", re.I)
_RESULTADO_EQUIVALENCIA = re.compile(
    r"^(?P<nome>.+?)\s+(?P<nota>\d{1,2}(?:[,.]\d{1,2})?)\s+(?P<carga>\d{1,3})\s*$"
)
_LINHA_UNIOESTE = re.compile(
    r"^\s*(?:\d+\s*[ºªo]?\s+ano\s+)?(?P<periodo>(?:19|20)\d{2}(?:\s*/\s*[\dIVX]+)?)\s+"
    r"(?P<codigo>[A-Z]{2,}\d{3,})\s+(?P<resto>.+)$", re.I
)
_LINHA_UNIPAR = re.compile(
    r"^\s*(?:(?P<periodo>\d{1,2}\s*/\s*(?:19|20)\d{2})\s+)?"
    r"(?P<codigo>\d{5,8})\s+(?P<resto>.*)$"
)
_CARGA_UNIPAR = re.compile(r"^\(?\s*(\d{1,3})\s*\)?\s*H\s*/\s*A$", re.I)
_SITUACAO_UNIPAR = re.compile(r"^(APROVADO|APROVADA|REP\s+NOTA|A\s+CURSAR)$", re.I)


def _sem_acentos(valor):
    valor = unicodedata.normalize("NFKD", valor or "")
    return "".join(c for c in valor if not unicodedata.combining(c)).lower().strip()


def _normalizar_campo(celula):
    texto = _sem_acentos(celula)
    if "cod" in texto:
        return "codigo"
    if any(palavra in texto for palavra in ("disciplina", "componente", "nome")):
        return "nome"
    if any(palavra in texto for palavra in ("nota", "media", "conceito")):
        return "nota"
    if any(palavra in texto for palavra in ("carga", "horas", "ch")):
        return "carga_horaria"
    if any(palavra in texto for palavra in ("periodo", "semestre", "ano letivo", "ano/semestre")):
        return "periodo"
    if any(palavra in texto for palavra in ("situacao", "status", "resultado")):
        return "situacao"
    return None


def _separar_colunas(linha):
    if "\t" in linha:
        return [parte.strip() for parte in linha.split("\t")]
    if "|" in linha:
        return [parte.strip() for parte in linha.strip("| ").split("|")]
    return [parte.strip() for parte in re.split(r"\s{2,}", linha.strip()) if parte.strip()]


def _criar_registro(campos, evidencia):
    registro = {campo: (campos.get(campo) or "").strip() or None for campo in CAMPOS}
    # Guarde apenas os quatro campos necessários para a análise. A linha bruta
    # do histórico pode conter nomes de docentes, notas e dados pessoais.
    registro["texto_origem"] = ""
    if registro["codigo"] and not registro["nome"]:
        correspondencia = _CODIGO.match(registro["codigo"])
        if correspondencia:
            registro["codigo"] = correspondencia.group("codigo")
            registro["nome"] = correspondencia.group("resto").strip() or None
    if not registro["nome"] and not registro["codigo"]:
        return None
    if _ROTULO_ADMINISTRATIVO.search(_sem_acentos(evidencia)):
        return None
    if _sem_acentos(registro.get("codigo") or "") in _CODIGOS_ADMINISTRATIVOS:
        return None
    # Cabeçalhos e dados cadastrais costumam estar em caixa alta e eram
    # confundidos com matérias. Exigimos uma carga horária explícita e válida
    # para manter somente linhas que podem participar da equivalência.
    carga = _CARGA_NUMERICA.fullmatch(registro.get("carga_horaria") or "")
    if not carga or not 1 <= int(carga.group(1)) <= 1000:
        return None
    if not registro.get("nome") or len(registro["nome"].strip()) < 3:
        return None
    return registro


def _montar_registro(codigo, nome, carga, situacao, periodo=None):
    """Cria um registro limitado a disciplina, código, carga e situação."""
    nome = re.sub(r"\s+", " ", nome or "").strip(" -–|\t")
    if not nome or len(nome) < 3 or not carga or not 1 <= int(carga) <= 1000:
        return None
    return {
        "codigo": codigo,
        "nome": nome,
        "nota": None,
        "carga_horaria": str(int(carga)),
        "periodo": None,
        "situacao": situacao,
        "texto_origem": "",
    }


def _ler_tabelas_historico(linhas):
    """Lê linhas tabulares comuns em históricos da UNIPAR e da UNIOESTE."""
    registros = []
    indice_por_codigo = {}
    ultimo_unioeste = None

    for linha in linhas:
        uni = _LINHA_UNIOESTE.match(linha)
        if uni:
            resto = uni.group("resto")
            # A tabela UNIOESTE termina com carga, frequência, média e situação.
            celulas = re.split(r"\s{2,}", resto.strip())
            if len(celulas) >= 4:
                carga = re.fullmatch(r"\d{1,3}", celulas[-4].strip())
                situacao = celulas[-1].strip().upper()
                if carga and situacao == "A":
                    nome = " ".join(celulas[:-4]).strip()
                    registro = _montar_registro(
                        uni.group("codigo"), nome, carga.group(0), "Aprovado"
                    )
                    if registro:
                        indice_por_codigo[registro["codigo"]] = len(registros)
                        registros.append(registro)
                        ultimo_unioeste = registro
                        continue

        unipar = _LINHA_UNIPAR.match(linha)
        if unipar:
            celulas = re.split(r"\s{2,}", linha.strip())
            carga_indice = next(
                (i for i, celula in enumerate(celulas) if _CARGA_UNIPAR.fullmatch(celula.strip())),
                None,
            )
            situacao_indice = next(
                (i for i, celula in enumerate(celulas) if _SITUACAO_UNIPAR.fullmatch(celula.strip())),
                None,
            )
            if carga_indice is not None and situacao_indice is not None and len(celulas) >= 3:
                nome = celulas[2]
                situacao_original = celulas[situacao_indice].strip().upper()
                situacao = {
                    "REP NOTA": "Reprovado por nota",
                    "A CURSAR": "A cursar",
                }.get(situacao_original, "Aprovado")
                registro = _montar_registro(
                    unipar.group("codigo"),
                    nome,
                    _CARGA_UNIPAR.fullmatch(celulas[carga_indice].strip()).group(1),
                    situacao,
                )
                if registro:
                    indice_por_codigo[registro["codigo"]] = len(registros)
                    registros.append(registro)
                    ultimo_unioeste = None
                    continue

        # Nomes longos podem quebrar em linhas seguintes no PDF. Na tabela
        # UNIPAR, a coluna de disciplina começa aproximadamente no caractere 25.
        indentacao = len(linha) - len(linha.lstrip())
        trecho_continuacao = linha[24:50].strip() if 24 <= indentacao < 50 else ""
        if trecho_continuacao and re.fullmatch(r"[\wÀ-ÿ '&()/.-]+", trecho_continuacao):
            codigo_anterior = next(
                (codigo for codigo, indice in reversed(list(indice_por_codigo.items()))
                 if indice == len(registros) - 1),
                None,
            )
            if codigo_anterior:
                anterior = registros[-1]
                anterior["nome"] = f"{anterior['nome']} {trecho_continuacao}"
                continue

        # Nomes UNIOESTE também podem continuar na linha logo abaixo do código.
        if ultimo_unioeste and 18 <= indentacao < 50:
            trecho = linha[18:50].strip()
            if trecho and re.fullmatch(r"[\wÀ-ÿ '&()/.-]+", trecho):
                ultimo_unioeste["nome"] = f"{ultimo_unioeste['nome']} {trecho}".strip()
                continue
        if linha.strip():
            ultimo_unioeste = None

    return registros


def _ler_linha_com_colunas(colunas, cabecalho, evidencia):
    if not cabecalho or len(colunas) != len(cabecalho):
        return None
    campos = {}
    for indice, campo in enumerate(cabecalho):
        if campo and colunas[indice]:
            campos[campo] = colunas[indice]
    if campos.get("nome"):
        nome = campos["nome"]
        codigo = _CODIGO.match(nome)
        if codigo:
            campos.setdefault("codigo", codigo.group("codigo"))
            campos["nome"] = codigo.group("resto").strip() or None
    return _criar_registro(campos, evidencia)


def _ler_linha_sem_cabecalho(linha):
    texto = " ".join(linha.strip().split())
    if not texto:
        return None
    codigo_match = _CODIGO.match(texto)
    if not codigo_match:
        return None
    codigo = codigo_match.group("codigo")
    resto = codigo_match.group("resto")
    campos = {"codigo": codigo}

    periodo = _PERIODO.search(resto)
    if periodo:
        campos["periodo"] = periodo.group(0).replace(" ", "")
        resto = resto[:periodo.start()] + " " + resto[periodo.end():]

    nota = _NOTA_ROTULADA.search(resto)
    if nota:
        campos["nota"] = nota.group(1)
        resto = resto[:nota.start()] + " " + resto[nota.end():]

    carga = _CARGA_ROTULADA.search(resto) or _CARGA_COM_UNIDADE.search(resto)
    if carga:
        campos["carga_horaria"] = carga.group(1)
        resto = resto[:carga.start()] + " " + resto[carga.end():]

    situacao = _SITUACAO.search(resto)
    if situacao:
        campos["situacao"] = situacao.group(1)
        resto = resto[:situacao.start()] + " " + resto[situacao.end():]

    nome = re.sub(r"\s+", " ", resto).strip(" -–|\t")
    if nome:
        campos["nome"] = nome
    return _criar_registro(campos, texto)


def _interpretar_linhas(linhas):
    registros = []
    cabecalho = None
    for linha in linhas:
        if not linha or not linha.strip():
            continue
        colunas = _separar_colunas(linha)
        mapa = [_normalizar_campo(coluna) for coluna in colunas]
        if "nome" in mapa and sum(campo is not None for campo in mapa) >= 2:
            cabecalho = mapa
            continue
        registro = _ler_linha_com_colunas(colunas, cabecalho, linha)
        if registro is None:
            registro = _ler_linha_sem_cabecalho(linha)
        if registro:
            registros.append(registro)
    return registros


def _interpretar_linhas_equivalencia(linhas):
    """Lê a coluna de disciplinas cursadas em formulários de equivalência da UNIPAR."""
    registros = []
    pode_completar_nome = False
    for linha in linhas:
        correspondencia = _LINHA_EQUIVALENCIA.match(linha)
        if not correspondencia:
            texto = linha.strip()
            if (
                pode_completar_nome
                and registros
                and texto
                and len(texto) >= 3
                and len(linha) - len(linha.lstrip()) >= 20
                and not re.match(r"^(?:CURSANDO|A CURSAR|ANO|CÓDIGO|DISCIPLINA|EQUIVALÊNCIA)\b", texto, re.I)
                and not re.search(r"\d{4,}|\b(?:CURSANDO|A CURSAR)\b", texto, re.I)
                and re.fullmatch(r"[\wÀ-ÿ '&()/.-]+", texto)
            ):
                registros[-1]["nome"] = (registros[-1]["nome"] + " " + texto).strip()
                registros[-1]["texto_origem"] += " " + texto
                pode_completar_nome = True
            else:
                pode_completar_nome = False
            continue

        periodo = correspondencia.group("periodo").replace(" ", "")
        codigo = correspondencia.group("codigo")
        resto = correspondencia.group("resto")
        destino = _COLUNA_DESTINO.search(resto)
        if not destino:
            pode_completar_nome = False
            continue
        origem = resto[:destino.start()].strip()
        resultado = _RESULTADO_EQUIVALENCIA.match(origem)
        if not resultado:
            pode_completar_nome = False
            continue
        nome = resultado.group("nome").strip()
        registro = {
            "codigo": codigo,
            "nome": nome,
            "nota": resultado.group("nota"),
            "carga_horaria": resultado.group("carga"),
            "periodo": periodo,
            "situacao": None,
            "texto_origem": linha.strip(),
        }
        registros.append(registro)
        pode_completar_nome = True
    return registros


def extrair_disciplinas(nome_arquivo, conteudo):
    extensao = PurePath(nome_arquivo or "").suffix.lower()
    try:
        if extensao == ".pdf":
            pdf = PdfReader(BytesIO(conteudo), strict=False)
            linhas = []
            for pagina in pdf.pages:
                texto = pagina.extract_text(extraction_mode="layout") or ""
                linhas.extend(texto.splitlines())
        elif extensao == ".docx":
            documento = Document(BytesIO(conteudo))
            linhas = [paragrafo.text for paragrafo in documento.paragraphs]
            for tabela in documento.tables:
                for linha in tabela.rows:
                    linhas.append("\t".join(celula.text.strip() for celula in linha.cells))
        else:
            raise ValueError("Formato não suportado. Envie um arquivo PDF ou DOCX.")
    except ValueError:
        raise
    except Exception as erro:
        raise ValueError("Não foi possível ler o documento. Verifique se o PDF/DOCX não está corrompido ou protegido.") from erro

    resultados = _ler_tabelas_historico(linhas) if extensao == ".pdf" else []
    if not resultados:
        resultados = _interpretar_linhas_equivalencia(linhas) if extensao == ".pdf" else []
    if not resultados:
        resultados = _interpretar_linhas(linhas)
    # A tela de revisão e a análise precisam somente destes quatro campos;
    # descartar nota, período e trecho bruto evita guardar conteúdo irrelevante.
    resultados = [
        {
            "codigo": item.get("codigo"),
            "nome": item.get("nome"),
            "nota": None,
            "carga_horaria": item.get("carga_horaria"),
            "periodo": None,
            "situacao": item.get("situacao"),
            "texto_origem": "",
        }
        for item in resultados
        if item.get("nome") and item.get("carga_horaria")
    ]
    for item in resultados:
        status = (item.get("situacao") or "").strip().upper()
        if status == "A":
            item["situacao"] = "Aprovado"
        elif status == "REP NOTA":
            item["situacao"] = "Reprovado por nota"
        elif status == "A CURSAR":
            item["situacao"] = "A cursar"
    aviso = None
    if not any(linha.strip() for linha in linhas):
        aviso = "Não foi possível extrair texto. O PDF pode ser uma imagem digitalizada; os dados não foram inferidos."
    elif not resultados:
        aviso = (
            "Não encontrei disciplinas com carga horária identificável. Confira se anexou "
            "o histórico acadêmico correto e se as linhas mostram nome e carga horária."
        )
    return resultados, aviso
