# Additional tests for utils.py
import pytest


class TestUtils:
    """Test utility functions"""

    def test_num2sym_exists(self):
        """Test NUM2SYM exists"""
        from cp2k_input_tools.utils import NUM2SYM
        assert isinstance(NUM2SYM, list)
        assert len(NUM2SYM) > 0

    def test_common_elements(self):
        """Test common elements in NUM2SYM"""
        from cp2k_input_tools.utils import NUM2SYM
        assert NUM2SYM[1] == "H"  # Hydrogen
        assert NUM2SYM[6] == "C"  # Carbon
        assert NUM2SYM[8] == "O"  # Oxygen

    def test_num2sym_indexing(self):
        """Test NUM2SYM indexing"""
        from cp2k_input_tools.utils import NUM2SYM
        # Index 0 should be empty
        assert NUM2SYM[0] == ""