from unidecode import unidecode


def normalize_name(name: str) -> str:
    return unidecode(name.lower()).strip()
