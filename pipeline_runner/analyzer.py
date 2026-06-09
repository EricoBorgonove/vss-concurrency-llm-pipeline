"""Inferencia leve de ferramentas a partir do conteudo de benchmarks C."""

import re

ASSERT_MARKERS = ("__ESBMC_assert", "assert(")
MEMORY_MARKERS = (
    "malloc(",
    "calloc(",
    "realloc(",
    "free(",
    "strcpy(",
    "strcat(",
    "sprintf(",
    "gets(",
    "memcpy(",
    "memmove(",
)
INPUT_MARKERS = (
    "argc",
    "argv",
    "stdin",
    "scanf(",
    "fscanf(",
    "fgets(",
    "getchar(",
    "read(",
)
PTHREAD_MARKERS = ("pthread_create", "pthread_join", "pthread_mutex_")


def strip_c_comments(source):
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*", "", source)


def infer_tools_from_source(source):
    code = strip_c_comments(source)
    tools = set()

    if any(marker in code for marker in ASSERT_MARKERS):
        tools.add("esbmc")

    has_memory_marker = any(marker in code for marker in MEMORY_MARKERS)
    has_array_index = bool(re.search(r"\w+\s*\[[^\]]+\]\s*=", code))
    if has_memory_marker or has_array_index:
        tools.add("asan")

    if has_memory_marker or any(marker in code for marker in INPUT_MARKERS):
        tools.add("afl")

    if any(marker in code for marker in PTHREAD_MARKERS):
        tools.add("tsan")

    if "pthread_mutex_lock" in code:
        tools.add("deadlock")

    return tuple(sorted(tools))


def infer_tools_from_file(path):
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ()

    return infer_tools_from_source(source)
