from typing import List

from heartslayer.game.screen_type import ScreenType
from heartslayer.machine.command import Command
from heartslayer.machine.handlers.handler import Handler
from heartslayer.machine.handlers.handler_action import HandlerAction
from heartslayer.machine.state import GameState


class CommonShopEntranceHandler(Handler):

    def can_handle(self, state: GameState) -> bool:
        return state.has_command(Command.CHOOSE) \
               and state.screen_type() == ScreenType.SHOP_ROOM.value

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        return HandlerAction(commands=["choose shop", "wait 30"])
