from heartslayer.machine.command import Command
from heartslayer.machine.handlers.handler import Handler
from heartslayer.machine.handlers.handler_action import HandlerAction
from heartslayer.machine.state import GameState


class DefaultCancelHandler(Handler):

    def can_handle(self, state: GameState) -> bool:
        return state.has_command(Command.CANCEL)

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        return HandlerAction(commands=["return"])
