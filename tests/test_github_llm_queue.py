import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline_runner import github_llm_queue


class GitHubLLMQueueTest(unittest.TestCase):
    # Verifica se a fila seleciona confirmados e suspeitos de alta prioridade.
    def test_build_queue_rows_selects_ready_findings(self):
        rows = github_llm_queue.build_queue_rows(
            [
                {
                    "id": "finding-confirmed",
                    "link_id": "gh_000001",
                    "file_path": "src/a.c",
                    "line": "20",
                    "category": "memory_corruption",
                    "severity": "media",
                    "priority": "media",
                    "status": "confirmado",
                    "message": "uso de memcpy exige validacao explicita de tamanho",
                    "context": "> 20: memcpy(dst, src, n);",
                },
                {
                    "id": "finding-high",
                    "link_id": "gh_000002",
                    "file_path": "src/b.c",
                    "line": "8",
                    "category": "memory_corruption",
                    "severity": "alta",
                    "priority": "alta",
                    "status": "suspeito",
                    "message": "uso de strcpy pode copiar dados alem do destino",
                    "context": "> 8: strcpy(dst, src);",
                },
                {
                    "id": "finding-low",
                    "link_id": "gh_000003",
                    "file_path": "src/c.c",
                    "line": "3",
                    "category": "assertion_violation",
                    "severity": "baixa",
                    "priority": "baixa",
                    "status": "suspeito",
                    "message": "assertiva identifica propriedade",
                    "context": "> 3: assert(x);",
                },
            ],
            created_at="2026-06-17T12:00:00",
        )

        self.assertEqual([row["finding_id"] for row in rows], ["finding-confirmed", "finding-high"])
        self.assertEqual(rows[0]["selection_reason"], "achado confirmado na revisao")
        self.assertIn("Analise o achado de seguranca", rows[0]["prompt"])
        self.assertIn("> 20: memcpy(dst, src, n);", rows[0]["prompt"])

    # Verifica se a fila pode ser gerada a partir de CSV e persistida.
    def test_build_queue_from_findings_writes_csv(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            findings_file = root / "github_findings.csv"
            output_file = root / "github_llm_queue.csv"
            findings_file.write_text(
                (
                    "id,link_id,file_id,tool,file_path,line,category,severity,priority,"
                    "status,message,evidence,context_start_line,context_end_line,context,created_at\n"
                    "f1,gh_000001,file1,static-patterns,src/a.c,1,memory_corruption,"
                    "alta,alta,suspeito,uso de strcpy pode copiar dados alem do destino,"
                    "strcpy(dst src),1,2,> 1: strcpy(dst src),2026-06-17T12:00:00\n"
                ),
                encoding="utf-8",
            )

            rows = github_llm_queue.build_queue_from_findings(
                findings_file=findings_file,
                output_file=output_file,
                created_at="2026-06-17T12:00:00",
            )

            self.assertEqual(len(rows), 1)
            self.assertTrue(output_file.exists())
            self.assertIn("finding_id", output_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
