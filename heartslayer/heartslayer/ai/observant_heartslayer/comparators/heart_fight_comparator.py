from typing import Optional

from heartslayer.common.comparators.big_fight_comparator import comparisons as big_fight_comparisons
from heartslayer.common.comparators.common_general_comparator import CommonGeneralComparator
from heartslayer.common.comparators.core.comparisons import least_incoming_damage_over_1
from heartslayer.common.comparators.core.assessment import ComparatorAssessment as CA

# 碎心战交换预算：允许单步最多多付 5 点净生命，换取对心脏的实质输出推进。
# 依据（离线回放，心脏局 XDMVJN end#2 等）：原评估把“免蹭伤”排在“击杀进度”之上，
# 会带能量空过（净损失 9 空过 vs 12 连打 6 张、推进 56 伤）。
HEART_TRADE_HP_BUDGET = 5


def trade_hp_for_damage(best: CA, challenger: CA) -> Optional[bool]:
    inc_best, inc_chal = best.incoming_damage(), challenger.incoming_damage()
    dmg_best, dmg_chal = best.total_monster_health(), challenger.total_monster_health()
    if abs(inc_best - inc_chal) <= HEART_TRADE_HP_BUDGET and dmg_best != dmg_chal:
        return dmg_chal < dmg_best
    return None


comparisons = big_fight_comparisons.copy()
comparisons.insert(comparisons.index(least_incoming_damage_over_1), trade_hp_for_damage)


class HeartFightComparator(CommonGeneralComparator):
    def __init__(self):
        super().__init__(comparisons)
