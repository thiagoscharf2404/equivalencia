from decimal import Decimal, InvalidOperation
import re


_CARGA_HORARIA = re.compile(r"^\s*(\d+(?:[,.]\d+)?)\s*(?:h|hs|horas?)?\s*$", re.I)


def normalizar_carga_horaria(valor):
    if valor is None or isinstance(valor, bool):
        return None
    correspondencia = _CARGA_HORARIA.fullmatch(str(valor))
    if correspondencia is None:
        return None
    try:
        horas = Decimal(correspondencia.group(1).replace(",", "."))
    except InvalidOperation:
        return None
    return horas if horas > 0 else None


def comparar_carga_horaria(carga_origem, carga_destino):
    origem = normalizar_carga_horaria(carga_origem)
    destino = normalizar_carga_horaria(carga_destino)
    if origem is None:
        return {
            "atendido": None,
            "origem": None,
            "destino": destino,
            "motivo": "A carga horária de origem não foi identificada como um valor válido.",
        }
    if destino is None:
        return {
            "atendido": None,
            "origem": origem,
            "destino": None,
            "motivo": "A carga horária da disciplina da UNIPAR não é válida.",
        }
    if origem >= destino:
        return {
            "atendido": True,
            "origem": origem,
            "destino": destino,
            "motivo": "Carga horária de origem igual ou superior à carga horária da UNIPAR.",
        }
    return {
        "atendido": False,
        "origem": origem,
        "destino": destino,
        "motivo": "Carga horária de origem inferior à da UNIPAR.",
    }
