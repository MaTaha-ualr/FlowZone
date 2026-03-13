"""Tests for Safe Harbor protocol logic."""
import pytest
from app.core.safe_harbor import determine_floor, can_escalate
from app.core.constants import SafeHarborLevel


class TestDetermineFloor:
    def test_no_history_green(self):
        assert determine_floor(False, False) == SafeHarborLevel.GREEN

    def test_trauma_yellow(self):
        assert determine_floor(True, False) == SafeHarborLevel.YELLOW

    def test_crisis_yellow(self):
        assert determine_floor(False, True) == SafeHarborLevel.YELLOW

    def test_both_yellow(self):
        assert determine_floor(True, True) == SafeHarborLevel.YELLOW


class TestCanEscalate:
    def test_green_to_yellow(self):
        assert can_escalate(SafeHarborLevel.GREEN, SafeHarborLevel.YELLOW) is True

    def test_green_to_red(self):
        assert can_escalate(SafeHarborLevel.GREEN, SafeHarborLevel.RED) is True

    def test_yellow_to_red(self):
        assert can_escalate(SafeHarborLevel.YELLOW, SafeHarborLevel.RED) is True

    def test_no_deescalate_yellow_green(self):
        assert can_escalate(SafeHarborLevel.YELLOW, SafeHarborLevel.GREEN) is False

    def test_no_deescalate_red_yellow(self):
        assert can_escalate(SafeHarborLevel.RED, SafeHarborLevel.YELLOW) is False

    def test_same_level_not_escalation(self):
        assert can_escalate(SafeHarborLevel.GREEN, SafeHarborLevel.GREEN) is False
        assert can_escalate(SafeHarborLevel.RED, SafeHarborLevel.RED) is False
