import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline_runner import github_links


class GitHubLinksTest(unittest.TestCase):
    # Verifica se o arquivo de links e criado com cabecalho padronizado.
    def test_ensure_links_file_creates_header(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"

            github_links.ensure_links_file(csv_file)

            with csv_file.open(encoding="utf-8", newline="") as input_file:
                reader = csv.reader(input_file)
                self.assertEqual(next(reader), github_links.LINK_FIELDS)

    # Verifica se um link enviado pelo usuario e registrado como pendente.
    def test_append_link_registers_pending_row(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"

            row = github_links.append_link(
                " https://github.com/user/repo ",
                csv_file,
                submitted_at="2026-06-16T08:00:00",
            )

            self.assertEqual(
                row,
                {
                    "id": "gh_000001",
                    "submitted_at": "2026-06-16T08:00:00",
                    "url": "https://github.com/user/repo",
                    "url_type": "",
                    "status": "pendente",
                    "local_path": "",
                    "error": "",
                    "started_at": "",
                    "finished_at": "",
                },
            )
            self.assertEqual(github_links.read_links(csv_file), [row])

    # Verifica se os IDs continuam sequenciais.
    def test_append_link_uses_next_sequential_id(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"

            github_links.append_link("https://github.com/user/one", csv_file)
            row = github_links.append_link("https://github.com/user/two", csv_file)

            self.assertEqual(row["id"], "gh_000002")

    # Verifica se URL vazia nao e aceita.
    def test_append_link_rejects_empty_url(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"

            with self.assertRaises(ValueError):
                github_links.append_link("   ", csv_file)


if __name__ == "__main__":
    unittest.main()
