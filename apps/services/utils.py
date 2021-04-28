import secrets


def random_secret_generator():
    return secrets.token_hex(32)
