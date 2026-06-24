"""Validacao inicial de achados GitHub por ferramentas locais."""

import csv
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

from pipeline_runner.github_files import resolve_local_path
from pipeline_runner.github_findings import read_findings
from pipeline_runner.paths import PROJECT_ROOT, REPORTS_DIR, display_path

GITHUB_TOOL_VALIDATIONS_FILE = REPORTS_DIR / "github_tool_validations.csv"
VALIDATION_FIELDS = [
    "id",
    "finding_id",
    "link_id",
    "tool",
    "status",
    "classification",
    "command",
    "returncode",
    "log_file",
    "error",
    "created_at",
]
TOOLS_BY_CATEGORY = {
    "memory_corruption": ("asan",),
    "data_race": ("tsan",),
    "deadlock": ("deadlock",),
    "assertion_violation": ("esbmc",),
}
TOOL_SCRIPTS = {
    "asan": "scripts/run_asan.py",
    "tsan": "scripts/run_tsan.py",
    "deadlock": "scripts/run_deadlock.py",
    "esbmc": "scripts/run_esbmc.py",
}
DETECTED_MARKERS = (
    "AddressSanitizer:",
    "ThreadSanitizer:",
    "WARNING: ThreadSanitizer",
    "VERIFICATION FAILED",
    "Violated property",
    "data race",
    "heap-buffer-overflow",
)
LOG_PATH_PATTERN = re.compile(r"Log salvo em:\s*(.+)")
MISSING_HEADER_PATTERN = re.compile(r"fatal error:\s*['<]([^'>]+)[>']\s+file not found")
STANDARD_C_HEADERS = {
    "assert.h",
    "ctype.h",
    "errno.h",
    "float.h",
    "inttypes.h",
    "limits.h",
    "locale.h",
    "math.h",
    "setjmp.h",
    "signal.h",
    "stdalign.h",
    "stdarg.h",
    "stdatomic.h",
    "stdbool.h",
    "stddef.h",
    "stdint.h",
    "stdio.h",
    "stdlib.h",
    "stdnoreturn.h",
    "string.h",
    "time.h",
    "uchar.h",
    "wchar.h",
    "wctype.h",
}


def tools_for_finding(finding):
    return TOOLS_BY_CATEGORY.get(finding.get("category", ""), ())


def next_validation_id(index):
    return f"github_validation_{index:06d}"


def build_tool_command(tool, source_path, timeout):
    script = TOOL_SCRIPTS[tool]
    command = [sys.executable, script, str(source_path), "--timeout", str(timeout)]
    return command


def parse_log_path(output):
    for line in str(output or "").splitlines():
        match = LOG_PATH_PATTERN.search(line)
        if match:
            value = match.group(1).strip()
            path = PROJECT_ROOT / value if not Path(value).is_absolute() else Path(value)
            return display_path(path)
    return ""


def missing_header_name(text):
    match = MISSING_HEADER_PATTERN.search(str(text or ""))
    return match.group(1) if match else ""


def has_esbmc_parsing_error(text):
    return "ERROR: PARSING ERROR" in str(text or "")


def classify_tool_result(tool, returncode, log_text, stderr=""):
    combined = f"{log_text}\n{stderr}"
    if any(marker in combined for marker in DETECTED_MARKERS):
        return "detectado"
    if "undefined reference to `main'" in combined or "undefined reference to 'main'" in combined:
        return "nao_validavel"
    missing_header = missing_header_name(combined)
    if tool == "esbmc" and has_esbmc_parsing_error(combined) and missing_header:
        if Path(missing_header).name in STANDARD_C_HEADERS:
            return "erro_ferramenta"
        return "nao_validavel"
    if "falha na compilacao" in combined.lower() or re.search(
        r"\[compile\]\s*returncode:\s*[1-9]\d*",
        combined,
    ):
        return "erro_compilacao"
    if returncode == 124:
        return "detectado" if tool == "deadlock" else "inconclusivo"
    if returncode == 127:
        return "erro_ferramenta"
    if returncode == 0:
        return "nao_detectado"
    return "inconclusivo"


def read_log_text(log_file):
    if not log_file:
        return ""
    path = PROJECT_ROOT / log_file if not Path(log_file).is_absolute() else Path(log_file)
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def extract_error_message(log_text, stderr=""):
    text = str(log_text or "")
    combined = f"{text}\n{stderr}"
    if "undefined reference to `main'" in combined or "undefined reference to 'main'" in combined:
        return (
            "arquivo sem funcao main; validacao isolada por ASAN exige um executavel. "
            "Para esse achado, use um harness ou o build do projeto original."
        )
    missing_header = missing_header_name(combined)
    if has_esbmc_parsing_error(combined) and missing_header:
        if Path(missing_header).name in STANDARD_C_HEADERS:
            return (
                f"ESBMC nao encontrou o header padrao {missing_header}. "
                "No painel, use Preparar e retestar para instalar a toolchain da AWS "
                "e executar este achado novamente."
            )
        return (
            f"ESBMC nao conseguiu parsear o arquivo isoladamente porque falta o header "
            f"{missing_header}. Esse achado precisa dos includes/build do projeto original."
        )
    marker = "[error]"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return str(stderr or "").strip()


