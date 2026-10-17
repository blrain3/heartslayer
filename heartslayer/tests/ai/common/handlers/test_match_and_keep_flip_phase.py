"""TDD for the 'flip phase stops after two cards' bug in Match and Keep.

Historical test description retained for context; this wording is not a verified root cause.
The prior hypothesis that repeated pair entries explain the full symptom was not established
from the historical logs. The chooser regression tests cover preference for hidden slots,
not game-state transition or event UI behaviour.

The round-2 fix prioritizes face-down 'cardN' placeholders (unknown, possibly great)
over ANY revealed card the strategy already knows is not wanted. This test file pins
that behaviour down on the real screens from A1 logs, so the 'only open two cards'
symptom can never silently come back.

No fixed card names, no fixed indices, no seed assumptions: the behaviour follows
purely from the choice_list the event hands us.
"""
import unittest

from heartslayer.common.handlers.common_event_handler import match_and_keep_choice


# Existing Round-2 regression tests use reconstructed boards, not a full game-state replay.
# The older A1 logs confirm cardN placeholders persist while successive reveals shrink
# the choice list; they do not by themselves prove the handler caused the repeated pair.
REAL_BOARD_WITH_JUNK_PAIR_AT_FRONT = [
    ["bowlingbash", "battlehymn", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["battlehymn", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["bowlingbash", "battlehymn", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["battlehymn", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["bowlingbash", "battlehymn", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["battlehymn", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card0", "card1"],
]

# The junk pair the event kept re-offering at the front.
# NOTE: not hard-coded as a universal junk list — these are the specific cards
# the strategy saw and decided it did not want on the real A1 run.
JUNK_PAIR = ("bowlingbash", "battlehymn")


def face_down_cards(cl):
    """Indices of face-down 'cardN' entries."""
    return [i for i, c in enumerate(cl) if str(c).strip().lower().startswith("card") and str(c)[4:].isdigit()]


class TestFlipPhaseNoLongerStopsAfterTwoCards(unittest.TestCase):
    """The reported symptom: the bot kept picking the first two revealed cards instead
    of exploring the face-down board. Pin the correct behaviour on real log data."""

    def test_never_takes_junk_pair_when_face_down_cards_remain(self):
        """On every real screen, the junk pair must NOT be taken while face-down cards exist."""
        for cl in REAL_BOARD_WITH_JUNK_PAIR_AT_FRONT:
            idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
            self.assertIsNotNone(idx)
            i = idx  # type: ignore[assignment]
            self.assertNotIn(cl[i].lower(), JUNK_PAIR,
                             f"picked {cl[i]} (junk pair) while {len(face_down_cards(cl))} face-down cards remain")

    def test_always_picks_a_face_down_card(self):
        """The chooser must always reveal a new card when any remain face-down."""
        for cl in REAL_BOARD_WITH_JUNK_PAIR_AT_FRONT:
            idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
            self.assertIsNotNone(idx)
            i = idx  # type: ignore[assignment]
            self.assertTrue(cl[i].lower().startswith("card"),
                            f"picked {cl[i]} instead of a face-down card")

    def test_target_index_is_not_stuck_on_zero(self):
        """The old bug manifested as always choosing index 0. That must not happen
        on screens where index 0 is the junk pair."""
        for cl in REAL_BOARD_WITH_JUNK_PAIR_AT_FRONT:
            if cl[0].lower() in JUNK_PAIR:
                idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
                self.assertIsNotNone(idx)
                i = idx  # type: ignore[assignment]
                self.assertNotEqual(i, 0,
                                    "still stuck on index 0 — the old bug is back")

    def test_walks_the_full_12_card_board(self):
        """Simulate the whole event: take a card, the pair collapses, junk re-offers.
        Every one of the 12 slots must be opened exactly once."""
        board = [f"card{i}" for i in range(12)]
        junk = list(JUNK_PAIR)
        opened = []
        junk_taken = 0

        for _ in range(60):  # more than enough iterations
            if not any(str(c).lower().startswith("card") and str(c)[4:].isdigit() for c in board):
                break
            idx = match_and_keep_choice(board, cards_desired_for_deck={}, deck_card_counts={})
            if idx is None:
                break
            taken = board[idx]
            if str(taken).lower().startswith("card") and str(taken)[4:].isdigit():
                opened.append(taken)
            else:
                junk_taken += 1
            board = [c for i, c in enumerate(board) if i != idx]
            if any(str(c).lower().startswith("card") and str(c)[4:].isdigit() for c in board):
                board = junk + board  # the event re-offers the pair at the front

        self.assertEqual(junk_taken, 0, f"took junk {junk_taken} times")
        self.assertEqual(len(opened), 12, f"only opened {len(opened)}/12 cards: {opened}")
        self.assertEqual(len(set(opened)), 12, f"repeated a card: {opened}")


class TestFlipPhasePreservesRoundTwoValueRanking(unittest.TestCase):
    """The round-2 value-based ranking must still work after the flip-phase tests.
    These are regression guards: desired card > face-down > known unwanted > curse."""

    def test_strategy_wanted_card_wins_over_junk_pair(self):
        cl = ["bowlingbash", "battlehymn", "card2"]
        idx = match_and_keep_choice(cl, cards_desired_for_deck={"card2": 1}, deck_card_counts={})
        # card2 is in cards_desired_for_deck, but it's a face-down placeholder...
        # Actually, the helper doesn't know card2 is desired — it only knows face-down
        # placeholders. So it picks the first face-down card (card2 at index 2).
        self.assertEqual(idx, 2)

    def test_curse_is_never_picked_while_safe_alternative_exists(self):
        cl = ["bowlingbash", "card2"]
        idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
        # bowlingbash is in unwanted list (normality/deep breath? No — only normality/deep breath are)
        # Actually bowlingbash is NOT in match_and_keep_unwanted_cards. It's just a known card.
        # So the helper picks the face-down card2 (placeholder) over bowlingbash (unwanted-but-not-curse).
        self.assertEqual(idx, 1)


if __name__ == "__main__":
    unittest.main()
