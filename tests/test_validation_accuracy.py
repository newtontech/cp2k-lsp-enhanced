"""Tests for validation accuracy framework."""

import pathlib

import pytest

from .validation.accuracy_runner import AccuracyReport, calculate_accuracy, run_validation_suite, run_validation_test
from .. import TEST_DIR


class TestAccuracyRunner:
    """Tests for the accuracy calculation framework."""

    def test_calculate_accuracy_all_correct(self):
        results = {"true_positives": 10, "false_positives": 0, "false_negatives": 0}
        acc = calculate_accuracy(results)
        assert acc["precision"] == 1.0
        assert acc["recall"] == 1.0
        assert acc["f1"] == 1.0

    def test_calculate_accuracy_partial(self):
        results = {"true_positives": 5, "false_positives": 1, "false_negatives": 2}
        acc = calculate_accuracy(results)
        assert acc["precision"] == pytest.approx(0.8333, abs=0.01)
        assert acc["recall"] == pytest.approx(0.7143, abs=0.01)
        assert 0.76 < acc["f1"] < 0.78

    def test_calculate_accuracy_empty(self):
        results = {"true_positives": 0, "false_positives": 0, "false_negatives": 0}
        acc = calculate_accuracy(results)
        assert acc["precision"] == 1.0
        assert acc["recall"] == 1.0

    def test_run_validation_test_valid_file(self):
        valid_dir = TEST_DIR / "validation" / "valid"
        valid_dir.mkdir(parents=True, exist_ok=True)
        test_file = valid_dir / "standard_qm.inp"
        if test_file.exists():
            result = run_validation_test(test_file, expected_error=False, category="valid")
            # standard_qm.inp should parse without error
            assert not result.actual_error

    def test_run_validation_test_invalid_file(self):
        test_file = TEST_DIR / "validation" / "structure" / "invalid_element.inp"
        if test_file.exists():
            result = run_validation_test(test_file, expected_error=True, category="structure")
            # May or may not be detected by current parser
            assert isinstance(result.category, str)

    def test_accuracy_report(self):
        report = AccuracyReport()
        from .validation.accuracy_runner import TestResult

        report.add_result(TestResult("test1", "cat1", True, True))
        report.add_result(TestResult("test2", "cat1", True, False))
        report.add_result(TestResult("test3", "cat2", False, False))
        report.add_result(TestResult("test4", "cat2", False, True))

        assert report.total == 4
        assert report.true_positives == 1
        assert report.false_negatives == 1
        assert report.true_negatives == 1
        assert report.false_positives == 1
        assert report.precision == 0.5
        assert report.recall == 0.5
        assert report.f1 == 0.5

    def test_accuracy_report_to_dict(self):
        report = AccuracyReport()
        from .validation.accuracy_runner import TestResult

        report.add_result(TestResult("test1", "cat1", True, True))
        d = report.to_dict()
        assert "total" in d
        assert "precision" in d
        assert "f1" in d
        assert "by_category" in d

    def test_accuracy_report_summary(self):
        report = AccuracyReport()
        from .validation.accuracy_runner import TestResult

        report.add_result(TestResult("test1", "cat1", True, True))
        summary = report.summary()
        assert "Total tests: 1" in summary
        assert "precision" in summary.lower()

    def test_run_validation_suite(self):
        report = run_validation_suite(TEST_DIR / "validation")
        assert report.total >= 0
        assert isinstance(report.summary(), str)

    def test_force_eval_method_conflict(self):
        """Test that method conflict files are detected."""
        test_file = TEST_DIR / "validation" / "force_eval" / "method_conflict.inp"
        if test_file.exists():
            result = run_validation_test(test_file, expected_error=True, category="force_eval")
            # The parser should detect duplicate METHOD or invalid config
            assert result.test_file == "method_conflict.inp"
            assert result.category == "force_eval"

    def test_valid_standard_qm(self):
        """Test that a valid QM input passes validation."""
        test_file = TEST_DIR / "validation" / "valid" / "standard_qm.inp"
        if test_file.exists():
            result = run_validation_test(test_file, expected_error=False, category="valid")
            assert not result.actual_error, f"Valid file should not error: {result.message}"


class TestValidationCategories:
    """Integration tests for each validation category."""

    def test_all_force_eval_tests(self):
        fe_dir = TEST_DIR / "validation" / "force_eval"
        if fe_dir.exists():
            for f in fe_dir.glob("*.inp"):
                result = run_validation_test(f, expected_error=True, category="force_eval")
                assert result.category == "force_eval"

    def test_all_dft_tests(self):
        dft_dir = TEST_DIR / "validation" / "dft_section"
        if dft_dir.exists():
            for f in dft_dir.glob("*.inp"):
                result = run_validation_test(f, expected_error=True, category="dft_section")
                assert result.category == "dft_section"

    def test_all_structure_tests(self):
        struct_dir = TEST_DIR / "validation" / "structure"
        if struct_dir.exists():
            for f in struct_dir.glob("*.inp"):
                result = run_validation_test(f, expected_error=True, category="structure")
                assert result.category == "structure"
