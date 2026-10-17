from typing import List

from presentation_config import presentation_mode, p_delay, p_delay_s
from rs.machine.command import Command
from rs.machine.handlers.handler import Handler
from rs.machine.handlers.handler_action import HandlerAction
from rs.machine.state import GameState


class CommonUpgradeHandler(Handler):

    def __init__(self, priorities: List[str]):
        self.upgrade_priorities: List[str] = priorities

    def can_handle(self, state: GameState) -> bool:
        return state.has_command(Command.CHOOSE) \
               and state.game_state()["screen_type"] == "GRID" \
               and state.game_state()["screen_state"]["for_upgrade"]

    def transform_priorities_based_on_game_state(self, priorities: List[str], state: GameState):
        # can be implemented by children
        pass

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        choice_list = state.game_state()["choice_list"]

        # we have to copy this, otherwise it will modify the list until the bot is rerun
        transformed_priorities = self.upgrade_priorities.copy()
        self.transform_priorities_based_on_game_state(transformed_priorities, state)

        # Unchanged path: a UI whose card names are readable matches by name, exactly as
        # before.
        for priority in transformed_priorities:
            if priority in choice_list:
                if presentation_mode:
                    return HandlerAction(commands=[p_delay, "choose " + priority, p_delay_s])
                return HandlerAction(commands=["choose " + priority])

        # NOTE (local fix): on a non-English UI `choice_list` holds localized names, so
        # every entry is "??" and none of the priorities above can match -- the old code
        # then sent "choose ??" and the game rejected it ("Invalid argument ?? in
        # command"), leaving the run stuck. `screen_state['cards'][i]['id']` is the
        # stable identifier and its index lines up with `choice_list`, so retry by id and
        # send the index instead. Reached only when name matching found nothing, so the
        # English behaviour above is untouched.
        cards = (state.game_state().get("screen_state") or {}).get("cards") or []
        for priority in transformed_priorities:
            for i, card in enumerate(cards):
                # card ids are CamelCase in the game payload ("Eruption"), while the
                # priority lists use the lower-case CardId values ("eruption"), so
                # compare case-insensitively.
                if (card.get("id") or "").lower() == priority.lower() and i < len(choice_list):
                    if presentation_mode:
                        return HandlerAction(commands=[p_delay, "choose " + str(i), p_delay_s])
                    return HandlerAction(commands=["choose " + str(i)])

        # Nothing matched: index 0 is valid in every language, unlike choice_list[0].
        if not choice_list:
            return HandlerAction(commands=[])
        if presentation_mode:
            return HandlerAction(commands=[p_delay, "choose 0", p_delay_s])
        return HandlerAction(commands=["choose 0"])