def validation_row(
    index,
    finding,
    tool,
    status,
    classification,
    command=None,
    returncode="",
    log_file="",
    error="",
    created_at=None,
):
    return {
        "id": next_validation_id(index),
        "finding_id": finding.get("id", ""),
        "link_id": finding.get("link_id", ""),
        "tool": tool,
        "status": status,
        "classification": classification,
        "command": " ".join(command or []),
        "returncode": str(returncode),
        "log_file": log_file,
        "error": error,
        "created_at": created_at or dt.datetime.now().isoformat(timespec="seconds"),
    }


def validate_finding_with_tool(finding, tool, index, timeout=10, created_at=None):
    file_path = finding.get("file_path", "")
    source_path = resolve_local_path(file_path)
    if not source_path.exists():
        return validation_row(
            index,
            finding,
            tool,
            "nao_executado",
            "nao_validavel",
            error=f"arquivo nao encontrado: {file_path}",
            created_at=created_at,
        )
    if source_path.suffix != ".c":
        return validation_row(
            index,
            finding,
            tool,
            "nao_executado",
            "nao_validavel",
            error="validacao isolada inicial suporta apenas arquivos .c",
            created_at=created_at,
        )

    command = build_tool_command(tool, source_path, timeout)
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    log_file = parse_log_path(f"{result.stdout}\n{result.stderr}")
    log_text = read_log_text(log_file)
    classification = classify_tool_result(tool, result.returncode, log_text, result.stderr)
    status = (
        "nao_executado"
        if classification == "nao_validavel"
        else "executado"
        if classification not in ("erro_compilacao", "erro_ferramenta")
        else "falhou"
    )
    error = (
        extract_error_message(log_text, result.stderr)
        if classification in ("erro_compilacao", "erro_ferramenta", "nao_validavel")
        else ""
    )
    return validation_row(
        index,
        finding,
        tool,
        status,
        classification,
        command=command,
        returncode=result.returncode,
        log_file=log_file,
        error=error or classification,
        created_at=created_at,
    )


def validation_candidates(findings, limit=None):
    candidates = []
    for finding in findings:
        if finding.get("status") == "falso_positivo":
            continue
        for tool in tools_for_finding(finding):
            candidates.append((finding, tool))

    if limit is not None:
        candidates = candidates[:limit]
    return candidates


def validate_findings(
    findings,
    timeout=10,
    limit=None,
    created_at=None,
    start_index=1,
    progress_callback=None,
):
    candidates = validation_candidates(findings, limit=limit)
    rows = []
    created_at = created_at or dt.datetime.now().isoformat(timespec="seconds")
    total = len(candidates)
    if progress_callback:
        progress_callback(0, total, "", "")
    for offset, (finding, tool) in enumerate(candidates, start=1):
        index = start_index + offset - 1
        rows.append(
            validate_finding_with_tool(
                finding,
                tool,
                index,
                timeout=timeout,
                created_at=created_at,
            )
        )
        if progress_callback:
            progress_callback(offset, total, finding.get("id", ""), tool)
    return rows


def write_validations(rows, csv_file=GITHUB_TOOL_VALIDATIONS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=VALIDATION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_validations(csv_file=GITHUB_TOOL_VALIDATIONS_FILE):
    csv_file = Path(csv_file)
    if not csv_file.exists():
        return []

    with csv_file.open(encoding="utf-8", newline="") as input_file:
        return [
            {field: row.get(field, "") for field in VALIDATION_FIELDS}
            for row in csv.DictReader(input_file)
        ]


def matches_scope(row, link_id=None, finding_id=None):
    if finding_id is not None:
        return row.get("finding_id") == finding_id or row.get("id") == finding_id
    if link_id is not None:
        return row.get("link_id") == link_id
    return True


def filter_findings(findings, link_id=None, finding_id=None):
    return [
        finding
        for finding in findings
        if matches_scope(finding, link_id=link_id, finding_id=finding_id)
    ]


def validate_findings_file(
    findings_file=None,
    output_file=GITHUB_TOOL_VALIDATIONS_FILE,
    timeout=10,
    limit=None,
    link_id=None,
    finding_id=None,
    progress_callback=None,
):
    findings = read_findings(findings_file) if findings_file else read_findings()
    findings = filter_findings(findings, link_id=link_id, finding_id=finding_id)

    if link_id is None and finding_id is None:
        rows = validate_findings(
            findings,
            timeout=timeout,
            limit=limit,
            progress_callback=progress_callback,
        )
        write_validations(rows, output_file)
        return rows

    existing_rows = read_validations(output_file)
    remaining_rows = [
        row
        for row in existing_rows
        if not matches_scope(row, link_id=link_id, finding_id=finding_id)
    ]
    rows = validate_findings(
        findings,
        timeout=timeout,
        limit=limit,
        start_index=len(remaining_rows) + 1,
        progress_callback=progress_callback,
    )
    write_validations([*remaining_rows, *rows], output_file)
    return rows
