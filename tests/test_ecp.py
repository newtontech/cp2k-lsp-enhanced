"""Tests for ECP (Effective Core Potential) data model"""

from decimal import Decimal

from cp2k_input_tools.pseudopotentials.ecp import ECP


def test_ecp_basic():
    """Test basic ECP creation"""
    ecp = ECP(
        Z=6,
        Znuc=4,
        M=(0, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )

    assert ecp.Z == 6
    assert ecp.Znuc == 4
    assert ecp.M == (0, 1, 0, 0, 0, 0)
    assert len(ecp.coefficients) == 1


def test_ecp_crystal_format_line_iter():
    """Test Crystal format line iteration"""
    ecp = ECP(
        Z=6,
        Znuc=4,
        M=(0, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )

    lines = list(ecp.crystal_format_line_iter())
    assert len(lines) == 2
    assert lines[0] == "4 0 1 0 0 0 0"  # Znuc + M[0-5]
    assert lines[1].startswith("  ")


def test_ecp_nwchem_format_line_iter():
    """Test NWChem format line iteration"""
    ecp = ECP(
        Z=6,
        Znuc=4,
        M=(0, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )

    lines = list(ecp.nwchem_format_line_iter())
    assert len(lines) == 5  # header, ul, default S, C S, coefficient
    assert "C nelec 2" in lines[0]  # 6 - 4 = 2 electrons in pseudo
    assert "C ul" in lines[1]
    assert "2     1.000000    0.000000" in lines[2]  # Default S shell
    assert "C S" in lines[3]


def test_ecp_multiple_coefficients():
    """Test ECP with multiple coefficients"""
    ecp = ECP(
        Z=8,
        Znuc=6,
        M=(1, 2, 0, 0, 0, 0),
        coefficients=[
            (Decimal("10.0"), Decimal("0.5"), 0),
            (Decimal("1.5"), Decimal("2.3"), 1),
            (Decimal("3.2"), Decimal("1.1"), 1),
        ],
    )

    assert ecp.Z == 8
    assert ecp.Znuc == 6
    assert ecp.M == (1, 2, 0, 0, 0, 0)
    assert len(ecp.coefficients) == 3


def test_ecp_crystal_format_multiple():
    """Test Crystal format with multiple coefficients"""
    ecp = ECP(
        Z=8,
        Znuc=6,
        M=(1, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("10.0"), Decimal("0.5"), 0),
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )

    lines = list(ecp.crystal_format_line_iter())
    assert len(lines) == 3
    assert lines[0] == "6 1 1 0 0 0 0"  # Znuc + M[0-5]


def test_ecp_nwchem_format_with_s_shell():
    """Test NWChem format with S shell coefficients"""
    ecp = ECP(
        Z=6,
        Znuc=4,
        M=(1, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("10.0"), Decimal("0.5"), 0),
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )

    lines = list(ecp.nwchem_format_line_iter())
    # M[0] = 1, so should have S shell coefficient
    assert len(lines) >= 4
    assert "C nelec 2" in lines[0]
    # First coefficient line should be for S shell (l=0)
    assert "0" in lines[3] or "C S" in lines[3]


def test_ecp_nwchem_format_empty_p():
    """Test NWChem format with empty P shell"""
    ecp = ECP(
        Z=6,
        Znuc=4,
        M=(1, 0, 0, 0, 0, 0),
        coefficients=[
            (Decimal("10.0"), Decimal("0.5"), 0),
        ],
    )

    lines = list(ecp.nwchem_format_line_iter())
    # M[1] = 0, so P shell should be skipped
    assert "C P" not in lines


def test_ecp_pydantic_validation():
    """Test Pydantic validation for ECP"""
    # Valid ECP
    ecp = ECP(
        Z=6,
        Znuc=4,
        M=(0, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )
    assert ecp is not None

    # Test with integer conversion
    ecp2 = ECP(
        Z=8,
        Znuc=6,
        M=(1, 1, 0, 0, 0, 0),
        coefficients=[
            (Decimal("10.0"), Decimal("0.5"), 0),
            (Decimal("1.5"), Decimal("2.3"), 1),
        ],
    )
    assert ecp2.Z == 8
    assert ecp2.Znuc == 6


def test_ecp_precision():
    """Test ECP with high precision coefficients"""
    ecp = ECP(
        Z=1,
        Znuc=1,
        M=(1, 0, 0, 0, 0, 0),
        coefficients=[
            (Decimal("123456789.123456789"), Decimal("987654321.987654321"), 0),
        ],
    )

    lines = list(ecp.crystal_format_line_iter())
    assert len(lines) == 2
    # Check that precision is preserved
    assert lines[1].count(".") >= 1
