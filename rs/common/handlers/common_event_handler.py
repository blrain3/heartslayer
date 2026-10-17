from presentation_config import presentation_mode, p_delay, p_delay_s, slow_events
from rs.game.event import Event
from rs.game.screen_type import ScreenType
from rs.helper.logger import log_missing_event
from rs.machine.command import Command
from rs.machine.handlers.handler import Handler
from rs.machine.handlers.handler_action import HandlerAction
from rs.machine.state import GameState

# CommunicationMod reports the event's internal id as "Match and Keep!" while the Event enum
# stores the display name "Match and Keep". `event_name` is localized, so it is NOT used for
# recognition (it is "????" under a Chinese UI); only `event_id` is.
# The id spelling is log-verified (e.g. 10H474B3AGLVI.log: event_id == "Match and Keep!").
match_and_keep_event_ids = ("match and keep!",)

# Cards we never want to draw from a "Match and Keep" screen.
# NOTE: Normality is a CURSE, but Deep Breath is a SKILL, so a CardType.CURSE check alone is not
# enough -- this list has to be explicit. Compared with any trailing '+' stripped.
match_and_keep_unwanted_cards = (
    "normality",
    "deep breath",
)


def is_match_and_keep(state: GameState) -> bool:
    """Recognize the Match and Keep event.

    Deliberately does NOT read `event_name`: it is localized (English "Match and Keep!" vs
    Chinese "????") and cannot identify this event reliably.
    """
    screen_state = state.screen_state()
    event_id = str(screen_state.get("event_id", "") or "").strip().lower()
    return event_id in match_and_keep_event_ids


def match_and_keep_choice(
    choice_list: list,
    cards_desired_for_deck: dict | None = None,
    deck_card_counts: dict | None = None,
) -> int | None:
    """Pick which card to take from the current Match and Keep screen.

    Ranked by what the strategy already knows, so no card name has to be hard-coded:

    1. A card the strategy wants and has not yet reached its desired count for. This reuses the
       same `cards_desired_for_deck` / deck-count logic as `CommonCardRewardHandler`, so the
       event agrees with card rewards about what is worth having.
    2. A face-down 'cardN' placeholder. Unknown, so it can still turn out to be a wanted card.
    3. A card known to not be wanted -- taken only when nothing unknown is left, since the
       screen forces a choice.
    4. A curse. Truly last resort, and only when the screen offers nothing else.
    Returns None when there is no card entry at all (e.g. only 'leave'); the extra parameters
    are optional so older callers keep working.
    """
    if cards_desired_for_deck is None:
        cards_desired_for_deck = {}
    if deck_card_counts is None:
        deck_card_counts = {}

    def normalize(choice) -> str:
        # Same normalization as rs/machine/state.py get_choice_list(); kept identical on purpose.
        return str(choice or "").strip().lower().replace("+", "")

    desired_index = None
    placeholder_index = None
    unwanted_index = None  # known card the strategy does not want
    curse_index = None  # only reached when nothing else remains on screen

    for idx, choice in enumerate(choice_list):
        name = normalize(choice)
        if not name or name == "leave":
            continue
        if name in match_and_keep_unwanted_cards:
            if curse_index is None:
                curse_index = idx
            continue
        if unwanted_index is None:
            unwanted_index = idx  # first known-but-not-wanted card: second worst
        if name.startswith("card") and name[4:].isdigit():
            if placeholder_index is None:
                placeholder_index = idx
            continue
        if desired_index is None and deck_card_counts.get(name, 0) < cards_desired_for_deck.get(name, 0):
            desired_index = idx

    # A hidden slot remains exploratory; do not take an already revealed card first.
    for candidate in (desired_index, placeholder_index, unwanted_index, curse_index):
        if candidate is not None:
            return candidate
    return None


