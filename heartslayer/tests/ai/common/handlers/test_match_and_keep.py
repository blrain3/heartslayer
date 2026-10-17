"""Tests for match-and-keep event recognition and card choice.

Covers (per user requirement):
- reliable recognition that does NOT depend on the localized `event_name`
  (English "Match and Keep!" vs enum "Match and Keep"; Chinese UI -> "????")
- choice logic that inspects the ACTUAL choice_list / card content instead of
  a fixed index
- avoids Normality and Deep Breath; prefers real cards; handles Leave
"""
import unittest

from rs.machine.state import GameState
from test_helpers.resources import load_resource_state


class TestMatchAndKeepRecognition(unittest.TestCase):
    """Recognition must work off event_id, not the localized event_name."""

    def _state(self, event_id, event_name, choice_list, options):
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
                "floor": 2,
                "act": 1,
                "room_type": "EventRoom",
                "class": "WATCHER",
                "map": [],
                "potions": [],
            },
        }
        # GameState expects the parsed dict (see rs/machine/state.py:17 `json_state["game_state"]`
        # and tests/test_helpers/resources.py which passes json.loads(...)).
        return GameState(state_dict, TheBotsMemoryBook.new_default())

    @staticmethod
    def _opts(n, labels=None):
        out = []
        for i in range(n):
            label = labels[i] if labels and i < len(labels) else f"card{i}"
            out.append({"choice_index": i, "disabled": False, "text": label, "label": label})
        return out

    # ---- recognition -----------------------------------------------------

    def test_is_match_and_keep_true_for_english_localization(self):
        from rs.common.handlers.common_event_handler import is_match_and_keep
        state = self._state("Match and Keep!", "Match and Keep!", ["card0"], self._opts(1))
        self.assertTrue(is_match_and_keep(state))

    def test_is_match_and_keep_true_for_missing_localization(self):
        # The Chinese UI produces '????' for event_name; recognition must survive it.
        from rs.common.handlers.common_event_handler import is_match_and_keep
        state = self._state("Match and Keep!", "????", ["card0"], self._opts(1))
        self.assertTrue(is_match_and_keep(state))

    def test_is_match_and_keep_does_not_read_event_name(self):
        """event_name is localized; recognition must not depend on it at all.

        Log-verified: the Chinese UI reports event_name == '????' while event_id stays
        'Match and Keep!'. The id must be sufficient, and the name must not create matches.
        """
        from rs.common.handlers.common_event_handler import is_match_and_keep
        # The name alone cannot make it True.
        state = self._state("", "Match and Keep!", ["card0"], self._opts(1))
        self.assertFalse(is_match_and_keep(state))
        state = self._state("", "????", ["card0"], self._opts(1))
        self.assertFalse(is_match_and_keep(state))
        # The id alone must be enough.
        state = self._state("Match and Keep!", "????", ["card0"], self._opts(1))
        self.assertTrue(is_match_and_keep(state))

    def test_is_match_and_keep_false_for_other_events(self):
        from rs.common.handlers.common_event_handler import is_match_and_keep
        for eid, name in [("Nest", "The Nest"), ("Scrap Ooze", "Scrap Ooze"), ("Bonfire Elementals", "????")]:
            with self.subTest(event_id=eid):
                state = self._state(eid, name, ["land"], self._opts(1))
                self.assertFalse(is_match_and_keep(state))

    def test_recognition_is_localization_independent(self):
        # All three localized/raw spellings of the name must agree.
        from rs.common.handlers.common_event_handler import is_match_and_keep
        for event_name in ("Match and Keep!", "????", "Match and Keep"):
            with self.subTest(event_name=event_name):
                state = self._state("Match and Keep!", event_name, ["card0"], self._opts(1))
                self.assertTrue(is_match_and_keep(state))

    def test_recognition_survives_odd_event_id_values(self):
        """event_id missing / None / unrelated -> no crash, no false match.
        Casing: the id is compared lowercased, so any case of the real id still matches."""
        from rs.common.handlers.common_event_handler import is_match_and_keep
        for event_id in ("", None, "Some Other Event"):
            with self.subTest(event_id=event_id):
                state = self._state(event_id, "????", ["card0"], self._opts(1))
                self.assertFalse(is_match_and_keep(state))
        for event_id in ("MATCH AND KEEP!", "match and KEEP!"):
            with self.subTest(event_id=event_id):
                state = self._state(event_id, "????", ["card0"], self._opts(1))
                self.assertTrue(is_match_and_keep(state))

    def test_choice_handles_non_string_entries(self):
        """choice_list entries are not guaranteed to be strings."""
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        self.assertEqual(match_and_keep_choice([None, "card1"]), 1)
        self.assertEqual(match_and_keep_choice([0, "normality", "card2"]), 2)

    def test_choice_when_only_curses_and_leave_remain(self):
        """Both cards unwanted but only one is a real card -> that card (screen forces a choice)."""
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        self.assertEqual(match_and_keep_choice(["normality", "leave"]), 0)

    # ---- choice logic ----------------------------------------------------
    def test_choice_avoids_normality_and_deep_breath(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        # The real A0 log shape: curses sit at index 0 and 1.
        choices = ["normality", "deep breath", "card2", "card3", "card4", "card5"]
        idx = match_and_keep_choice(choices)
        self.assertEqual(idx, 2)  # first real card
        self.assertNotIn(choices[idx], ("normality", "deep breath"))

    def test_choice_prefers_first_non_cursed_card(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        choices = ["card0", "normality", "card2"]
        self.assertEqual(match_and_keep_choice(choices), 0)

    def test_choice_handles_deep_breath_even_though_it_is_not_a_curse_type(self):
        # Deep Breath is a SKILL, not a CURSE card type, so a naive type check misses it.
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        choices = ["deep breath", "card1"]
        self.assertEqual(match_and_keep_choice(choices), 1)

    def test_choice_recognizes_upgraded_curses(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        choices = ["normality+", "deep breath+", "card2"]
        self.assertEqual(match_and_keep_choice(choices), 2)

    def test_choice_is_stable_when_only_curses_are_left(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        # Only cursed options remain -> no good answer; must not crash, must pick something.
        choices = ["normality", "deep breath"]
        self.assertIn(match_and_keep_choice(choices), (0, 1))

    def test_choice_is_stable_for_placeholder_card_names(self):
        """Log-proven: CommunicationMod exposes face-down cards as 'cardN' (10H474B3AGLVI L117-162).
        Those must yield a valid index, never crash."""
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        self.assertEqual(match_and_keep_choice(["card0", "card1", "card2"]), 0)
        self.assertEqual(match_and_keep_choice(["card1", "card2", "card3"]), 0)
        self.assertEqual(match_and_keep_choice(["normality", "deep breath", "card2"]), 2)

    def test_choice_skips_face_down_placeholders(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        # Face-down cards report as 'cardN' placeholders.
        choices = ["card0", "card1", "card2", "card3", "card4", "card5"]
        self.assertEqual(match_and_keep_choice(choices), 0)

    def test_choice_returns_none_for_leave_only(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        # 'leave' is not a card -> caller must fall back to its own default.
        self.assertIsNone(match_and_keep_choice(["leave"]))

    def test_choice_returns_none_for_empty_list(self):
        from rs.common.handlers.common_event_handler import match_and_keep_choice
        self.assertIsNone(match_and_keep_choice([]))


class TestMatchAndKeepHandlerIntegration(unittest.TestCase):
    """End-to-end: the CommonEventHandler must actually pick a real card."""

    def _fixture_path(self, body):
        import json
        import os

        name = "event_match_and_keep_" + body + ".json"
        return "/event/" + name, name

    def test_handler_avoids_curse_in_english(self):
        path, _ = self._fixture_path("english")
        from rs.ai._example.handlers.event_handler import EventHandler
        from rs.machine.the_bots_memory_book import TheBotsMemoryBook

        state = load_resource_state(path)
        handler = EventHandler([], {})
        action = handler.handle(state)
        self.assertIn(action.commands[0], ("choose 2", "choose 3", "choose 4"))
        self.assertNotEqual(action.commands[0], "choose 0")

    def test_handler_avoids_curse_when_event_name_is_unreadable(self):
        # Chinese UI: event_name == '????'. Recognition must fall back to event_id.
        from rs.ai._example.handlers.event_handler import EventHandler

        state = load_resource_state("/event/event_match_and_keep_chinese_ui.json")
        action = EventHandler([], {}).handle(state)
        self.assertIn(action.commands[0], ("choose 2", "choose 3", "choose 4", "choose 5"))
        self.assertNotEqual(action.commands[0], "choose 0")

    def test_handler_avoids_deep_breath_which_is_not_a_curse_type(self):
        from rs.ai._example.handlers.event_handler import EventHandler

        state = load_resource_state("/event/event_match_and_keep_deep_breath_only.json")
        action = EventHandler([], {}).handle(state)
        self.assertIn(action.commands[0], ("choose 1", "choose 2"))
        self.assertNotEqual(action.commands[0], "choose 0")

    def test_handler_does_not_crash_on_leave_screen(self):
        from rs.ai._example.handlers.event_handler import EventHandler

        state = load_resource_state("/event/event_match_and_keep_leave_only.json")
        # Single option -> handler's single-choice path should take it.
        action = EventHandler([], {}).handle(state)
        self.assertIsNotNone(action)
        self.assertEqual(action.commands[0], "choose 0")
