import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_CLIS = [
    ROOT / "scripts" / "check-shops.py",
    ROOT / "heartslayer_kit" / "check_shops.py",
    *sorted((ROOT / "tools").glob("*.py")),
]
SHELL_CLIS = sorted((ROOT / "scripts").glob("*.sh"))


class CliTests(unittest.TestCase):
    def test_python_help_works_without_bottled_ai(self):
        for cli in PYTHON_CLIS:
            with self.subTest(cli=cli.name):
                result = subprocess.run(
                    [sys.executable, str(cli), "--help"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_python_invalid_arguments_return_two(self):
        for cli in PYTHON_CLIS:
            with self.subTest(cli=cli.name):
                result = subprocess.run(
                    [sys.executable, str(cli), "--invalid-option"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_shell_help_is_safe_and_returns_zero(self):
        for cli in SHELL_CLIS:
            with self.subTest(cli=cli.name):
                result = subprocess.run(
                    ["bash", str(cli), "--help"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
