from dataclasses import dataclass, field

from heartslayer.calculator.executor import get_best_battle_action
from heartslayer.calculator.interfaces.comparator_interface import ComparatorInterface
from heartslayer.common.comparators.big_fight_comparator import BigFightComparator
from heartslayer.common.comparators.common_general_comparator import CommonGeneralComparator
from heartslayer.common.comparators.gremlin_nob_comparator import GremlinNobComparator
from heartslayer.common.comparators.shield_and_spear_comparator import ShieldAndSpearComparator  # 碎心移植：矛先于盾
from heartslayer.common.comparators.three_sentry_comparator import ThreeSentriesComparator
from heartslayer.common.comparators.three_sentry_turn_1_comparator import ThreeSentriesTurn1Comparator
from heartslayer.common.comparators.time_eater_comparator import TimeEaterComparator
from heartslayer.common.comparators.transient_comparator import TransientComparator
from heartslayer.common.comparators.waiting_lagavulin_comparator import WaitingLagavulinComparator
from heartslayer.game.card import CardType
from heartslayer.machine.command import Command
from heartslayer.machine.handlers.handler import Handler
from heartslayer.machine.handlers.handler_action import HandlerAction
from heartslayer.machine.state import GameState


@dataclass
class BattleHandlerConfig:
    big_fight_floors: list[int] = field(default_factory=lambda: [33, 50])
    big_fight_comparator: ComparatorInterface = BigFightComparator
    time_eater_comparator: ComparatorInterface = TimeEaterComparator
    gremlin_nob_comparator: ComparatorInterface = GremlinNobComparator
    three_sentries_comparator: ComparatorInterface = ThreeSentriesComparator
    three_sentries_turn_1_comparator: ComparatorInterface = ThreeSentriesTurn1Comparator
    transient_comparator: ComparatorInterface = TransientComparator
    shield_and_spear_comparator: ComparatorInterface = ShieldAndSpearComparator  # 碎心移植
    heart_fight_comparator: ComparatorInterface = BigFightComparator  # 碎心移植：心脏战可覆盖（默认=big fight）
    waiting_lagavulin_comparator: ComparatorInterface = WaitingLagavulinComparator
    general_comparator: ComparatorInterface = CommonGeneralComparator


class CommonBattleHandler(Handler):

    def __init__(self, config: BattleHandlerConfig = BattleHandlerConfig(), max_path_count: int = 11_000):
        self.config: BattleHandlerConfig = config
        self.max_path_count: int = max_path_count

    def can_handle(self, state: GameState) -> bool:
        return state.has_command(Command.PLAY) \
               or state.current_action() == "DiscardAction" \
               or state.current_action() == "ExhaustAction"

    def select_comparator(self, state: GameState) -> ComparatorInterface:
        alive_monsters = len(list(filter(lambda m: not m["is_gone"], state.get_monsters())))

        # 碎心移植：心脏战按 big fight 对待（id 口径，兼容本地化）。
        # CorruptHeart = 游戏本体内部 id（desktop-1.0.jar 常量核验，2026-10-05）
        corrupt_heart_is_present = state.has_monster("Corrupt Heart") or state.has_monster("CorruptHeart")

        big_fight = state.floor() in self.config.big_fight_floors \
                    or corrupt_heart_is_present

        gremlin_nob_is_present = state.has_monster("GremlinNob")

        three_sentries_are_alive_turn_1 = state.has_monster("Sentry") \
                                   and alive_monsters == 3 \
                                   and state.combat_state()['turn'] == 1

        three_sentries_are_alive = state.has_monster("Sentry") \
                                          and alive_monsters == 3

        lagavulin_is_sleeping = state.has_monster("Lagavulin") \
                                and state.combat_state()['turn'] <= 2 \
                                and not state.game_state()['room_type'] == "EventRoom"

        lagavulin_is_worth_delaying = state.deck.contains_type(CardType.POWER) \
                                      or state.deck.contains_cards(["Terror", "Terror+"]) \
                                      or state.deck.contains_cards(["Talk To The Hand", "Talk To The Hand+"]) \
                                      or state.has_relic("Warped Tongs") \
                                      or state.has_relic("Ice Cream")

        transient_is_present = state.has_monster("Transient") and alive_monsters == 1

        time_eater_is_present = state.has_monster("TimeEater")

        # 碎心移植：Spire Shield/Spear 战——盾还活着时用矛优先 comparator（id 口径；
        # SpireShield/SpireSpear 经游戏本体核验，空格形态为显示名兜底）
        spear_still_alive = (state.has_monster("Spire Shield") or state.has_monster("SpireShield")) \
                            and alive_monsters == 2

        if time_eater_is_present:
            return self.config.time_eater_comparator()
        elif corrupt_heart_is_present:
            return self.config.heart_fight_comparator()
        elif big_fight:
            return self.config.big_fight_comparator()
        elif gremlin_nob_is_present:
            return self.config.gremlin_nob_comparator()
        elif three_sentries_are_alive_turn_1:
            return self.config.three_sentries_turn_1_comparator()
        elif three_sentries_are_alive:
            return self.config.three_sentries_comparator()
        elif lagavulin_is_sleeping and lagavulin_is_worth_delaying:
            return self.config.waiting_lagavulin_comparator()
        elif transient_is_present:
            return self.config.transient_comparator()
        elif spear_still_alive:
            return self.config.shield_and_spear_comparator()
        return self.config.general_comparator()

    def handle(self, state: GameState, slay_heart: bool = False) -> HandlerAction:
        actions = get_best_battle_action(state, self.select_comparator(state), self.max_path_count)
        if actions:
            return actions
        if state.has_command(Command.END):
            return HandlerAction(commands=["end"], memory_book=None)
        return HandlerAction(commands=[], memory_book=None)