class CommonEventHandler(Handler):

    def __init__(self, removal_priority_list, cards_desired_for_deck):
        self.removal_priority_list = removal_priority_list.copy()
        self.cards_desired_for_deck = cards_desired_for_deck.copy()

    def can_handle(self, state: GameState) -> bool:
        return state.screen_type() == ScreenType.EVENT.value and state.has_command(Command.CHOOSE)

    def handle(self, state: GameState, slay_heart: bool = False) -> HandlerAction:

        if len(state.get_choice_list()) == 1:  # If there's just one option, take it.
            if presentation_mode or slow_events:
                return HandlerAction(commands=[p_delay, "choose 0", "wait 30"])
            return HandlerAction(commands=["choose 0", "wait 30"])

        # Resolve once: event decisions can inspect and normalize the full state.
        choice = self.find_event_choice(state)
        if choice:
            if presentation_mode or slow_events:
                return HandlerAction(commands=[p_delay, choice, p_delay_s])
            return HandlerAction(commands=[choice, "wait 30"])

    def find_event_choice(self, state: GameState) -> str:
        hp_per = state.get_player_health_percentage() * 100
        event = state.get_event()

        # Matched before the `match` below: `event_name` is localized and cannot be trusted,
        # so Match and Keep is recognized via the language-independent event_id / choice_list.
        if is_match_and_keep(state):
            choice = match_and_keep_choice(
                state.get_choice_list(),
                cards_desired_for_deck=self.cards_desired_for_deck,
                deck_card_counts=state.get_deck_card_list_by_name_with_upgrade_stripped(),
            )
            if choice is not None:
                return "choose " + str(choice)
            return None

        match event:

            case Event.BIG_FISH:
                if hp_per <= 30:
                    return "choose 0"  # heal
                if state.get_relic_counter("Omamori") >= 1:
                    return "choose 2"  # relic and curse
                return "choose 1"  # max health up

            case Event.THE_CLERIC:
                if hp_per <= 65 and 'heal' in state.get_choice_list():
                    return "choose heal"
                if 'purify' in state.get_choice_list():
                    return "choose purify"  # Purge
                if hp_per >= 90:
                    return "choose leave"  # Heal not worth the money and can't purify apparently
                return "choose 0"

            case Event.DEAD_ADVENTURER:
                return "choose 1"  # Escape. Could do: Add logic for sometimes taking the fight.

            case Event.GOLDEN_IDOL:
                if state.has_relic("Ectoplasm"):
                    return "choose 1"  # Leave!
                if len(state.get_choice_list()) == 2:
                    return "choose 0"  # Take it!
                if len(state.get_choice_list()) == 3:
                    if state.get_relic_counter("Omamori") >= 1:
                        return "choose 0"  # curse
                    if hp_per >= 90:
                        return "choose 1"  # 25% (35%) damage
                    return "choose 2"  # max hp loss

            case Event.HYPNOTIZING_MUSHROOMS:
                if hp_per >= 40:
                    return "choose 0"  # Get 'em!
                return "choose 1" # Take the heal and curse

            case Event.LIVING_WALL:
                return "choose 2"  # Upgrade

            case Event.SCRAP_OOZE:
                return "choose 0"  # Yolo. We'll probably get it after a few tries? If not, we don't deserve to live!!

            case Event.SHINING_LIGHT:
                if hp_per >= 70:
                    return "choose 0"  # Take the 2 random upgrades.
                return "choose 1"  # Leave.

            case Event.THE_SSSSSERPENT:
                if state.get_relic_counter("Omamori") >= 1 and not state.has_relic("Ectoplasm"):
                    return "choose 0"  # Money in exchange for a curse
                return "choose 1"  # Leave

            case Event.WORLD_OF_GOOP:
                if hp_per >= 80 and not state.has_relic("Ectoplasm"):
                    return "choose 0"  # Take the money and lose a little HP.
                return "choose 1"  # Leave

            case Event.WING_STATUE:
                if hp_per >= 70:
                    return "choose 0"  # Purge at cost of 7 HP
                return "choose 1"  # Money or leave

            # ACT 1, 2

            case Event.FACE_TRADER:
                if hp_per >= 75 and not state.has_relic("Ectoplasm"):
                    return "choose 0"
                return "choose 2"  # Leave.

            # ACT 1, 2, 3

            case Event.A_NOTE_FOR_YOURSELF:
                return "choose 1"  # Ignore.

            case Event.BONFIRE_SPIRITS:
                return "choose 0"  # Purge

            case Event.THE_DIVINE_FOUNTAIN:
                return "choose 0"  # Remove curses!

            case Event.DUPLICATOR:
                return "choose 1"  # Needs some duplication logic, would be better, but for now leave.

            case Event.GOLDEN_SHRINE:
                if state.get_relic_counter("Omamori") >= 1 and not state.has_relic("Ectoplasm"):
                    return "choose 1"  # More free money!
                return "choose 0"  # Free money

            case Event.LAB:
                return "choose 0"  # Free potions

            case Event.MATCH_AND_KEEP:
                return "choose 0"  # Just keep clicking

            case Event.OMINOUS_FORGE:
                if state.get_relic_counter("Omamori") >= 1:
                    return "choose 1"  # Warped tongs!
                if state.floor() >= 30:
                    return "choose 0"  # Might not be able to reasonably get rid of the curse anymore
                return "choose 1"  # I love the Warped Tongs relic.

            case Event.PURIFIER:
                return "choose 0"  # Purge

            case Event.TRANSMOGRIFIER:
                return "choose 1"  # Ignore the transform since we don't know all cards (depending on character)

            case Event.UPGRADE_SHRINE:
                return "choose 0"  # Free upgrade

            case Event.WE_MEET_AGAIN:
                return "choose 0" # Todo

            case Event.THE_WOMAN_IN_BLUE:
                return "choose 0"  # Grab 1 potion, or if we don't have enough money, leave.

            # ACT 2

            case Event.ANCIENT_WRITING:
                return "choose 1"  # Upgrade all strikes and defends always because we currently can't tell the difference between card selection and purging in a grid event.

            case Event.AUGMENTER:
                return "choose 2"  # Take the Mutagenic Strength relic.

            case Event.THE_COLOSSEUM:
                return "choose 0" # todo

            case Event.COUNCIL_OF_GHOSTS:
                if state.has_relic("Snecko Eye") or state.deck.contains_cards(["Bite"]):  # Not amazing combos:
                    return "choose refuse"
                return "choose accept"  # Become a spooky ghost!

            case Event.CURSED_TOME:
                return "choose 1"  # Leave, we don't currently make good use of the possible relics.

            case Event.FORGOTTEN_ALTAR:
                return "choose 0" # todo

            case Event.THE_JOUST:
                return "choose 0"  # Be conservative

            case Event.KNOWING_SKULL:
                return "choose 3"  # Leave

            case Event.THE_LIBRARY:
                return "choose sleep"  # Heal, because we currently can't tell the difference between card selection and purging in a grid event.

            case Event.MASKED_BANDITS:
                if hp_per >= 65:
                    return "choose 1"  # Get 'em!
                return "choose 0"  # Give up all money and leave.

            case Event.THE_MAUSOLEUM:
                if state.get_relic_counter("Omamori") >= 1:
                    return "choose 0"
                return "choose 1"  # Leave, we don't like curses.

            case Event.THE_NEST:
                return "choose 0"  # Free money. 1 would be Ritual Dagger and a little damage.

            case Event.NLOTH:
                return "choose 2"  # Leave, hard to statically make a good choice here.

            case Event.OLD_BEGGAR:
                return "choose 0"  # Cheap purge.

            case Event.PLEADING_VAGRANT:
                if state.get_relic_counter("Omamori") >= 1:
                    return "choose rob"  # Get curse and relic
                elif "offer gold" in state.get_choice_list():
                    return "choose offer gold"  # 85 gold for random relic
                else:
                    return "choose leave"

            case Event.VAMPIRES:
                if state.deck.contains_cards(["Apparition"]):
                    return "choose refuse"
                if state.has_relic("Strike Dummy"):
                    return "choose refuse"
                if state.deck.contains_card_amount("strike") >= 3:  # note: these are specifically un-upgraded strikes
                    if state.has_relic("Blood Vial"):
                        return "choose 1"  # Nom the Spire
                    else:
                        return "choose accept"
                return "choose refuse"

            # Act 2, 3

            case Event.DESIGNER_IN_SPIRE:
                return "choose 0"  # It'll do reasonable things like upgrading and removing.

            # Act 3

            case Event.FALLING:
                options = state.get_falling_event_options()

                # check for stuff we want to purge
                for least_desired in self.removal_priority_list:
                    if least_desired in options:
                        for idx, card in enumerate(options):
                            if card == least_desired:
                                return "choose " + str(idx)

                # check for cards not in the pickup list
                for idx, option in enumerate(options):
                    if option not in self.cards_desired_for_deck:
                        return "choose " + str(idx)

                # check for lowest card on the pickup list
                pickup_prios = list(self.cards_desired_for_deck.keys())
                pickup_prios.reverse()

                for least_desired in pickup_prios:
                    if least_desired in options:
                        for idx, card in enumerate(options):
                            if card == least_desired:
                                return "choose " + str(idx)

            case Event.MIND_BLOOM:
                return "choose 0"  # Fight an Act 1 boss for a relic.

            case Event.MIND_BLOOM:
                return "choose 1"  # Get a bunch of money or leave

            case Event.MYSTERIOUS_SPHERE:
                if hp_per >= 70:
                    return "choose 0"  # Get 'em!
                else:
                    return "choose 1"  # Leave

            case Event.SECRET_PORTAL:
                return "choose 1"  # Nope - we want the rest of Act 3 to not screw up our stats.

            case Event.SENSORY_STONE:
                return "choose 0"  # Get a free colorless obtain

            case Event.TOMB_OF_LORD_RED_MASK:
                if state.has_relic("Red Mask") or state.game_state()['gold'] <= 130:
                    return "choose 0"  # Either free money or cheap.
                else:
                    return "choose 1"  # Leave

            case Event.WINDING_HALLS:
                if state.get_relic_counter("Omamori") >= 1 and hp_per < 75:
                    return "choose 1"  # Take the curse and heal
                if hp_per <= 10:
                    return "choose 1"  # Take the curse and heal
                return "choose 2"  # Lose Max HP

            case _:
                log_missing_event(str(event))
                return "choose 0"
