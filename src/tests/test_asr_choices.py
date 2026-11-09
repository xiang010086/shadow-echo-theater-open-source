import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asr_choices import corrected_prediction, prediction_grammar


class SceneRecognitionTests(unittest.TestCase):
    def test_observed_fox_confusions_require_scene_decoder_agreement(self):
        self.assertEqual(corrected_prediction('苦力','狐狸',.95),'狐狸')
        self.assertEqual(corrected_prediction('我猜她怕的是和利益','我 猜 她 怕 的 是 狐狸',.95),'我猜她怕的是狐狸')
        self.assertIsNone(corrected_prediction('苦力','老虎',.99))

    def test_unrelated_mixed_or_negative_answers_are_not_forced(self):
        for raw in ['不是苦力','我不选苦力','狐狸和老虎','你好啊在听吗有没有听到啊','今天搬运苦力','我猜老虎因为它很大']:
            self.assertIsNone(corrected_prediction(raw,'狐狸',.99))

    def test_uncertain_and_unknown_audio_is_not_rewritten(self):
        self.assertIsNone(corrected_prediction('苦力','狐狸',.4))
        self.assertIsNone(corrected_prediction('苦力','[unk] 狐狸',.99))
        self.assertIn('[unk]',prediction_grammar())
        self.assertIn('狐狸',prediction_grammar())
        self.assertIn('老虎',prediction_grammar())


if __name__=='__main__':unittest.main()
