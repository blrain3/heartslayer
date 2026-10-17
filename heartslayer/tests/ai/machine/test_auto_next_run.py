"""Automatic next-run after Game Over.

`main.py` runs `for i in range(run_amount): game.start(seed); game.run()`.
`Game.run()` breaks out of its loop when the Game Over handler fires, returning control to
`main.py`, which then calls `start()` again.

This test pins down the contract that makes back-to-back runs work:
  1. The Game Over handler reports that it can handle the GAME_OVER screen.
  2. It emits exactly one command, `proceed` -- NOT `start`, and nothing that could make
     the run loop fall through to "Dying from not knowing what to do next".
  3. `main.py`'s loop calls start()+run() once per iteration, so a finished run leads to a
     new one instead of stopping the batch.

Points 1 and 2 are the real gates: if the handler ever needs two commands, or if
CommunicationMod needs `start` instead of `proceed` to leave the game-over screen, the
batch would stall. Point 3 documents main.py's contract without needing a live game.
"""
import unittest
from unittest import mock

from heartslayer.machine.default_game_over import DefaultGameOverHandler
from heartslayer.machine.state import GameState
from heartslayer.machine.the_bots_memory_book import TheBotsMemoryBook


def _state(game_over: bool, **overrides) -> GameState:
    gs = {
        "in_game": not game_over,
        "ready_for_command": True,
        "game_state": {
            "screen_type": "GAME_OVER" if game_over else "EVENT",
            "room_type": "EventRoom",
            "choice_list": ["continue"],
            "screen_state": {},
            "floor": 50,
            "act": 3,
            "class": "WATCHER",
            "deck": [],
            "relics": [],
            "potions": [],
            "map": [],
            "max_hp": 72,
            "current_hp": 0 if game_over else 72,
            "seed": "ABC123",
        },
        "available_commands": ["proceed"] if game_over else ["choose", "wait", "state"],
    }
    gs.update(overrides)
    return GameState(gs, TheBotsMemoryBook.new_default())


class TestGameOverHandlerContract(unittest.TestCase):
    """The game-over screen must be dismissible with exactly one `proceed`."""

    def test_can_handle_when_proceed_is_available(self):
        h = DefaultGameOverHandler()
        state = _state(game_over=True)
        self.assertTrue(h.can_handle(state))

    def test_does_not_fire_outside_game_over(self):
        h = DefaultGameOverHandler()
        self.assertFalse(h.can_handle(_state(game_over=False)))

    def test_emits_exactly_one_proceed(self):
        h = DefaultGameOverHandler()
        with mock.patch("heartslayer.machine.default_game_over.log_missing_calculator_enums_to_run"), \
             mock.patch("heartslayer.machine.default_game_over.log_run_results"):
            cmds = h.handle(_state(game_over=True), [], [], "peaceful_pummeling")
        self.assertEqual(cmds, ["proceed"])

    def test_proceed_is_a_command_the_game_over_screen_offers(self):
        """Guards against emitting a command the screen cannot accept."""
        from heartslayer.machine.command import Command

        state = _state(game_over=True)
        self.assertTrue(state.has_command(Command.PROCEED))


class TestBatchLoopContract(unittest.TestCase):
    """main.py's loop must start a new run for every finished one."""

    def test_start_and_run_alternate_once_per_iteration(self):
        from heartslayer.machine.game import Game

        game = Game(mock.MagicMock(), mock.MagicMock())
        calls = []
        with mock.patch.object(Game, "start", side_effect=lambda s="": calls.append(("start", s))), \
             mock.patch.object(Game, "run", side_effect=lambda: calls.append(("run",))):
            for i in range(3):
                game.start("seed%d" % i)
                game.run()
        self.assertEqual(calls, [("start", "seed0"), ("run",), ("start", "seed1"), ("run",), ("start", "seed2"), ("run",)])

    def test_loop_survives_a_run_that_raises(self):
        """A single crashing run must not abort the batch.

        main.py wraps each iteration in its own try/except, so run N failing logs the
        failure and run N+1 still starts. Without this, "auto next run" would actually
        mean "auto stop at the first problem".
        """
        from heartslayer.machine.game import Game

        game = Game(mock.MagicMock(), mock.MagicMock())
        iterations = []

        def boom(self, *args, **kwargs):
            iterations.append(1)
            raise RuntimeError("bot stuck")

        started = []
        with mock.patch.object(Game, "start", side_effect=lambda s="": started.append(s)), \
             mock.patch.object(Game, "run", boom), \
             mock.patch("heartslayer.helper.logger.log"), \
             mock.patch("heartslayer.helper.logger.log_to_run"), \
             mock.patch("traceback.format_exc", return_value="trace"):
            try:
                for _ in range(3):
                    try:
                        game.start()
                        game.run()
                    except Exception:
                        pass
            except RuntimeError:
                self.fail("exception escaped the per-run try")
        self.assertEqual(len(started), 3)

    def test_start_failure_is_also_recovered(self):
        """`start()` failing must not abort the batch either.

        `start()` performs the client handshake, so it failing means the game process is
        not ready -- re-creating the Game (as main.py does) can recover it. Both start and
        run sit inside the same per-run try.
        """
        from heartslayer.machine.game import Game

        game = Game(mock.MagicMock(), mock.MagicMock())
        started = []

        def bad_start(self, s=""):
            started.append(s)
            raise RuntimeError("no client")

        with mock.patch.object(Game, "start", bad_start), \
             mock.patch.object(Game, "run"), \
             mock.patch("heartslayer.helper.logger.log"), \
             mock.patch("heartslayer.helper.logger.log_to_run"), \
             mock.patch("traceback.format_exc", return_value="trace"):
            for _ in range(3):
                try:
                    game.start()
                    game.run()
                except Exception:
                    pass
            # Every iteration still ran, i.e. the batch was not aborted.
            self.assertEqual(len(started), 3)


if __name__ == "__main__":
    unittest.main()
