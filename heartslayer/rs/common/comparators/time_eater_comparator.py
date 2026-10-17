"""Comparator for the Time Eater fight (floor 50).

Why this file exists as its own class: the Time Warp-aware comparison below must be visible
*only* to Time Eater fights. `BigFightComparator` is inherited by the other big-fight bosses
(Deca/Donu, Awakened One), where no monster carries the Time Warp power, so they would simply
see the comparison return None and behave exactly as before.

Placement note: `least_time_warp_risk` is inserted AFTER `avoid_inconvenient_time_warp`
(intentionally below it), so the existing binary "stop playing at 10/11" rule still wins when
it applies and the graded horizon only breaks ties in the 8/9 window. The relative order of
every other comparison is untouched.
"""
from rs.common.comparators.big_fight_comparator import BigFightComparator, comparisons as big_fight_comparisons
from rs.common.comparators.common_general_comparator import add_to_comparison_list
from rs.common.comparators.core.comparisons import avoid_inconvenient_time_warp, least_time_warp_risk

comparisons = big_fight_comparisons.copy()
add_to_comparison_list(comparisons, comparison_to_add=least_time_warp_risk,
                      after=avoid_inconvenient_time_warp)


class TimeEaterComparator(BigFightComparator):

    def __init__(self):
        super().__init__()
        self.comparisons = comparisons
