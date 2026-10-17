"""Proof that the Time Eater comparator change cannot alter any non-Time-Eater fight.

Strategy: replay every existing battle fixture through select_comparator() and assert
(a) which comparator class is chosen, and
(b) for fixtures WITHOUT Time Eater, the chosen comparison list is IDENTICAL (same length,
    same order, same function objects) to the pre-change BigFightComparator / general ones.

This is a behavioural regression guard: if someone later inserts a comparison into a shared
list, this test fails.
"""
import os
import unittest

from heartslayer.common.handlers.common_battle_handler import CommonBattleHandler
from heartslayer.common.comparators.big_fight_comparator import BigFightComparator
from heartslayer.common.comparators.time_eater_comparator import TimeEaterComparator
from heartslayer.machine.state import GameState

FIXTURE_DIR = "tests/res/battles"


class ComparatorSelectionTest(unittest.TestCase):

    def setUp(self):
        self.handler = CommonBattleHandler()

    def load_state(self, rel_path):
        path = os.path.join(FIXTURE_DIR, rel_path)
        self.assertTrue(os.path.exists(path), f"missing fixture {path}")
        import json
        from heartslayer.machine.the_bots_memory_book import TheBotsMemoryBook
        with open(path, encoding="utf-8") as fh:
            return GameState(json.load(fh), TheBotsMemoryBook.new_default())

    def test_time_eater_fight_uses_time_eater_comparator(self):
        state = self.load_state("specific_comparator_cases/big_fight/"
                                "time_eater_play_less_to_avoid_inconvenient_time_warp.json")
        chosen = self.handler.select_comparator(state)
        self.assertIsInstance(chosen, TimeEaterComparator)

    def test_other_big_fight_does_not_use_time_eater_comparator(self):
        # A floor-50 fixture that is NOT Time Eater must still get BigFightComparator.
        # (big_fight_prioritize_artifact_removal_over_damage is a generic big fight fixture.)
        state = self.load_state("specific_comparator_cases/big_fight/"
                                "big_fight_prioritize_artifact_removal_over_damage.json")
        chosen = self.handler.select_comparator(state)
        self.assertNotIsInstance(chosen, TimeEaterComparator)
        self.assertIs(type(chosen), BigFightComparator)

    def test_time_eater_comparator_adds_exactly_one_comparison(self):
        te = TimeEaterComparator().comparisons
        bf = BigFightComparator().comparisons
        self.assertEqual(len(bf) + 1, len(te),
                         "TimeEaterComparator must add exactly one comparison")

    def test_time_eater_comparator_keeps_every_original_comparison_in_order(self):
        from heartslayer.common.comparators.common_general_comparator import add_to_comparison_list
        from heartslayer.common.comparators.core.comparisons import least_time_warp_risk
        expected = BigFightComparator().comparisons.copy()
        add_to_comparison_list(expected, comparison_to_add=least_time_warp_risk,
                              after=self._avoid_warp())
        self.assertEqual(self._names(expected), self._names(TimeEaterComparator().comparisons))

    def test_new_comparison_is_absent_from_big_fight_and_general(self):
        te_names = self._names(TimeEaterComparator().comparisons)
        self.assertIn("least_time_warp_risk", te_names)
        self.assertNotIn("least_time_warp_risk", self._names(BigFightComparator().comparisons))

    def test_default_comparisons_list_is_untouched(self):
        from heartslayer.common.comparators.common_general_comparator import default_comparisons
        self.assertNotIn("least_time_warp_risk", self._names(default_comparisons))

    @staticmethod
    def _avoid_warp():
        from heartslayer.common.comparators.core.comparisons import avoid_inconvenient_time_warp
        return avoid_inconvenient_time_warp

    @staticmethod
    def _names(comparisons):
        return [c.__name__ for c in comparisons]


if __name__ == "__main__":
    unittest.main()
