from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from auto_listen import SpeechGate


class SpeechGateTests(unittest.TestCase):
    def test_room_noise_never_counts_as_a_finished_answer(self):
        for noise in [0,100,500,1400]:
            gate=SpeechGate()
            self.assertFalse(any(gate.feed(noise) for _ in range(85)))
            self.assertFalse(gate.started)

    def test_submission_requires_speech_then_a_pause(self):
        gate=SpeechGate()
        for _ in range(5):self.assertFalse(gate.feed(100))
        for _ in range(12):self.assertFalse(gate.feed(1800))
        self.assertTrue(gate.started)
        for _ in range(8):self.assertFalse(gate.feed(100))
        self.assertTrue(any(gate.feed(100) for _ in range(3)))

    def test_short_pause_inside_an_answer_does_not_cut_it_off(self):
        gate=SpeechGate()
        for rms in [100]*5+[1500]*5+[100]*5+[1400]*5:
            self.assertFalse(gate.feed(rms))
        self.assertTrue(any(gate.feed(100) for _ in range(11)))


if __name__=='__main__':unittest.main()
