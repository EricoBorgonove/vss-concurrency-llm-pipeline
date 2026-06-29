"""Fluxo de reparos LLM para benchmarks controlados."""

import csv
import datetime as dt
import json
import re
from pathlib import Path

from pipeline_runner import llm_client
from pipeline_runner.metadata import read_benchmark_metadata
from pipeline_runner.paths import PROJECT_ROOT, REPORTS_DIR, display_path

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "llm"
REPAIRS_DIR = OUTPUT_DIR / "repairs"
REPAIRED_BENCHMARKS_DIR = OUTPUT_DIR / "repaired_benchmarks"
LLM_BENCHMARK_REPAIRS_FILE = REPORTS_DIR / "llm_benchmark_repairs.csv"
REPAIR_FIELDS = [
    "id",
    "benchmark",
    "category",
    "tool",
    "source_log",
    "repair_file",
    "repaired_benchmark",
    "response_file",
    "model",
    "mode",
    "status",
    "validation_status",
    "validation_tool",
    "validation_log",
    "error",
    "created_at",
    "validated_at",
]
TOOL_BY_CATEGORY = {
    "memory_corruption": "asan",
    "data_race": "tsan",
    "deadlock": "deadlock",
    "assertion_violation": "esbmc",
}
TOOL_ALIASES = {
    "afl": "asan",
    "afl++": "asan",
}


def relative_or_raw(path):
    return display_path(path) if path else ""


def read_repairs(csv_file=LLM_BENCHMARK_REPAIRS_FILE):
    csv_file = Path(csv_file)
    if not csv_file.exists():
        return []
    with csv_file.open(encoding="utf-8", newline="") as input_file:
        return [
            {field: row.get(field, "") for field in REPAIR_FIELDS}
            for row in csv.DictReader(input_file)
        ]


def write_repairs(rows, csv_file=LLM_BENCHMARK_REPAIRS_FILE):
    csv_file = Path(csv_file)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=REPAIR_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def next_repair_id(rows):
    return f"llm_benchmark_repair_{len(rows) + 1:06d}"


def append_repair(row, csv_file=LLM_BENCHMARK_REPAIRS_FILE):
    rows = read_repairs(csv_file)
    row = {field: str(row.get(field, "")) for field in REPAIR_FIELDS}
    row["id"] = row.get("id") or next_repair_id(rows)
    rows.append(row)
    write_repairs(rows, csv_file)
    return row


def update_repair(repair_id, updates, csv_file=LLM_BENCHMARK_REPAIRS_FILE):
    rows = read_repairs(csv_file)
    updated = None
    for row in rows:
        if row.get("id") == repair_id or row.get("repair_file") == repair_id:
            row.update({field: str(value) for field, value in updates.items() if field in REPAIR_FIELDS})
            updated = row
            break
    if updated is None:
        raise ValueError(f"reparo LLM nao encontrado: {repair_id}")
    write_repairs(rows, csv_file)
    return updated


def parse_log_metadata(log_path):
    data = {"tool": "", "benchmark": "", "returncode": ""}
    text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith("tool: "):
            data["tool"] = line.removeprefix("tool: ").strip()
        elif line.startswith("benchmark: "):
            data["benchmark"] = line.removeprefix("benchmark: ").strip()
        elif line.startswith("returncode: ") and not data["returncode"]:
            data["returncode"] = line.removeprefix("returncode: ").strip()
    return data, text


def metadata_by_benchmark():
    return read_benchmark_metadata()


def category_for_benchmark(benchmark):
    metadata = metadata_by_benchmark().get(benchmark, {})
    if metadata.get("category"):
        return metadata["category"]
    parts = Path(benchmark).parts
    if "benchmarks" in parts:
        index = parts.index("benchmarks")
        if len(parts) > index + 1:
            return parts[index + 1]
    return ""


def tool_for_benchmark(benchmark, tool=""):
    if tool:
        return TOOL_ALIASES.get(tool, tool)
    return TOOL_BY_CATEGORY.get(category_for_benchmark(benchmark), "asan")


def extract_c_code(response_text, original_code):
    match = re.search(r"```(?:c|C)?\s*(.*?)```", response_text, flags=re.DOTALL)
    if match:
        return match.group(1).strip() + "\n"
    if "#include" in response_text or "int main" in response_text:
        return response_text.strip() + "\n"
    return original_code


def build_prompt(benchmark, category, tool, log_text, source_code):
    return f"""Corrija o benchmark C abaixo para remover o problema detectado.

Regras:
- devolva somente o codigo C completo corrigido;
- preserve o objetivo didatico do benchmark;
- nao use pseudocodigo;
- nao explique em texto fora do codigo;
- mantenha o programa compilavel isoladamente quando possivel.

benchmark: {benchmark}
categoria: {category or 'nao informada'}
ferramenta: {tool or 'nao informada'}

log da ferramenta:
```text
{log_text[:12000]}
```

codigo original:
```c
{source_code}
```
"""


