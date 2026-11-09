"""Read only the account token explicitly supplied for this project."""
from pathlib import Path

TOKEN_FILE=Path(__file__).resolve().parent/'.private/hf_token.txt'


def load_token():
    try:
        token=TOKEN_FILE.read_text(encoding='utf-8-sig').strip()
    except OSError:
        return False
    if not token.startswith('hf_') or len(token)<10 or any(c.isspace() for c in token):
        return False
    return token
