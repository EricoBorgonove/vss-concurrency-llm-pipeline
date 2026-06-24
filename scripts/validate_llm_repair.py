#!/usr/bin/env python3
"""Valida de forma simulada uma sugestao gerada pela etapa de LLM."""

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_runner.benchmark_llm_repairs import update_repair  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "llm"
SUPPORTED_TOOLS = ("asan", "tsan", "esbmc", "deadlock")
LOG_PATH_PATTERN = re.compile(r"Log salvo em:\s*(.+)")


def display_path(path):
    path = Path(path)
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def display_command(command):
    return [display_path(part) if "/" in str(part) else str(part) for part in command]


def sanitize_text(text):
    text = str(text)
    text = text.replace(str(PROJECT_ROOT) + "/", "")
    temp_pattern = r"/var" + r"/folders/\S+/T/vss-"
    text = re.sub(temp_pattern + r"[^/\s,;\"<>]+/(\S+)", r"<tmp>/\1", text)
    return re.sub(temp_pattern + r"[^\s,;\"<>]+", "<tmp>", text)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Valida uma sugestao simulada de reparo sem alterar codigo-fonte."
    )
    parser.add_argument("repair_file", help="Arquivo de sugestao gerado por run_llm_repair.py.")
    parser.add_argument(
        "--fixed-benchmark",
        help="Arquivo .c reparado a ser validado por uma ferramenta ja integrada.",
    )
    parser.add_argument(
        "--tool",
        choices=SUPPORTED_TOOLS,
        default="asan",
        help="Ferramenta usada para validar o benchmark reparado. Padrao: asan.",
    )
    parser.add_argument(
        "--tool-timeout",
        type=int,
        default=30,
        help="Timeout usado pela ferramenta de validacao em segundos. Padrao: 30.",
    )
    parser.add_argument(
        "--repair-id",
        help="ID do reparo em reports/llm_benchmark_repairs.csv a atualizar.",
    )
    return parser


def make_output_path(repair_path):
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return OUTPUT_DIR / f"{repair_path.stem}_{timestamp}_validation.txt"


def parse_repair(content):
    issue_type = ""
    has_suggestion = False

    for line in content.splitlines():
        if line.startswith("issue_type: "):
            issue_type = line.removeprefix("issue_type: ").strip()
        if line.startswith("category: ") and not issue_type:
            issue_type = line.removeprefix("category: ").strip()
        if line.strip() == "suggestion:":
            has_suggestion = True
        if line.strip() == "response:":
            has_suggestion = True

    return issue_type, has_suggestion


def validate_repair(content):
    issue_type, has_suggestion = parse_repair(content)
    problems = []

    if "LLM repair simulation" not in content and "LLM benchmark repair" not in content:
        problems.append("arquivo nao parece ser uma sugestao de LLM")
    if not issue_type:
        problems.append("campo issue_type ausente")
    if not has_suggestion:
        problems.append("secao suggestion ausente")

    status = "validacao_simulada_aprovada" if not problems else "validacao_simulada_reprovada"
    return status, issue_type, problems


def run_tool_validation(tool, fixed_benchmark, timeout):
    if tool == "asan":
        command = [
            sys.executable,
            "scripts/run_asan.py",
            str(fixed_benchmark),
            "--timeout",
            str(timeout),
        ]
    elif tool == "tsan":
        command = [
            sys.executable,
            "scripts/run_tsan.py",
            str(fixed_benchmark),
            "--timeout",
            str(timeout),
        ]
    elif tool == "esbmc":
        command = [
            sys.executable,
            "scripts/run_esbmc.py",
            str(fixed_benchmark),
            "--timeout",
            str(timeout),
        ]
    elif tool == "deadlock":
        command = [
            sys.executable,
            "scripts/run_deadlock.py",
            str(fixed_benchmark),
            "--timeout",
            str(timeout),
        ]
    else:
        raise ValueError(f"ferramenta nao suportada: {tool}")

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return command, result


