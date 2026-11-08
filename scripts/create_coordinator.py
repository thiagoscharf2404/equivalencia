"""Create an institutional coordinator account without exposing a password in shell history."""

import getpass
import hashlib
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import obter_conexao  # noqa: E402


def main():
    with obter_conexao() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, nome FROM unidade WHERE ativa = TRUE ORDER BY id")
        units = cursor.fetchall()
    if not units:
        raise SystemExit("Nenhuma unidade ativa. Execute primeiro sql/migrations/auth_coordenacao.sql.")
    print("Unidades disponíveis:")
    for unit_id, name in units:
        print(f"  {unit_id}: {name}")
    unit_id = int(input("ID da unidade: ").strip())
    if unit_id not in {row[0] for row in units}:
        raise SystemExit("Unidade inválida.")
    name = input("Nome do coordenador: ").strip()
    email = input("E-mail institucional: ").strip().lower()
    password = getpass.getpass("Senha: ")
    confirmation = getpass.getpass("Confirme a senha: ")
    minimum = 3 if os.getenv("APP_ENV", "development").lower() == "development" else 12
    if len(password) < minimum:
        raise SystemExit(f"A senha deve ter pelo menos {minimum} caracteres neste ambiente.")
    if password != confirmation:
        raise SystemExit("As senhas digitadas não coincidem.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    encoded = f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"
    with obter_conexao() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO coordenador (unidade_id, nome, email, senha_hash)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (unit_id, name, email, encoded),
        )
        coordinator_id = cursor.fetchone()[0]
    print(f"Acesso criado com sucesso (coordenador {coordinator_id}, unidade {unit_id}).")


if __name__ == "__main__":
    main()
