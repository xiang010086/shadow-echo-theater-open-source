from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from voice_engine import usable_transcript
from choice_reply_cache import lookup


class LiveVoiceFeedbackTests(unittest.TestCase):
    def test_noise_or_fillers_cannot_be_sent_as_an_answer(self):
        for text in ['', '呢', '嗯嗯', '啊呀呢', '。！？']:
            self.assertIs(usable_transcript(text), False, text)
        for text in ['A', 'b', '狐狸', '我猜狐狸', '不选狐狸', '我不知道']:
            self.assertIs(usable_transcript(text), True, text)

    def test_both_clarifications_use_existing_local_question_audio(self):
        for interaction in ['prediction', 'method']:
            result = lookup(interaction, 'clarify')
            self.assertIsNotNone(result)
            self.assertEqual(result['path'].name, interaction + '.wav')
            self.assertEqual(result['path'].parent.name, 'voice-prompts')
        self.assertIsNone(lookup('unknown', 'clarify'))


if __name__ == '__main__':
    unittest.main()
