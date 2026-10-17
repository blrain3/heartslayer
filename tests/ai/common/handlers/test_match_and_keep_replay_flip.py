"""Match and Keep flip phase: does it stop after the first two cards?

The reported symptom came from 2026-09-23-12-43-06--10XDXJRPAI4XR.log floor 41, where all
13 logged screens were answered with `choose 0`. That run started at 12:43 and the
value-ranked chooser was deployed at 13:10, so it was decided by the OLD rule
("first entry that is not a curse"). These tests pin down the difference between that rule
and the current one on the exact screens the log contained.
"""
import unittest

from rs.common.handlers.common_event_handler import match_and_keep_choice

# Verbatim choice_lists from 10XDXJRPAI4XR.log floor 41 (the `card`-bearing screens).
LOGGED_CARD_SCREENS = [
    # all twelve face down
    ["card0", "card1", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    # card0 taken and gone
    ["card1", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    # the junk pair is what card1 turned out to be; it stays on the board
    ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["flyingsleeaves", "judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["flyingsleeves", "judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
    ["judgement", "card2", "card3", "card4", "card5", "card6", "card7", "card8", "card9", "card10", "card11"],
]

JUNK = ("flyingsleeaves", "judgement")


def old_chooser(choice_list):
    """The rule active when that log was produced: first entry that is not a curse."""
    first_card = None
    for idx, choice in enumerate(choice_list):
        name = str(choice or "").strip().lower().replace("+", "")
        if not name or name == "leave":
            continue
        if first_card is None:
            first_card = idx
        if name not in ("normality", "deep breath"):
            return idx
    return first_card


def new_chooser(choice_list):
    return match_and_keep_choice(
        list(choice_list), cards_desired_for_deck={}, deck_card_counts={}
    )


class TestOldRuleReproducesTheReportedBug(unittest.TestCase):
    """The symptom, reproduced deterministically on real screen data."""

    def test_old_rule_takes_index_zero_on_every_screen_where_junk_comes_first(self):
        junk_first = [s for s in LOGGED_CARD_SCREENS if s[0] in JUNK]
        self.assertGreaterEqual(len(junk_first), 6, "expected many such screens in the log")
        for s in junk_first:
            self.assertEqual(old_chooser(s), 0)

    def test_old_rule_takes_junk_cards(self):
        """So it is not mere curse avoidance: it grabs the dead-weight pair."""
        junk_takes = [s[old_chooser(s)] for s in LOGGED_CARD_SCREENS if old_chooser(s) is not None]
        self.assertTrue(any(t in JUNK for t in junk_takes))

    def test_old_rule_opens_nothing_past_card2(self):
        picks = {old_chooser(s) for s in LOGGED_CARD_SCREENS}
        picked_names = set()
        for s in LOGGED_CARD_SCREENS:
            i = old_chooser(s)
            if i is not None:
                picked_names.add(s[i])
        deeper = [p for p in picked_names if str(p).startswith("card") and p not in ("card0", "card1", "card2")]
        self.assertEqual(deeper, [], f"old rule opened {deeper}")


class TestNewChooserOnTheSameRealScreens(unittest.TestCase):
    """Same data, current chooser."""

    def test_never_takes_the_junk_pair_while_face_down_cards_remain(self):
        for s in LOGGED_CARD_SCREENS:
            idx = new_chooser(s)
            self.assertIsNotNone(idx)
            self.assertNotIn(s[idx], JUNK)

    def test_always_takes_a_face_down_card(self):
        for s in LOGGED_CARD_SCREENS:
            idx = new_chooser(s)
            self.assertTrue(str(s[idx]).startswith("card"), f"took {s[idx]}")

    def test_target_moves_off_index_zero_when_index_zero_is_junk(self):
        for s in LOGGED_CARD_SCREENS:
            if s[0] in JUNK:
                self.assertNotEqual(new_chooser(s), 0)


class TestWholeBoardGetsOpened(unittest.TestCase):
    """Walk the event: take a card, it leaves the board, the junk pair comes back."""

    def test_all_twelve_slots_are_opened_exactly_once(self):
        """A full sweep: 12 face-down entries, every one opened exactly once.

        The chooser's job is only to never open the same slot twice and never leave
        face-down cards unexplored while it keeps grabbing known junk. The board is
        walked by removing the taken card (pairs collapse as the log shows) and
        re-adding the junk pair the event keeps offering.
        """
        board = [f"card{i}" for i in range(12)]
        opened = []
        junk_taken = 0

        for _ in range(60):
            if not any(str(c).startswith("card") for c in board):
                break  # nothing explorable left: leaving is the only sane action
            idx = new_chooser(board)
            if idx is None:
                break
            taken = board[idx]
            if str(taken).startswith("card"):
                opened.append(taken)
            else:
                junk_taken += 1
            board = [c for i, c in enumerate(board) if i != idx]
            if any(str(c).startswith("card") for c in board):
                board = list(JUNK) + board  # the event re-offers the pair

        self.assertEqual(opened, [f"card{i}" for i in range(12)], "every slot opened, in order, once")
        self.assertEqual(junk_taken, 0)

    def test_more_than_two_cards_are_opened(self):
        board = [f"card{i}" for i in range(12)]
        opened = []
        for _ in range(40):
            idx = new_chooser(board)
            if idx is None:
                break
            taken = board[idx]
            if str(taken).startswith("card"):
                opened.append(taken)
            board = [c for i, c in enumerate(board) if i != idx]
            if len(opened) % 2 == 1:
                board = list(JUNK) + board
            if not board:
                break
        self.assertGreater(len(opened), 2)

    def test_no_junk_is_taken_while_face_down_cards_remain(self):
        """The rule must never take junk while a face-down card is still on the board."""
        board = [f"card{i}" for i in range(12)]
        opened_total = 0
        junk_while_face_down = 0
        for _ in range(40):
            if not any(str(c).startswith("card") for c in board):
                break  # nothing left to explore: taking junk is then unavoidable
            idx = new_chooser(board)
            if idx is None:
                break
            taken = board[idx]
            if taken in JUNK:
                junk_while_face_down += 1
            if str(taken).startswith("card"):
                opened_total += 1
            board = [c for i, c in enumerate(board) if i != idx]
            if opened_total % 2 == 1 and any(str(c).startswith("card") for c in board):
                board = list(JUNK) + board  # the event re-offers the pair
        self.assertEqual(junk_while_face_down, 0,
                         f"took junk {junk_while_face_down} times while face-down cards remained")
        self.assertEqual(opened_total, 12, f"opened {opened_total} cards")


def opened_count(board):
    """Number of face-down entries currently on the board."""
    return [c for c in board if str(c).startswith("card")]


if __name__ == "__main__":
    unittest.main()
