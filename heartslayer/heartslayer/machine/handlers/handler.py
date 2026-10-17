from typing import Optional

from heartslayer.machine.handlers.handler_action import HandlerAction
from heartslayer.machine.state import GameState


class Handler:

    def can_handle(self, state: GameState) -> bool:
        return False

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        raise Exception("must be implemented by children")
