"""Small local speech/silence gate; never guesses the audience's answer."""


class SpeechGate:
    def __init__(self):
        self.elapsed=0.0
        self.calibration=[]
        self.threshold=260.0
        self.voiced=0.0
        self.silence=0.0
        self.started=False

    def feed(self,rms,seconds=.1):
        self.elapsed+=seconds
        if self.elapsed<=.41:
            self.calibration.append(rms)
            self.threshold=max(260,min(self.calibration)*2.6)
            return False
        if rms>self.threshold:
            self.voiced+=seconds
            self.silence=0
            if self.voiced>=.2:self.started=True
        elif self.started:
            self.silence+=seconds
        return self.started and self.elapsed>=1.2 and self.silence>=.9
