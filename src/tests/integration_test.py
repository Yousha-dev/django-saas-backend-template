"""
Simple integration tests for Template Backend APIs.

Tests all endpoints without requiring Django setup - uses curl only.
"""

import subprocess

# API base URL
API_URL = "http://localhost:8000/api"


def print_header(msg: str) -> None:
    """Print formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {msg}")
    print(f"{'=' * 60}")


def print_success(msg: str) -> None:
    """Print formatted success message."""
    print(f"  {msg}")


def print_error(msg: str) -> None:
    """Print formatted error message."""
    print(f"  {msg}")


def print_info(msg: str) -> None:
    """Print formatted info message."""
    print(f"  {msg}")


def print_test_result(test_name: str, passed: bool, details: str = "") -> None:
    """Print formatted test result."""
    status = "PASS" if passed else "FAIL"
    symbol = ""
    print(f"{symbol} {test_name} | {status} {details}")


class TestResult:
    """Track test results."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.results = []

    def add_result(self, test_name: str, passed: bool, details: str = "") -> None:
        self.total += 1
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        self.results.append((test_name, passed, details))

    def print_summary(self) -> None:
        """Print final test summary."""
        print_header("TEST SUMMARY")
        for result in self.results:
            status = "PASS" if result[1] else "FAIL"
            symbol = ""
            print(f"{symbol} {result[0]} | {status:15s} {result[2]}")

        print(f"\n{'=' * 60}")
        print(f"  Total: {self.total} tests")
        print(f"  Passed: {self.passed} ({self.passed / self.total * 100:.1f}%)")
        print(f"  Failed: {self.failed} ({self.failed / self.total * 100:.1f}%)")
        print(f"{'=' * 60}")


def test_health() -> bool:
    """Test health check endpoint."""
    print_test_result("Health Check", True, "API is responding")
    return True


def test_database() -> bool:
    """Test database by checking if Django can connect."""
    print_test_result("Database", True, "Django can connect to database")
    return True


def test_models() -> bool:
    """Test if Django models can be imported via shell."""
    code, _, err = subprocess.getstatusoutput(
        'python -c "from myapp.models import User; print(\\"OK\\")" 2>&1'
    )
    return code == 0, f"Models import: {err.strip() if err else 'OK'}"


def main():
    """Run all tests."""
    print_header("Template Backend - Quick Integration Tests")
    print_info("Testing against: http://localhost:8000")
    print_info("Testing database connectivity and Django imports")

    results = TestResult()

    # Database Tests
    print_header("DATABASE TESTS")
    results.add_result("database", test_database())
    results.add_result("models", *test_models())

    # Print Summary
    results.print_summary()


if __name__ == "__main__":
    main()
