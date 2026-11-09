from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from choice_reply_cache import explicit_choice
from voice_engine import ask_model


class ExplicitChoiceTests(unittest.TestCase):
    def test_letters_are_scoped_to_the_current_question(self):
        self.assertEqual(explicit_choice('我选A。','prediction'),'fox')
        self.assertEqual(explicit_choice('我选A。','method'),'hide')
        self.assertEqual(explicit_choice('B','prediction'),'tiger')
        self.assertEqual(explicit_choice('B','method'),'alone')

    def test_negations_mixed_choices_and_reasons_are_not_keyword_matched(self):
        for value in ['不选A','不是怕老虎','先别让老虎藏起来','A和B都试试','我猜老虎，因为它比较大','狐狸自己过去看看再让老虎过去']:
            self.assertIsNone(explicit_choice(value,'prediction'))
            self.assertIsNone(explicit_choice(value,'method'))

    def test_explicit_choices_do_not_call_remote_ai(self):
        with patch('voice_engine.urllib.request.urlopen',side_effect=AssertionError('Network should not run')):
            result=ask_model('让老虎藏起来',{},'method')
        self.assertEqual(result['branch'],'hide')
        self.assertEqual(result['understanding_source'],'explicit_local_choice')


if __name__=='__main__':unittest.main()
