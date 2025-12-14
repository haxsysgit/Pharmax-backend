def get_password_hash(password: str) -> str:
    raise NotImplementedError()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    raise NotImplementedError()
