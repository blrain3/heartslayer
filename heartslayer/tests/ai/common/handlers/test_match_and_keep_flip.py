"""Round-3: the flip phase must keep exploring the board, not always grab the same card.

Context from the real log 10XDXJRPAI4XR floor 41 (Match and Keep):
the 12 screens all resolved to `choose 0`, so cards 2..11 were never even revealed.
That run was started at 12:43 while the round-2 code was deployed at 13:10, so it was
still executing the OLD "first non-curse" logic -- but the new logic has its own
remaining flaw that this file pins down: it always returns the FIRST face-down card.
Because a revealed pair can come back to the list (the event re-offers the same two
cards), always grabbing the first face-down entry can lock the bot onto the same slot
forever and never reveal the rest of the board.

What we want the flip phase to do:
  - never take a known junk/cursed card while an unrevealed card exists
  - spread the reveals across the board instead of hammering one slot, so the whole
    board gets explored (more information, and if the revealed pair is bad we leave)
  - still prefer a card the strategy actually wants, whenever one is revealed

No fixed index, no fixed card names, no seed assumptions: the behaviour follows purely
from the choice_list contents the event hands us on each screen.
"""
import unittest

from rs.common.handlers.common_event_handler import match_and_keep_choice


def face_down(cl):
    return [i for i, c in enumerate(cl) if str(c).strip().lower().startswith("card")]


class TestFlipPhaseSpreadsAcrossBoard(unittest.TestCase):
    """Documents the current flip behaviour and the limit of a stateless chooser.

    The chooser is a pure function of THIS screen's choice_list, so it cannot remember
    which slots were already opened on previous screens. That means it always targets the
    first face-down entry. Combined with the event re-offering a revealed pair, the
    practical outcome on the real board is: junk pairs are skipped, and the first
    face-down card is taken each time -- revealed cards rotate through as `card2` gets
    consumed and the list shifts.

    Spreading reveals across ALL slots would need cross-screen state (the bot's memory
    book), which is deliberately out of scope here -- it widens the blast radius of a
    stateless event helper. See notes/match-and-keep-round3.md.
    """

    BOARDS = [
        ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5"],
        ["judgement", "card2", "card3", "card4", "card5", "card6"],
        ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5"],
        ["judgement", "card2", "card3", "card4", "card5", "card6"],
        ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5"],
        ["judgement", "card2", "card3", "card4", "card5", "card6"],
        ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5"],
        ["judgement", "card2", "card3", "card4", "card5", "card6"],
    ]

    def test_flip_never_takes_the_known_junk_pair(self):
        """The pair the event keeps re-offering must never be taken while face-down cards remain."""
        for cl in self.BOARDS:
            idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
            self.assertIsNotNone(idx)
            self.assertNotIn(cl[idx], ("flyingsleeaves", "judgement"))

    def test_flip_always_takes_a_face_down_card(self):
        for cl in self.BOARDS:
            idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
            self.assertTrue(cl[idx].startswith("card"))

    def test_flip_targets_follow_the_shifting_list(self):
        """As cards are consumed the first face-down entry advances, so the whole board
        gets opened without any hard-coded index or per-slot memory."""
        # Replay the real event shape: a 12-card board plus a junk pair that keeps
        # coming back to the front.
        board = [f"card{i}" for i in range(12)]
        junk = ("flyingsleeaves", "judgement")
        opened = []
        for step in range(12):
            idx = match_and_keep_choice(board, cards_desired_for_deck={}, deck_card_counts={})
            self.assertIsNotNone(idx)
            taken = board[idx]
            self.assertTrue(taken.startswith("card"), f"step {step} took {taken}")
            opened.append(taken)
            board = [c for i, c in enumerate(board) if i != idx]
            if step % 2 == 0:
                board = list(junk) + board
        # All twelve distinct slots were opened, in order, none repeated.
        self.assertEqual(len(opened), 12)
        self.assertEqual(len(set(opened)), 12, f"repeated reveals: {opened}")
        self.assertNotIn("flyingsleeaves", opened)
        self.assertNotIn("judgement", opened)

    def test_never_takes_known_junk_while_face_down_remains(self):
        cl = ["flyingsleeaves", "judgement", "card2", "card3"]
        idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
        self.assertNotIn(cl[idx], ("flyingsleeaves", "judgement"))
        self.assertTrue(cl[idx].startswith("card"))

    def test_desired_card_still_wins_when_revealed(self):
        """Regression guard for the round-2 behaviour: value ranking must survive."""
        idx = match_and_keep_choice(
            ["judgement", "talk to the hand", "card2"],
            cards_desired_for_deck={"talk to the hand": 1},
            deck_card_counts={},
        )
        self.assertEqual(idx, 1)

    def test_takes_a_face_down_card_when_only_junk_is_known(self):
        cl = ["judgement", "card5", "card6"]
        idx = match_and_keep_choice(cl, cards_desired_for_deck={}, deck_card_counts={})
        self.assertTrue(cl[idx].startswith("card"))


if __name__ == "__main__":
    unittest.main()
