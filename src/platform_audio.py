"""Local capture commands for PC rehearsal and the board; no network calls."""
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent


def recognizer_python():
    return ROOT/('.pc-venv/Scripts/python.exe' if sys.platform=='win32' else '.venv/bin/python')


def model_directory(prepare=False):
    source=ROOT/'models/vosk-model-small-cn-0.22'
    if sys.platform!='win32':return source
    # The native Windows Vosk library cannot open this project's Chinese path.
    target=Path(tempfile.gettempdir()).resolve()/'ying-stage-models/vosk-model-small-cn-0.22'
    if prepare and not (target/'am/final.mdl').is_file():
        target.parent.mkdir(exist_ok=True)
        shutil.copytree(source,target,dirs_exist_ok=True)
    return target


def start_capture(audio_path,stop_path):
    if sys.platform=='win32':
        command=[str(recognizer_python()),str(ROOT/'record_pc.py'),str(audio_path),str(stop_path)]
        environment=dict(os.environ)
        extra={'creationflags':subprocess.CREATE_NO_WINDOW}
    else:
        command=['arecord','-q','-D','pulse','-f','S16_LE','-r','16000','-c','1','-d','15',str(audio_path)]
        environment=dict(os.environ,PULSE_SOURCE='alsa_input.platform-es8388-sound.stereo-fallback')
        extra={}
    return subprocess.Popen(command,env=environment,stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**extra)


def stop_capture(recorder,stop_path):
    if recorder.poll() is None:
        if sys.platform=='win32':stop_path.touch()
        else:recorder.send_signal(signal.SIGINT)
    try:
        return recorder.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        recorder.kill()
        recorder.communicate()
        raise