def parse_log_path(output):
    for line in str(output or "").splitlines():
        match = LOG_PATH_PATTERN.search(line)
        if match:
            value = match.group(1).strip()
            path = PROJECT_ROOT / value if not Path(value).is_absolute() else Path(value)
            return display_path(path)
    return ""


def write_validation(
    output_path,
    repair_path,
    status,
    issue_type,
    problems,
    tool_command=None,
    tool_result=None,
):
    with output_path.open("w", encoding="utf-8") as output_file:
        output_file.write("LLM repair validation simulation\n")
        output_file.write(f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}\n")
        output_file.write(f"repair_file: {display_path(repair_path)}\n")
        output_file.write(f"status: {status}\n")
        output_file.write(f"issue_type: {issue_type or 'N/A'}\n\n")
        output_file.write("checks:\n")
        if problems:
            for problem in problems:
                output_file.write(f"- {problem}\n")
        else:
            output_file.write("- sugestao contem metadados minimos esperados\n")

        if tool_command and tool_result:
            output_file.write("\ntool_validation:\n")
            output_file.write(f"command: {' '.join(display_command(tool_command))}\n")
            output_file.write(f"returncode: {tool_result.returncode}\n")
            if tool_result.stdout:
                output_file.write("stdout:\n")
                output_file.write(sanitize_text(tool_result.stdout))
                if not tool_result.stdout.endswith("\n"):
                    output_file.write("\n")
            if tool_result.stderr:
                output_file.write("stderr:\n")
                output_file.write(sanitize_text(tool_result.stderr))
                if not tool_result.stderr.endswith("\n"):
                    output_file.write("\n")
        else:
            output_file.write("- nenhuma validacao com ferramenta foi solicitada nesta etapa\n")


def main():
    parser = build_parser()
    args = parser.parse_args()

    repair_path = Path(args.repair_file).resolve()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = make_output_path(repair_path)

    if not repair_path.exists():
        print(f"Erro: arquivo de reparo nao encontrado: {display_path(repair_path)}", file=sys.stderr)
        return 2

    if not repair_path.is_file():
        print(f"Erro: reparo deve ser um arquivo: {display_path(repair_path)}", file=sys.stderr)
        return 2

    try:
        content = repair_path.read_text(encoding="utf-8", errors="replace")
        status, issue_type, problems = validate_repair(content)
        tool_command = None
        tool_result = None

        if args.fixed_benchmark:
            fixed_benchmark = Path(args.fixed_benchmark).resolve()
            if not fixed_benchmark.exists():
                problems.append(f"benchmark reparado nao encontrado: {display_path(fixed_benchmark)}")
            elif fixed_benchmark.suffix != ".c":
                problems.append(f"benchmark reparado deve ser arquivo .c: {display_path(fixed_benchmark)}")
            else:
                tool_command, tool_result = run_tool_validation(
                    args.tool,
                    fixed_benchmark,
                    args.tool_timeout,
                )
                if tool_result.returncode != 0:
                    problems.append(
                        f"validacao com {args.tool} falhou com codigo {tool_result.returncode}"
                    )

            status = "validacao_controlada_aprovada" if not problems else "validacao_controlada_reprovada"

        write_validation(
            output_path,
            repair_path,
            status,
            issue_type,
            problems,
            tool_command=tool_command,
            tool_result=tool_result,
        )
        if args.repair_id:
            validation_log = ""
            if tool_result:
                validation_log = parse_log_path(f"{tool_result.stdout}\n{tool_result.stderr}")
            update_repair(
                args.repair_id,
                {
                    "status": "validado",
                    "validation_status": status,
                    "validation_tool": args.tool if args.fixed_benchmark else "",
                    "validation_log": validation_log,
                    "validated_at": dt.datetime.now().isoformat(timespec="seconds"),
                    "error": "; ".join(problems),
                },
            )
        print(f"Validacao simulada salva em: {display_path(output_path)}")
        return 0 if not problems else 1
    except OSError as exc:
        print(f"Erro ao validar reparo: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
