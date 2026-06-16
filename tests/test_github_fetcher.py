import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pipeline_runner import github_fetcher


class GitHubFetcherTest(unittest.TestCase):
    # Verifica se a URL de clone aponta para o repositorio, nao para subcaminhos.
    def test_repository_clone_url_uses_owner_and_repo(self):
        self.assertEqual(
            github_fetcher.repository_clone_url(
                "https://github.com/user/repo/tree/main/src"
            ),
            "https://github.com/user/repo.git",
        )

    # Verifica se o comando usa clone raso por padrao.
    def test_build_shallow_clone_command_uses_depth_one(self):
        command = github_fetcher.build_shallow_clone_command(
            "https://github.com/user/repo",
            Path("inputs/github_repos/gh_000001"),
        )

        self.assertEqual(
            command,
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/user/repo.git",
                "inputs/github_repos/gh_000001",
            ],
        )

    # Verifica se o download bem-sucedido retorna caminho local sem executar rede real.
    def test_fetch_repository_runs_git_clone(self):
        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with TemporaryDirectory() as temp_dir:
            with patch("pipeline_runner.github_fetcher.subprocess.run", return_value=completed) as run:
                result = github_fetcher.fetch_repository(
                    {
                        "id": "gh_000001",
                        "url": "https://github.com/user/repo",
                        "url_type": "repo",
                        "status": "pendente",
                    },
                    base_dir=Path(temp_dir),
                    timeout=5,
                )

        self.assertTrue(result["local_path"].endswith("gh_000001"))
        self.assertEqual(run.call_args.args[0][0:4], ["git", "clone", "--depth", "1"])

    # Verifica se tipos ainda nao suportados sao recusados.
    def test_fetch_repository_rejects_non_repo_links(self):
        with self.assertRaises(ValueError):
            github_fetcher.fetch_repository(
                {
                    "id": "gh_000001",
                    "url": "https://github.com/user/repo/blob/main/sample.c",
                    "url_type": "file",
                    "status": "pendente",
                }
            )


if __name__ == "__main__":
    unittest.main()
