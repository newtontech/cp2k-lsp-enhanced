"""Validation accuracy testing framework for CP2K-LSP.

Calculates precision, recall, and F1 score for validation rules.
"""

import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cp2k_input_tools.parser import CP2KInputParser
from cp2k_input_tools.parser_errors import InvalidNameError, InvalidParameterError, InvalidSectionError, ParserError
from cp2k_input_tools.tokenizer import TokenizerError


@dataclass
class TestResult:
    """Result of a single validation test case."""
    test_file: str
    category: str
    expected_error: bool
    actual_error: bool
    error_type: Optional[str] = None
    message: str = ""


@dataclass
class AccuracyReport:
    """Aggregated accuracy report."""
    total: int = 0
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    results: List[TestResult] = field(default_factory=list)
    by_category: Dict[str, "AccuracyReport"] = field(default_factory=dict)

    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 1.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 1.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 1.0
        return (self.true_positives + self.true_negatives) / self.total

    def _track(self, result: TestResult):
        self.total += 1
        self.results.append(result)

        if result.expected_error and result.actual_error:
            self.true_positives += 1
        elif result.expected_error and not result.actual_error:
            self.false_negatives += 1
        elif not result.expected_error and result.actual_error:
            self.false_positives += 1
        else:
            self.true_negatives += 1

    def add_result(self, result: TestResult):
        self._track(result)

        # Also track by category (no recursion)
        if result.category not in self.by_category:
            self.by_category[result.category] = AccuracyReport()
        self.by_category[result.category]._track(result)

    def summary(self) -> str:
        lines = [
            f"Total tests: {self.total}",
            f"True positives:  {self.true_positives}",
            f"False positives: {self.false_positives}",
            f"True negatives:  {self.true_negatives}",
            f"False negatives: {self.false_negatives}",
            f"Accuracy:  {self.accuracy:.2%}",
            f"Precision: {self.precision:.2%}",
            f"Recall:    {self.recall:.2%}",
            f"F1 score:  {self.f1:.2%}",
        ]
        if self.by_category:
            lines.append("\nBy category:")
            for cat, report in self.by_category.items():
                lines.append(
                    f"  {cat}: acc={report.accuracy:.2%} p={report.precision:.2%} "
                    f"r={report.recall:.2%} f1={report.f1:.2%} ({report.total} tests)"
                )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "accuracy": round(self.accuracy, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "by_category": {k: v.to_dict() for k, v in self.by_category.items()},
        }


def run_validation_test(test_file: pathlib.Path, expected_error: bool, category: str) -> TestResult:
    """Run the parser on a test file and compare with expected outcome."""
    parser = CP2KInputParser()
    actual_error = False
    error_type = None
    message = ""

    try:
        with open(test_file, "r") as f:
            parser.parse(f)
    except (TokenizerError, ParserError, InvalidNameError, InvalidSectionError, InvalidParameterError) as exc:
        actual_error = True
        error_type = type(exc).__name__
        message = str(exc.args[0]) if exc.args else str(exc)
    except Exception as exc:
        actual_error = True
        error_type = type(exc).__name__
        message = str(exc)

    return TestResult(
        test_file=str(test_file.name),
        category=category,
        expected_error=expected_error,
        actual_error=actual_error,
        error_type=error_type,
        message=message,
    )


def run_validation_suite(test_dir: pathlib.Path) -> AccuracyReport:
    """Run all validation tests in a directory tree."""
    report = AccuracyReport()

    for category_dir in sorted(test_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        for test_file in sorted(category_dir.glob("*.inp")):
            expected_error = not test_file.stem.startswith("valid_")
            result = run_validation_test(test_file, expected_error, category)
            report.add_result(result)

    return report


def calculate_accuracy(results: Dict[str, int]) -> dict:
    """Calculate precision, recall, F1 from raw counts."""
    tp = results.get("true_positives", 0)
    fp = results.get("false_positives", 0)
    fn = results.get("false_negatives", 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
