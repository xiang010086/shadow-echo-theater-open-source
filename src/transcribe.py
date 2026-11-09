"""One-shot local Mandarin ASR, run by the board's isolated Vosk environment."""
import json
from pathlib import Path
import sys
import wave

from vosk import KaldiRecognizer, Model, SetLogLevel
from asr_choices import prediction_grammar, corrected_prediction

SetLogLevel(-1)
with wave.open(sys.argv[1], "rb") as audio:
    if audio.getnchannels() != 1 or audio.getframerate() != 16000 or audio.getsampwidth() != 2:
        raise ValueError("Expected 16kHz mono PCM16")
    model = Model(str(Path(sys.argv[2])))
    recognizer = KaldiRecognizer(model, 16000)
    contextual = (KaldiRecognizer(model, 16000, json.dumps(prediction_grammar(), ensure_ascii=False))
                  if len(sys.argv)>3 and sys.argv[3]=='prediction' else None)
    if contextual:contextual.SetWords(True)
    pieces = []
    scene_pieces = []
    while block := audio.readframes(4000):
        if recognizer.AcceptWaveform(block):
            pieces.append(json.loads(recognizer.Result()).get("text", ""))
        if contextual and contextual.AcceptWaveform(block):
            scene_pieces.append(json.loads(contextual.Result()))
    pieces.append(json.loads(recognizer.FinalResult()).get("text", ""))
    raw_text="".join(pieces).replace(" ", "")
    output={'text':raw_text,'raw_text':raw_text,'correction_source':None}
    if contextual:
        scene_pieces.append(json.loads(contextual.FinalResult()))
        scene_text=''.join(item.get('text','') for item in scene_pieces).replace(' ','')
        words=[word for item in scene_pieces for word in item.get('result',[])]
        confidence=sum(word.get('conf',0) for word in words)/len(words) if words else 0
        corrected=corrected_prediction(raw_text,scene_text,confidence)
        output.update(context_text=scene_text,context_confidence=confidence)
        if corrected:output.update(text=corrected,correction_source='scene_decoder_observed_fox_confusion')
    print(json.dumps(output, ensure_ascii=False))
