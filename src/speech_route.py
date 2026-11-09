"""Explicit local provider selection; never falls back to a paid provider."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ROUTE=ROOT/'.private/speech_route.json'


def provider():
    try:
        value=json.loads(ROUTE.read_text(encoding='utf-8')).get('provider')
        return value if value in {'organizer','minimax'} else 'disabled'
    except (OSError,ValueError,AttributeError):
        return 'disabled'


def ready():
    if provider()=='disabled':return False
    if provider()=='organizer':
        from tts_organizer_worker import load_key
        return bool(load_key())
    from tts_minimax_worker import host_ready,balance_blocked
    return host_ready() and not balance_blocked()


def worker():
    if provider()=='disabled':raise ValueError('No speech provider selected')
    return ROOT/('tts_organizer_worker.py' if provider()=='organizer' else 'tts_minimax_worker.py')
