"""Tests for Match and Keep choice ranking and strategy-aware card selection.

Regression context (A1 log 10XDXJRPAI4XR, floor 41): the event offered the pair
(flyingsleeves, judgement) over and over. Both avoid the curse blacklist, so
`match_and_keep_choice` returned index 0 every time -> 5x Judgement + 5x Flying Sleeves.

Design: rank choices using the strategy data the handler ALREADY receives, instead of a
hard-coded "bad card" list:
  1. cards the strategy wants and has not reached its desired count for (highest)
  2. face-down 'cardN' placeholders -- unknown, might be a wanted card  (middle)
  3. known cards the strategy does not want
4. curses, only when the screen forces a card choice and no better option remains.

No card name is hard-coded in the production code except the curse blacklist.
"""
import unittest


class TestMatchAndKeepValueRanking(unittest.TestCase):
    """Unit level: match_and_keep_choice() with strategy value data."""

    def _choice(self, choices, desired=None, deck=None):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        return match_and_keep_choice(
            choices,
            cards_desired_for_deck=desired if desired is not None else {},
            deck_card_counts=deck if deck is not None else {},
        )

    def test_prefers_a_desired_card_over_other_real_cards(self):
        # judgement is offered first but not wanted; talk to the hand is wanted.
        idx = self._choice(
            ["judgement", "talk to the hand", "card2", "card3"],
            desired={"talk to the hand": 1},
        )
        self.assertEqual(idx, 1)

    def test_skips_desired_card_already_at_target_count(self):
        # Already have 1 blasphemy and want exactly 1 -> it is no longer desirable.
        # carve reality is a known but undesired card, so the face-down card2 must win.
        idx = self._choice(
            ["blasphemy", "carve reality", "card2"],
            desired={"blasphemy": 1},
            deck={"blasphemy": 1},
        )
        self.assertEqual(idx, 2)

    def test_still_takes_desired_card_below_target_count(self):
        self.assertEqual(
            self._choice(["blasphemy", "card1"], desired={"blasphemy": 2}, deck={"blasphemy": 1}), 0
        )
    def test_face_down_placeholder_beats_known_unwanted_card(self):
        """Core of the fix: 'cardN' (unknown, possibly great) must beat judgement."""
        idx = self._choice(["judgement", "card2", "card3"], desired={})
        self.assertEqual(idx, 1)

    def test_known_unwanted_card_is_last_resort(self):
        self.assertEqual(self._choice(["judgement"], desired={}), 0)

    def test_curses_never_selected_even_with_no_other_info(self):
        idx = self._choice(["normality", "judgement"], desired={})
        self.assertEqual(idx, 1)  # not the curse
        self.assertIsNotNone(idx)

    def test_falls_back_to_first_card_when_only_curses_remain(self):
        """The screen forces a choice: curses are the last resort, never a None."""
        self.assertEqual(self._choice(["normality", "deep breath"]), 0)
        self.assertEqual(self._choice(["normality", "leave"]), 0)

    def test_legacy_call_signature_still_works(self):
        """Old 1-arg callers must keep working (backwards compatible)."""
        self.assertEqual(self._choice(["card0", "normality"]), 0)


class TestMatchAndKeepHandlerUsesStrategyData(unittest.TestCase):
    """Integration: the handler must actually pass strategy data down."""

    def _state(self, event_id, event_name, choice_list, options):
        from rs.machine.state import GameState
        from rs.machine.the_bots_memory_book import TheBotsMemoryBook

        state_dict = {
            "available_commands": ["choose", "wait", "state"],
            "ready_for_command": True,
            "in_game": True,
            "game_state": {
                "choice_list": choice_list,
                "screen_type": "EVENT",
                "screen_state": {
                    "event_id": event_id,
                    "event_name": event_name,
                    "body_text": "",
                    "options": options,
                },
                "deck": [],
                "relics": [],
                "max_hp": 72,
                "current_hp": 72,
                "gold": 0,
                "floor": 41,
                "act": 2,
                "room_type": "EventRoom",
                "class": "WATCHER",
                "map": [],
                "potions": [],
            },
        }
        return GameState(state_dict, TheBotsMemoryBook.new_default())

    def test_handler_passes_desired_and_deck_data(self):
        from unittest import mock

        from rs.common.handlers.common_event_handler import CommonEventHandler

        # Strategy wants talk to the hand; the event offers judgement first.
        state = self._state(
            "Match and Keep!", "????", ["judgement", "talk to the hand", "card2"], self._opts(3)
        )
        handler = CommonEventHandler([], {"talk to the hand": 1})
        with mock.patch(
            "rs.common.handlers.common_event_handler.match_and_keep_choice",
            return_value=1,
        ) as patched:
            action = handler.handle(state)
        # It must have been called with the strategy tables, not just the choice list.
        kwargs = patched.call_args.kwargs
        self.assertEqual(kwargs.get("cards_desired_for_deck"), {"talk to the hand": 1})
        # deck counts come from the live state, not a pre-built constant.
        labeled_deck = kwargs.get("deck_card_counts")
        self.assertIn("deck_card_counts", kwargs)
        self.assertEqual(labeled_deck, state.get_deck_card_list_by_name_with_upgrade_stripped())
        self.assertIsNotNone(action)

    def test_handler_resolves_event_choice_only_once(self):
        from unittest import mock

        from rs.common.handlers.common_event_handler import CommonEventHandler

        state = self._state("Match and Keep!", "????", ["card0", "card1"], self._opts(2))
        handler = CommonEventHandler([], {})
        with mock.patch.object(handler, "find_event_choice", return_value="choose 0") as decision:
            action = handler.handle(state)

        decision.assert_called_once_with(state)
        self.assertEqual(action.commands, ["choose 0", "wait 30"])

    @staticmethod
    def _opts(n, labels=None):
        out = []
        for i in range(n):
            text = labels[i] if labels else "[" + str(i) + "]"
            out.append({"choice_index": i, "disabled": False, "text": text})
        return out
