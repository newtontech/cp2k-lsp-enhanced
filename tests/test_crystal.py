"""Tests for cp2k_input_tools/basissets/crystal.py"""

import pytest
from decimal import Decimal

from cp2k_input_tools.basissets.crystal import (
    BasisSetCoefficients,
    BasisSetData,
    BLOCK_MATCH,
)


class TestBlockMatch:
    """Test BLOCK_MATCH regex."""

    def test_block_match_valid(self):
        """Test valid block match."""
        match = BLOCK_MATCH.match("  1  2  ")
        assert match is not None

    def test_block_match_invalid(self):
        """Test invalid block match."""
        match = BLOCK_MATCH.match("H BASIS_SET")
        assert match is None


class TestBasisSetCoefficients:
    """Test BasisSetCoefficients model."""

    def test_creation(self):
        """Test creating BasisSetCoefficients."""
        coeff = BasisSetCoefficients(
            shell=0,
            charge=Decimal("1.0"),
            scaling=Decimal("1.0"),
            coefficients=[(Decimal("1.0"), Decimal("1.0"))]
        )
        assert coeff.shell == 0
        assert coeff.charge == Decimal("1.0")

    def test_multiple_coefficients(self):
        """Test with multiple coefficients."""
        coeff = BasisSetCoefficients(
            shell=1,
            charge=Decimal("2.0"),
            scaling=Decimal("1.0"),
            coefficients=[
                (Decimal("1.0"), Decimal("0.5")),
                (Decimal("2.0"), Decimal("0.3")),
            ]
        )
        assert len(coeff.coefficients) == 2


class TestBasisSetData:
    """Test BasisSetData model."""

    def test_creation_simple(self):
        """Test creating simple BasisSetData."""
        data = BasisSetData(
            Z=1,
            shells=[
                BasisSetCoefficients(
                    shell=0,
                    charge=Decimal("1.0"),
                    scaling=Decimal("1.0"),
                    coefficients=[(Decimal("1.0"), Decimal("1.0"))]
                )
            ]
        )
        assert data.Z == 1
        assert len(data.shells) == 1

    def test_with_ecp(self):
        """Test with ECP."""
        from cp2k_input_tools.pseudopotentials.ecp import ECP
        ecp = ECP(
            Z=1,
            Znuc=Decimal("1.0"),
            M=(1, 0, 0, 0, 0, 0),
            coefficients=[(Decimal("1.0"), Decimal("1.0"), 0)]
        )
        data = BasisSetData(
            Z=1,
            shells=[],
            ecp=ecp
        )
        assert data.ecp is not None
        assert data.ecp.Z == 1

    def test_from_lines_simple(self):
        """Test parsing from lines."""
        lines = [
            "1 1",  # Z=1, 1 shell
            "0 0 1 1.0 1.0",  # btype=0, shell=0, ngaussians=1, charge, scaling
            "1.0 1.0",  # coefficients
        ]
        data = BasisSetData.from_lines(lines)
        assert data.Z == 1
        assert len(data.shells) == 1

    def test_from_lines_multiple_shells(self):
        """Test parsing multiple shells."""
        lines = [
            "6 2",  # Z=6, 2 shells
            "0 0 2 1.0 1.0",  # first shell
            "1.0 0.5",
            "2.0 0.3",
            "0 1 1 2.0 1.0",  # second shell
            "3.0 1.0",
        ]
        data = BasisSetData.from_lines(lines)
        assert data.Z == 6
        assert len(data.shells) == 2

    def test_crystal_format_line_iter(self):
        """Test crystal_format_line_iter method."""
        data = BasisSetData(
            Z=1,
            shells=[
                BasisSetCoefficients(
                    shell=0,
                    charge=Decimal("1.0"),
                    scaling=Decimal("1.0"),
                    coefficients=[(Decimal("1.0"), Decimal("1.0"))]
                )
            ]
        )
        lines = list(data.crystal_format_line_iter())
        assert len(lines) > 0

    def test_is_block_start(self):
        """Test is_block_start static method."""
        assert BasisSetData.is_block_start("1 2")
        assert not BasisSetData.is_block_start("H BASIS_SET")

    def test_cp2k_format_line_iter(self):
        """Test cp2k_format_line_iter method."""
        data = BasisSetData(
            Z=1,
            shells=[
                BasisSetCoefficients(
                    shell=0,
                    charge=Decimal("1.0"),
                    scaling=Decimal("1.0"),
                    coefficients=[(Decimal("1.0"), Decimal("1.0"))]
                )
            ]
        )
        lines = list(data.cp2k_format_line_iter("TEST"))
        assert len(lines) > 0
