import unittest

from scripts import generate_report


class GenerateReportTest(unittest.TestCase):
    def test_parse_tools_accepts_comma_separated_tools(self):
        tools = generate_report.parse_tools("asan,tsan")

        self.assertEqual(tools, ("asan", "tsan"))

    def test_parse_tools_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            generate_report.parse_tools("asan,unknown")

    def test_classify_result_detects_asan_marker(self):
        data = {
            "error": "",
            "compile_returncode": "0",
        }

        classification = generate_report.classify_result(
            "SUMMARY: AddressSanitizer: heap-buffer-overflow",
            data,
        )

        self.assertEqual(classification, "detectado")

    def test_classify_result_detects_unavailable_tool(self):
        data = {
            "error": "Ferramenta AFL++ nao encontrada: afl-clang-fast, afl-fuzz.",
            "compile_returncode": "",
        }

        classification = generate_report.classify_result("", data)

        self.assertEqual(classification, "ferramenta indisponivel")

    def test_build_summary_counts_by_tool_and_classification(self):
        rows = [
            {"tool": "asan", "classification": "detectado"},
            {"tool": "asan", "classification": "detectado"},
            {"tool": "tsan", "classification": "nao detectado"},
        ]

        summary = generate_report.build_summary(rows)

        self.assertEqual(
            summary,
            [
                {"tool": "asan", "classification": "detectado", "count": 2},
                {"tool": "tsan", "classification": "nao detectado", "count": 1},
            ],
        )


if __name__ == "__main__":
    unittest.main()