def simulated_repaired_code(category):
    if category == "assertion_violation":
        return """#include <assert.h>

int main(void) {
    int limite = 10;
    int valor = 10;
    assert(valor <= limite);
    return 0;
}
"""
    if category == "data_race":
        return """#include <pthread.h>

static int contador = 0;
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

static void *worker(void *arg) {
    (void)arg;
    pthread_mutex_lock(&mutex);
    contador++;
    pthread_mutex_unlock(&mutex);
    return 0;
}

int main(void) {
    pthread_t t1;
    pthread_t t2;
    pthread_create(&t1, 0, worker, 0);
    pthread_create(&t2, 0, worker, 0);
    pthread_join(t1, 0);
    pthread_join(t2, 0);
    return contador == 2 ? 0 : 1;
}
"""
    if category == "deadlock":
        return """#include <pthread.h>

static pthread_mutex_t primeiro = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t segundo = PTHREAD_MUTEX_INITIALIZER;

static void *worker(void *arg) {
    (void)arg;
    pthread_mutex_lock(&primeiro);
    pthread_mutex_lock(&segundo);
    pthread_mutex_unlock(&segundo);
    pthread_mutex_unlock(&primeiro);
    return 0;
}

int main(void) {
    pthread_t t1;
    pthread_t t2;
    pthread_create(&t1, 0, worker, 0);
    pthread_create(&t2, 0, worker, 0);
    pthread_join(t1, 0);
    pthread_join(t2, 0);
    return 0;
}
"""
    return """#include <stdlib.h>
#include <string.h>

int main(void) {
    char *buffer = (char *)malloc(16);
    if (!buffer) {
        return 1;
    }
    strncpy(buffer, "corrigido", 15);
    buffer[15] = '\\0';
    free(buffer);
    return 0;
}
"""


def simulated_response(category):
    return (
        "LLM repair simulation\n"
        "note: codigo seguro gerado localmente para demonstracao temporaria.\n\n"
        "```c\n"
        f"{simulated_repaired_code(category)}"
        "```\n"
    )


def generate_repair_from_log(log_file, benchmark="", tool="", model=None):
    log_path = PROJECT_ROOT / log_file if not Path(log_file).is_absolute() else Path(log_file)
    log_data, log_text = parse_log_metadata(log_path)
    benchmark = benchmark or log_data.get("benchmark", "")
    if not benchmark:
        raise ValueError("benchmark nao informado e ausente no log")

    benchmark_path = PROJECT_ROOT / benchmark if not Path(benchmark).is_absolute() else Path(benchmark)
    if not benchmark_path.is_file():
        raise ValueError(f"benchmark nao encontrado: {benchmark}")

    source_code = benchmark_path.read_text(encoding="utf-8", errors="replace")
    category = category_for_benchmark(relative_or_raw(benchmark_path))
    tool = tool_for_benchmark(relative_or_raw(benchmark_path), tool or log_data.get("tool", ""))
    model = model or llm_client.configured_model()
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = benchmark_path.stem
    REPAIRS_DIR.mkdir(parents=True, exist_ok=True)
    REPAIRED_BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    repair_file = REPAIRS_DIR / f"{stem}_{timestamp}_repair.txt"
    response_file = REPAIRS_DIR / f"{stem}_{timestamp}_response.json"
    repaired_benchmark = REPAIRED_BENCHMARKS_DIR / f"{stem}_{timestamp}_fixed.c"
    prompt = build_prompt(relative_or_raw(benchmark_path), category, tool, log_text, source_code)
    mode = "real" if llm_client.is_configured() else "simulado"
    error = ""

    if llm_client.is_configured():
        try:
            response_text = llm_client.create_text_response(
                prompt,
                system_prompt=(
                    "Voce e um assistente de seguranca de software. "
                    "Retorne somente codigo C corrigido."
                ),
                model=model,
            )
        except Exception as exc:
            response_text = simulated_response(category)
            mode = "simulado"
            error = f"falha na chamada LLM real; usado fallback simulado: {exc}"
    else:
        response_text = simulated_response(category)
        error = "OPENAI_API_KEY ausente; usado fallback simulado"

    repaired_code = extract_c_code(response_text, source_code)
    repaired_benchmark.write_text(repaired_code, encoding="utf-8")
    repair_file.write_text(
        "\n".join(
            [
                "LLM benchmark repair",
                f"generated_at: {dt.datetime.now().isoformat(timespec='seconds')}",
                f"benchmark: {relative_or_raw(benchmark_path)}",
                f"category: {category}",
                f"tool: {tool}",
                f"source_log: {relative_or_raw(log_path)}",
                f"repaired_benchmark: {relative_or_raw(repaired_benchmark)}",
                f"model: {model}",
                f"mode: {mode}",
                "",
                "response:",
                response_text,
                "",
            ]
        ),
        encoding="utf-8",
    )
    response_file.write_text(
        json.dumps(
            {
                "benchmark": relative_or_raw(benchmark_path),
                "category": category,
                "tool": tool,
                "source_log": relative_or_raw(log_path),
                "model": model,
                "mode": mode,
                "response": response_text,
                "error": error,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    return append_repair(
        {
            "benchmark": relative_or_raw(benchmark_path),
            "category": category,
            "tool": tool,
            "source_log": relative_or_raw(log_path),
            "repair_file": relative_or_raw(repair_file),
            "repaired_benchmark": relative_or_raw(repaired_benchmark),
            "response_file": relative_or_raw(response_file),
            "model": model,
            "mode": mode,
            "status": "gerado",
            "error": error,
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
