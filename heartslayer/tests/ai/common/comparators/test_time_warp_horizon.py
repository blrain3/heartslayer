from heartslayer.common.comparators.core.comparisons import least_time_warp_risk  # noqa: F401 (RED step)
from calculator.calculator_test_fixture import CalculatorTestFixture
from heartslayer.calculator.enums.card_id import CardId
from heartslayer.calculator.enums.power_id import PowerId
from heartslayer.common.comparators.common_general_comparator import CommonGeneralComparator
from heartslayer.common.comparators.core.assessment import ComparatorAssessment
from heartslayer.common.comparators.core.comparisons import avoid_inconvenient_time_warp


class TimeWarpHorizonTest(CalculatorTestFixture):

    def given_assessment(self, card_id: CardId = CardId.STRIKE_R) -> ComparatorAssessment:
        state = self.given_state(card_id)
        return ComparatorAssessment(state, state, CommonGeneralComparator().assessment_config)

    def set_warp(self, assessment: ComparatorAssessment, amount: int) -> None:
        assessment.state.monsters[0].powers[PowerId.TIME_WARP] = amount

    # ---------- horizon semantics ----------

    def test_horizon_is_none_without_time_warp(self):
        a = self.given_assessment()
        self.assertIsNone(a.time_warp_horizon())

    def test_horizon_is_twelve_minus_counter(self):
        for amount, expected in [(0, 12), (5, 7), (8, 4), (9, 3), (10, 2), (11, 1)]:
            a = self.given_assessment()
            self.set_warp(a, amount)
            self.assertEqual(expected, a.time_warp_horizon(),
                             f"horizon for warp {amount} should be {expected}")

    def test_horizon_is_zero_at_or_above_twelve(self):
        for amount in (12, 13):
            a = self.given_assessment()
            self.set_warp(a, amount)
            self.assertEqual(0, a.time_warp_horizon())

    def test_horizon_takes_the_minimum_across_monsters(self):
        from heartslayer.calculator.monster import Monster
        a = self.given_assessment()
        extra = Monster(False, 100, 100, 0, {}, name="Second")
        a.state.monsters.append(extra)
        a.state.monsters[0].powers[PowerId.TIME_WARP] = 4
        self.set_warp(a, 9)
        # monsters[0] horizon = 8, monsters[1] horizon = 3 -> minimum is 3
        self.assertEqual(3, a.time_warp_horizon())

    # ---------- existing behaviour must NOT change ----------

    def test_inconvenient_time_warp_count_still_true_only_for_ten_or_eleven(self):
        for amount in [0, 8, 9, 10, 11, 12]:
            a = self.given_assessment()
            self.set_warp(a, amount)
            self.assertEqual(amount in (10, 11), a.inconvenient_time_warp_count(),
                             f"inconvenient_time_warp_count for warp {amount}")

    def test_avoid_inconvenient_time_warp_unchanged_at_eight_and_nine(self):
        a8 = self.given_assessment()
        self.set_warp(a8, 8)
        a9 = self.given_assessment()
        self.set_warp(a9, 9)
        # both "not inconvenient" -> tie, exactly as before the change
        self.assertIsNone(avoid_inconvenient_time_warp(a8, a9))
        self.assertIsNone(avoid_inconvenient_time_warp(a9, a8))

    def test_avoid_inconvenient_time_warp_still_fires_at_ten_and_eleven(self):
        a11 = self.given_assessment()
        self.set_warp(a11, 11)
        a10 = self.given_assessment()
        self.set_warp(a10, 10)
        a9 = self.given_assessment()
        self.set_warp(a9, 9)
        self.assertTrue(avoid_inconvenient_time_warp(a11, a9))
        self.assertTrue(avoid_inconvenient_time_warp(a10, a9))


class LeastTimeWarpRiskTest(CalculatorTestFixture):
    """The new, local comparison. Only Time Eater fights should ever see it active."""

    def given_assessment(self) -> ComparatorAssessment:
        state = self.given_state(CardId.STRIKE_R)
        return ComparatorAssessment(state, state, CommonGeneralComparator().assessment_config)

    def test_inert_without_time_warp(self):
        a = self.given_assessment()
        b = self.given_assessment()
        self.assertIsNone(least_time_warp_risk(a, b))

    def test_inert_when_horizons_are_equal(self):
        a = self.given_assessment()
        b = self.given_assessment()
        a.state.monsters[0].powers[PowerId.TIME_WARP] = 4
        b.state.monsters[0].powers[PowerId.TIME_WARP] = 4
        self.assertIsNone(least_time_warp_risk(a, b))

    def test_prefers_the_larger_horizon(self):
        a = self.given_assessment()
        b = self.given_assessment()
        a.state.monsters[0].powers[PowerId.TIME_WARP] = 5   # horizon 7
        b.state.monsters[0].powers[PowerId.TIME_WARP] = 9   # horizon 3
        self.assertFalse(least_time_warp_risk(a, b))
        self.assertTrue(least_time_warp_risk(b, a))

    def test_clamped_floor_of_zero_is_still_a_difference(self):
        a = self.given_assessment()
        b = self.given_assessment()
        a.state.monsters[0].powers[PowerId.TIME_WARP] = 12
        b.state.monsters[0].powers[PowerId.TIME_WARP] = 13
        self.assertIsNone(least_time_warp_risk(a, b))
