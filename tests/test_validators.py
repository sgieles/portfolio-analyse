"""Unit tests for utils.validators."""

import pytest

from utils.validators import (
    validate_ticker,
    validate_weights_sum,
    validate_weight_value,
    validate_benchmark,
    validate_period,
    validate_portfolio_not_empty,
    WEIGHT_TOLERANCE,
)


class TestValidateTicker:
    def test_valid_simple(self):
        assert validate_ticker("AAPL") == "AAPL"

    def test_valid_with_dot(self):
        assert validate_ticker("BRK.B") == "BRK.B"

    def test_valid_with_hyphen(self):
        assert validate_ticker("BRK-B") == "BRK-B"

    def test_lowercase_normalised(self):
        assert validate_ticker("msft") == "MSFT"

    def test_leading_trailing_spaces_stripped(self):
        assert validate_ticker("  SPY  ") == "SPY"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Invalid ticker"):
            validate_ticker("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="Invalid ticker"):
            validate_ticker("TOOLONGTICKER")   # 13 chars

    def test_special_chars_raise(self):
        with pytest.raises(ValueError, match="Invalid ticker"):
            validate_ticker("APP!E")


class TestValidateWeightsSum:
    def test_exact_one(self):
        validate_weights_sum([0.5, 0.3, 0.2])  # should not raise

    def test_within_tolerance(self):
        validate_weights_sum([0.5, 0.5 + WEIGHT_TOLERANCE / 2])  # should not raise

    def test_just_outside_tolerance_raises(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            validate_weights_sum([0.5, 0.5 + WEIGHT_TOLERANCE * 2])

    def test_single_weight_one(self):
        validate_weights_sum([1.0])

    def test_zero_sum_raises(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            validate_weights_sum([0.0, 0.0])


class TestValidateWeightValue:
    def test_zero(self):
        validate_weight_value(0.0)

    def test_one(self):
        validate_weight_value(1.0)

    def test_mid(self):
        validate_weight_value(0.42)

    def test_above_one_raises(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            validate_weight_value(1.001)

    def test_below_zero_raises(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            validate_weight_value(-0.001)


class TestValidateBenchmark:
    def test_valid_spy(self):
        validate_benchmark("SPY")

    def test_valid_vti(self):
        validate_benchmark("VTI")

    def test_valid_acwi(self):
        validate_benchmark("ACWI")

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="not supported"):
            validate_benchmark("QQQ")


class TestValidatePeriod:
    @pytest.mark.parametrize("period", ["1y", "3y", "5y", "10y", "max"])
    def test_valid_periods(self, period: str):
        validate_period(period)

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="not supported"):
            validate_period("7y")


class TestValidatePortfolioNotEmpty:
    def test_non_empty_ok(self):
        validate_portfolio_not_empty(["AAPL", "MSFT"])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_portfolio_not_empty([])
