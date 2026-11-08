import unicodedata


def normalizar_situacao(valor):
    valor = unicodedata.normalize("NFKD", valor or "")
    sem_acentos = "".join(caractere for caractere in valor if not unicodedata.combining(caractere))
    return " ".join(sem_acentos.lower().split())


def classificar_situacao(valor):
    situacao = normalizar_situacao(valor)
    if situacao.startswith("reprovad"):
        return (
            "Excluída",
            "Disciplina reprovada: não pode ser considerada para aproveitamento.",
        )
    if situacao.startswith("aprovad"):
        return "Elegível", "Situação aprovada; pode seguir para análise de equivalência."
    if not situacao:
        return (
            "Bloqueada",
            "Situação não identificada; informe aprovação antes da análise.",
        )
    return (
        "Bloqueada",
        "Situação não reconhecida como aprovação; corrija antes da análise.",
    )
