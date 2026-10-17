from calculator.calculator_test_fixture import CalculatorTestFixture
from rs.calculator.enums.card_id import CardId
from rs.calculator.enums.power_id import PowerId
from rs.common.comparators.common_general_comparator import CommonGeneralComparator
from rs.common.comparators.core.assessment import ComparatorAssessment
from rs.common.comparators.core.comparisons import avoid_inconvenient_time_warp, least_incoming_damage_over_1


class FakeAssessment:
    def __init__(self, incoming_damage: int):
        self._incoming_damage = incoming_damage

    def incoming_damage(self) -> int:
        return self._incoming_damage


class ComparisonFunctionsTest(CalculatorTestFixture):

    def test_least_incoming_damage_over_1_compares_three_against_ten(self):
        # 3 vs 10 must NOT tie: the max(2, ...) flatten only covers values of 2 or less.
        self.assertFalse(least_incoming_damage_over_1(FakeAssessment(3), FakeAssessment(10)))
        self.assertTrue(least_incoming_damage_over_1(FakeAssessment(10), FakeAssessment(3)))

    def test_least_incoming_damage_over_1_flattens_only_values_of_two_or_less(self):
        self.assertIsNone(least_incoming_damage_over_1(FakeAssessment(0), FakeAssessment(1)))
        self.assertIsNone(least_incoming_damage_over_1(FakeAssessment(0), FakeAssessment(2)))
        self.assertIsNone(least_incoming_damage_over_1(FakeAssessment(1), FakeAssessment(2)))
        self.assertFalse(least_incoming_damage_over_1(FakeAssessment(1), FakeAssessment(3)))
        self.assertFalse(least_incoming_damage_over_1(FakeAssessment(2), FakeAssessment(3)))

    def test_inconvenient_time_warp_count_is_true_only_when_time_warp_is_ten_or_eleven(self):
        for amount in [0, 9, 10, 11, 12]:
            state = self.given_state(CardId.STRIKE_R)
            state.monsters[0].powers[PowerId.TIME_WARP] = amount
            assessment = ComparatorAssessment(state, state, CommonGeneralComparator().assessment_config)
            expected = amount in (10, 11)
            self.assertEqual(expected, assessment.inconvenient_time_warp_count(),
                             f"expected inconvenient_time_warp_count {expected} for Time Warp {amount}")

    def test_avoid_inconvenient_time_warp_prefers_count_outside_ten_or_eleven(self):
        assessment_config = CommonGeneralComparator().assessment_config

        def assessment_with(time_warp: int):
            state = self.given_state(CardId.STRIKE_R)
            state.monsters[0].powers[PowerId.TIME_WARP] = time_warp
            return ComparatorAssessment(state, state, assessment_config)

        # 10 (inconvenient) vs 9 (fine): challenger wins
        self.assertTrue(avoid_inconvenient_time_warp(assessment_with(10), assessment_with(9)))
        # 11 (inconvenient) vs 12 (past the window): challenger wins
        self.assertTrue(avoid_inconvenient_time_warp(assessment_with(11), assessment_with(12)))
        # 9 vs 11: best (9) wins, challenger loses
        self.assertFalse(avoid_inconvenient_time_warp(assessment_with(9), assessment_with(11)))
        # both inconvenient (10 vs 11): tie -> None
        self.assertIsNone(avoid_inconvenient_time_warp(assessment_with(10), assessment_with(11)))