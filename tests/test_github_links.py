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
                    "url_type": "repo",
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

    # Verifica se os tipos de URL do GitHub sao identificados.
    def test_classify_github_url_detects_supported_types(self):
        self.assertEqual(
            github_links.classify_github_url("https://github.com/user/repo"),
            ("repo", ""),
        )
        self.assertEqual(
            github_links.classify_github_url(
                "https://github.com/user/repo/blob/main/src/sample.c"
            ),
            ("file", ""),
        )
        self.assertEqual(
            github_links.classify_github_url(
                "https://github.com/user/repo/tree/main/src"
            ),
            ("directory", ""),
        )

    # Verifica se URLs fora do GitHub sao registradas como falha auditavel.
    def test_append_link_records_invalid_github_url_as_failed(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"

            row = github_links.append_link(
                "https://example.com/user/repo",
                csv_file,
                submitted_at="2026-06-16T08:00:00",
            )

            self.assertEqual(row["status"], "falhou")
            self.assertEqual(row["url_type"], "")
            self.assertEqual(row["error"], "url deve ser do github.com")
            self.assertEqual(github_links.read_links(csv_file), [row])

    # Verifica se registros antigos sem tipo sao enriquecidos na leitura.
    def test_read_links_enriches_legacy_rows_without_url_type(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"
            csv_file.write_text(
                "\n".join(
                    [
                        ",".join(github_links.LINK_FIELDS),
                        (
                            "gh_000001,2026-06-16T08:00:00,"
                            "https://github.com/user/repo,,pendente,,,,"
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            rows = github_links.read_links(csv_file)

            self.assertEqual(rows[0]["url_type"], "repo")
            self.assertEqual(rows[0]["status"], "pendente")
            self.assertEqual(rows[0]["error"], "")

    # Verifica se URL vazia nao e aceita.
    def test_append_link_rejects_empty_url(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"

            with self.assertRaises(ValueError):
                github_links.append_link("   ", csv_file)

    # Verifica se um registro pode ser atualizado por ID.
    def test_update_link_changes_status_and_path(self):
        with TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "github_links.csv"
            github_links.append_link("https://github.com/user/repo", csv_file)

            row = github_links.update_link(
                "gh_000001",
                {
                    "status": "concluido",
                    "local_path": "inputs/github_repos/gh_000001",
                    "ignored": "value",
                },
                csv_file,
            )

            self.assertEqual(row["status"], "concluido")
            self.assertEqual(row["local_path"], "inputs/github_repos/gh_000001")
            self.assertNotIn("ignored", row)
            self.assertEqual(github_links.get_link("gh_000001", csv_file), row)


if __name__ == "__main__":
    unittest.main()
