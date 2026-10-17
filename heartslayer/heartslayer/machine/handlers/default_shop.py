from heartslayer.game.screen_type import ScreenType
from heartslayer.machine.handlers.handler import Handler
from heartslayer.machine.handlers.handler_action import HandlerAction
from heartslayer.machine.state import GameState


class DefaultShopHandler(Handler):

    def can_handle(self, state: GameState) -> bool:
        return state.screen_type() == ScreenType.SHOP_ROOM.value

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        return HandlerAction(commands=["proceed"])
