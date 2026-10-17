"""Replay Match and Keep choice lists captured from a Chinese A1 run."""
import unittest

from heartslayer.common.handlers.common_event_handler import match_and_keep_choice


# Captured from 2026-09-23-13-02-15--NI5X0FGD1WW1.log. The first two cards had
# been revealed; the event then kept both visible ahead of the remaining cardN slots.
REVEALED_PAIR_WITH_HIDDEN_CARDS = [
    "bowlingbash",
    "battlehymn",
    "card2",
    "card3",
    "card4",
    "card5",
    "card6",
    "card7",
    "card8",
    "card9",
    "card10",
    "card11",
]
ONE_REVEALED_CARD_WITH_HIDDEN_CARDS = [
    "battlehymn",
    "card2",
    "card3",
    "card4",
    "card5",
    "card6",
    "card7",
    "card8",
    "card9",
    "card10",
    "card11",
]


def selected_choice_for_test(choices, index):
    if index is None:
        raise AssertionError("chooser returned no selection")
    return choices[index]


class TestMatchAndKeepRevealRegression(unittest.TestCase):
    def test_reveals_hidden_card_instead_of_reselecting_visible_pair(self):
        for choices in (REVEALED_PAIR_WITH_HIDDEN_CARDS, ONE_REVEALED_CARD_WITH_HIDDEN_CARDS):
            with self.subTest(choices=choices):
                index = match_and_keep_choice(choices, {}, {})
                self.assertIsNotNone(index)
                selected_choice = selected_choice_for_test(choices, index)
                self.assertTrue(
                    selected_choice.startswith("card") and selected_choice[4:].isdigit(),
                    f"selected already-revealed {selected_choice!r} with hidden cards remaining",
                )

    def test_desired_card_keeps_precedence_over_hidden_slots(self):
        choices = ["card2", "wanted_card", "card3"]
        index = match_and_keep_choice(choices, {"wanted_card": 1}, {})
        self.assertEqual(choices[index], "wanted_card")

    def test_hidden_slot_precedes_known_non_target_and_curse(self):
        choices = ["normality", "known_card", "card7"]
        index = match_and_keep_choice(choices, {}, {})
        self.assertEqual(choices[index], "card7")


if __name__ == "__main__":
    unittest.main()
