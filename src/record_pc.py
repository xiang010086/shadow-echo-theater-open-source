"""Local Windows capture worker; no network access or external upload."""
from pathlib import Path
import sys
import time
import wave

import sounddevice as sd

destination=Path(sys.argv[1])
stop=Path(sys.argv[2])
deadline=time.monotonic()+15
try:
    with wave.open(str(destination),'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        with sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',blocksize=800) as stream:
            while time.monotonic()<deadline and not stop.exists():
                block,overflow=stream.read(800)
                output.writeframesraw(bytes(block))
                if overflow:print('capture_overflow',file=sys.stderr)
finally:
    stop.unlink(missing_ok=True)
