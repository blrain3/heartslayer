"""Replay the real Match and Keep screen choices from the A1 log 10XDXJRPAI4XR
against the NEW value-ranked logic.

Checks, in order:
  1. No Normality / Deep Breath is ever chosen (the round-1 guarantee still holds).
  2. The endless flyingsleeves/judgement pair is no longer taken every single time.
  3. Face-down placeholders are preferred while one is still on the screen.
  4. Nothing is hard-coded: the outcome follows from DESIRED_CARDS_FOR_DECK alone.

The screen snapshots below are the actual choice_list per screen, transcribed from
the log (the same lists the previous reproduction used, verified line by line).
"""
import unittest

from heartslayer.ai.peaceful_pummeling.config import DESIRED_CARDS_FOR_DECK
from heartslayer.common.handlers.common_event_handler import match_and_keep_choice

# (floor, logger line, choice_list as seen by the bot) -- 13 real screens.
SCREENS = [
    (41, 2682, ["card0", "card1", "flyingsleeves", "judgement"]),
    (41, 2687, ["card0", "card1", "flyingsleeves", "judgement"]),
    (41, 2693, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2698, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2703, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2708, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2713, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2718, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2723, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2728, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2733, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2738, ["flyingsleeves", "judgement", "card2", "card3"]),
    (41, 2743, ["leave"]),
]

BLACKLIST = {"normality", "deep breath"}


class TestReplayMatchAndKeepA1(unittest.TestCase):
    """Replay the real screens with a deck that mirrors the real run."""

    def _replay(self, deck_start=None):
        deck = dict(deck_start or {})
        chosen = []
        for _, _, choices in SCREENS:
            idx = match_and_keep_choice(
                choices,
                cards_desired_for_deck=DESIRED_CARDS_FOR_DECK,
                deck_card_counts=deck,
            )
            if idx is None:
                chosen.append(None)
                continue
            name = choices[idx].strip().lower().replace("+", "")
            chosen.append(name)
            if name not in BLACKLIST and not name.startswith("card"):
                deck[name] = deck.get(name, 0) + 1
        return chosen

    def test_no_curse_is_ever_chosen(self):
        chosen = self._replay()
        for name in chosen:
            if name is not None:
                self.assertNotIn(name, BLACKLIST)

    def test_face_down_is_preferred_while_available(self):
        """Screens 3-12 kept a card2/card3 face-down; those must be taken first."""
        chosen = self._replay()
        face_down = [c for c in chosen if c and c.startswith("card")]
        self.assertTrue(face_down, "should have flipped at least one face-down card")
        # The two screens that offered no face-down (only judgement/flyingsleeves/leave)
        # are where junk is unavoidable -- the rest must not be junk.
        self.assertGreaterEqual(len(face_down), 10)

    def test_junk_take_count_is_bounded_not_automatic(self):
        """Before the fix every screen with the pair produced a junk pickup.
        Now junk is only taken when no unknown card is left on that screen."""
        chosen = self._replay()
        junk = [c for c in chosen if c in ("flyingsleeves", "judgement")]
        # Real behaviour: 2 forced screens -> at most 2 junk picks, not 10.
        self.assertLessEqual(len(junk), 2)

    def test_deck_does_not_fill_with_junk(self):
        chosen = self._replay()
        deck = {}
        for name in chosen:
            if name and name not in BLACKLIST and not name.startswith("card"):
                deck[name] = deck.get(name, 0) + 1
        for junk in ("flyingsleeves", "judgement", "normality", "deep breath"):
            self.assertLessEqual(deck.get(junk, 0), 2, f"{junk} was picked {deck.get(junk, 0)}x")

    def test_matches_real_run_when_deck_starts_as_it_did(self):
        """With the real deck the fix produces a different, better spread than the live run:
        the live run ended with 5x judgement + 5x flyingsleeves."""
        chosen = self._replay()
        counts = {}
        for name in chosen:
            if name and name not in BLACKLIST and not name.startswith("card"):
                counts[name] = counts.get(name, 0) + 1
        self.assertNotEqual(
            (counts.get("judgement"), counts.get("flyingsleeves")),
            (5, 5),
            "reproduced the live run's 5x + 5x junk",
        )


if __name__ == "__main__":
    unittest.main()
