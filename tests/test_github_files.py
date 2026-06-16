import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline_runner import github_files


class GitHubFilesTest(unittest.TestCase):
    # Verifica se apenas arquivos C/C++ relevantes sao descobertos.
    def test_discover_code_files_filters_extensions_and_ignored_dirs(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            (root / "src" / "lib.hpp").write_text("#pragma once\n", encoding="utf-8")
            (root / "src" / "readme.md").write_text("# docs\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "ignored.c").write_text("ignored\n", encoding="utf-8")
            (root / "third_party").mkdir()
            (root / "third_party" / "vendored.c").write_text("ignored\n", encoding="utf-8")

            files = github_files.discover_code_files(root)

            self.assertEqual(
                [path.relative_to(root) for path in files],
                [Path("src/lib.hpp"), Path("src/main.c")],
            )

    # Verifica se a descoberta falha claramente quando o caminho nao existe.
    def test_discover_code_files_rejects_missing_path(self):
        with self.assertRaises(ValueError):
            github_files.discover_code_files(Path("missing-path"))

    # Verifica se arquivos descobertos sao gravados por link.
    def test_replace_files_for_link_writes_csv_rows(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_file = root / "github_files.csv"
            source = root / "sample.c"
            source.write_text("int main(void) { return 0; }\n", encoding="utf-8")

            rows = github_files.replace_files_for_link(
                "gh_000001",
                [source],
                csv_file=csv_file,
                created_at="2026-06-16T10:00:00",
            )

            self.assertEqual(rows[0]["id"], "gh_000001_file_000001")
            self.assertEqual(rows[0]["link_id"], "gh_000001")
            self.assertEqual(rows[0]["extension"], ".c")
            self.assertEqual(rows[0]["status"], "descoberto")
            self.assertEqual(github_files.file_counts_by_link(rows), {"gh_000001": 1})
            self.assertEqual(github_files.read_files(csv_file), rows)

    # Verifica se registros antigos do mesmo link sao substituidos.
    def test_replace_files_for_link_replaces_previous_rows_for_same_link(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_file = root / "github_files.csv"
            first = root / "first.c"
            second = root / "second.cpp"
            first.write_text("int first(void) { return 0; }\n", encoding="utf-8")
            second.write_text("int second(void) { return 0; }\n", encoding="utf-8")

            github_files.replace_files_for_link("gh_000001", [first], csv_file=csv_file)
            rows = github_files.replace_files_for_link("gh_000001", [second], csv_file=csv_file)

            self.assertEqual(len(rows), 1)
            self.assertEqual(github_files.read_files(csv_file), rows)
            self.assertEqual(rows[0]["extension"], ".cpp")


if __name__ == "__main__":
    unittest.main()
