#!/usr/bin/env python3
"""Servidor local para entrada de links do GitHub."""

import argparse
import datetime as dt
import json
import mimetypes
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline_runner.github_fetcher import fetch_repository  # noqa: E402
from pipeline_runner.github_files import (  # noqa: E402
    discover_code_files,
    file_counts_by_link,
    read_files,
    remove_files_for_link,
    replace_files_for_link,
    resolve_local_path,
)
from pipeline_runner.github_findings import (  # noqa: E402
    finding_counts_by_link,
    read_findings,
    remove_findings_for_link,
    replace_findings_for_link,
    update_finding_status,
)
from pipeline_runner.github_links import (  # noqa: E402
    append_link,
    get_link,
    read_links,
    remove_link,
    update_link,
)
from pipeline_runner.github_tool_validations import (  # noqa: E402
    read_validations,
    validate_findings_file,
)

WEB_DIR = PROJECT_ROOT / "web"
INDEX_FILE = WEB_DIR / "github_input.html"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
BENCHMARK_RUN_LOG = REPORTS_DIR / "benchmark_run_latest.log"
BENCHMARK_RUN_LOCK = threading.Lock()
BENCHMARK_RUN_STATE = {
    "status": "idle",
    "started_at": "",
    "finished_at": "",
    "returncode": None,
    "log_file": "",
    "error": "",
}
GITHUB_VALIDATION_RUN_LOG = REPORTS_DIR / "github_validation_run_latest.log"
GITHUB_VALIDATION_RUN_LOCK = threading.Lock()
GITHUB_VALIDATION_RUN_STATE = {
    "status": "idle",
    "started_at": "",
    "finished_at": "",
    "count": 0,
    "processed": 0,
    "total": 0,
    "current_finding_id": "",
    "current_tool": "",
    "limit": "",
    "timeout": "",
    "log_file": "",
    "error": "",
}


def env_int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def env_optional_int(name):
    value = os.environ.get(name, "").strip()
    if not value or value.lower() in ("0", "all", "todos", "none"):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def build_parser():
    parser = argparse.ArgumentParser(
        description="Serve a pagina de entrada de links do GitHub."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host do servidor.")
    parser.add_argument("--port", type=int, default=8080, help="Porta do servidor.")
    return parser


def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=True).encode("utf-8")


def links_with_file_counts():
    file_counts = file_counts_by_link()
    finding_counts = finding_counts_by_link()
    links = []
    for link in read_links():
        enriched = dict(link)
        link_id = link.get("id", "")
        enriched["file_count"] = file_counts.get(link_id, 0)
        enriched["finding_count"] = finding_counts.get(link_id, 0)
        links.append(enriched)
    return links


def benchmark_run_status():
    with BENCHMARK_RUN_LOCK:
        return dict(BENCHMARK_RUN_STATE)


def update_benchmark_run_state(**updates):
    with BENCHMARK_RUN_LOCK:
        BENCHMARK_RUN_STATE.update(updates)
        return dict(BENCHMARK_RUN_STATE)


def github_validation_run_status():
    with GITHUB_VALIDATION_RUN_LOCK:
        return dict(GITHUB_VALIDATION_RUN_STATE)


def update_github_validation_run_state(**updates):
    with GITHUB_VALIDATION_RUN_LOCK:
        GITHUB_VALIDATION_RUN_STATE.update(updates)
        return dict(GITHUB_VALIDATION_RUN_STATE)


def run_benchmark_pipeline():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "run_pipeline.py"]
    started_at = dt.datetime.now().isoformat(timespec="seconds")
    update_benchmark_run_state(
        status="running",
        started_at=started_at,
        finished_at="",
        returncode=None,
        log_file=str(BENCHMARK_RUN_LOG.relative_to(PROJECT_ROOT)),
        error="",
    )

    with BENCHMARK_RUN_LOG.open("w", encoding="utf-8") as log_file:
        log_file.write(f"$ {' '.join(command)}\n")
        log_file.write(f"Início: {started_at}\n\n")
        log_file.flush()
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        finished_at = dt.datetime.now().isoformat(timespec="seconds")
        log_file.write(f"\nFim: {finished_at}\n")
        log_file.write(f"Código de retorno: {result.returncode}\n")

    update_benchmark_run_state(
        status="succeeded" if result.returncode == 0 else "failed",
        finished_at=finished_at,
        returncode=result.returncode,
        error="" if result.returncode == 0 else "A execução dos benchmarks falhou.",
    )


def run_github_validations():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    limit = env_optional_int("GITHUB_VALIDATION_LIMIT")
    timeout = env_int("GITHUB_VALIDATION_TIMEOUT", 10)
    started_at = dt.datetime.now().isoformat(timespec="seconds")
    update_github_validation_run_state(
        status="running",
        started_at=started_at,
        finished_at="",
        count=0,
        processed=0,
        total=0,
        current_finding_id="",
        current_tool="",
        limit="" if limit is None else limit,
        timeout=timeout,
        log_file=str(GITHUB_VALIDATION_RUN_LOG.relative_to(PROJECT_ROOT)),
        error="",
    )

    try:
        with GITHUB_VALIDATION_RUN_LOG.open("w", encoding="utf-8") as log_file:
            log_file.write("Validação global dos achados GitHub\n")
            log_file.write(f"Início: {started_at}\n")
            log_file.write(f"Limite: {'todos' if limit is None else limit}\n")
            log_file.write(f"Timeout por ferramenta: {timeout}s\n\n")
            log_file.flush()

            def update_progress(processed, total, finding_id, tool):
                update_github_validation_run_state(
                    processed=processed,
                    total=total,
                    current_finding_id=finding_id,
                    current_tool=tool,
                )

            rows = validate_findings_file(
                limit=limit,
                timeout=timeout,
                progress_callback=update_progress,
            )
            finished_at = dt.datetime.now().isoformat(timespec="seconds")
            log_file.write(f"Validações registradas: {len(rows)}\n")
            log_file.write(f"Fim: {finished_at}\n")

        update_github_validation_run_state(
            status="succeeded",
            finished_at=finished_at,
            count=len(rows),
            processed=len(rows),
            total=len(rows),
            current_finding_id="",
            current_tool="",
            error="",
        )
    except Exception as exc:
        finished_at = dt.datetime.now().isoformat(timespec="seconds")
        with GITHUB_VALIDATION_RUN_LOG.open("a", encoding="utf-8") as log_file:
            log_file.write(f"\nErro: {exc}\n")
            log_file.write(f"Fim: {finished_at}\n")
        update_github_validation_run_state(
            status="failed",
            finished_at=finished_at,
            current_finding_id="",
            current_tool="",
            error=str(exc),
        )


class GitHubLinkHandler(BaseHTTPRequestHandler):
    server_version = "GitHubLinkServer/0.1"

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)

    def send_json(self, status, payload):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, status, content):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_project_file(self, route_prefix, base_dir, path):
        relative_path = path.removeprefix(route_prefix).strip("/")
        file_path = (base_dir / relative_path).resolve()
        try:
            file_path.relative_to(base_dir.resolve())
        except ValueError:
            self.send_json(404, {"error": "rota não encontrada"})
            return

        if not file_path.is_file():
            self.send_json(404, {"error": "arquivo não encontrado"})
            return

        self.send_file(file_path)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/github"):
            self.send_html(200, INDEX_FILE.read_text(encoding="utf-8"))
            return

        if path.startswith("/reports/"):
            self.send_project_file("/reports/", REPORTS_DIR, path)
            return

        if path.startswith("/outputs/"):
            self.send_project_file("/outputs/", OUTPUTS_DIR, path)
            return

        if path.startswith("/benchmarks/"):
            self.send_project_file("/benchmarks/", BENCHMARKS_DIR, path)
            return

        if path == "/api/github-links":
            self.send_json(200, {"links": links_with_file_counts()})
            return

        if path == "/api/github-files":
            self.send_json(200, {"files": read_files()})
            return

        if path == "/api/github-findings":
            self.send_json(200, {"findings": read_findings()})
            return

        if path == "/api/github-validations":
            self.send_json(200, {"validations": read_validations()})
            return

        if path == "/api/github-validations/run":
            self.send_json(200, {"run": github_validation_run_status()})
            return

        if path == "/api/benchmark-run":
            self.send_json(200, {"run": benchmark_run_status()})
            return

        self.send_json(404, {"error": "rota não encontrada"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/github-links":
            self.handle_create_link()
            return

        if path == "/api/github-validations/run":
            self.handle_run_validations()
            return

        if path == "/api/benchmark-run":
            self.handle_run_benchmarks()
            return

        if path.startswith("/api/github-findings/") and path.endswith("/validate"):
            finding_id = path.removeprefix("/api/github-findings/").removesuffix("/validate").strip("/")
            self.handle_validate_finding(finding_id)
            return

        if path.startswith("/api/github-links/") and path.endswith("/fetch"):
            link_id = path.removeprefix("/api/github-links/").removesuffix("/fetch").strip("/")
            self.handle_fetch_link(link_id)
            return

        if path.startswith("/api/github-links/") and path.endswith("/discover"):
            link_id = path.removeprefix("/api/github-links/").removesuffix("/discover").strip("/")
            self.handle_discover_files(link_id)
            return

        if path.startswith("/api/github-links/") and path.endswith("/triage"):
            link_id = path.removeprefix("/api/github-links/").removesuffix("/triage").strip("/")
            self.handle_triage_link(link_id)
            return

        if path.startswith("/api/github-links/") and path.endswith("/validate"):
            link_id = path.removeprefix("/api/github-links/").removesuffix("/validate").strip("/")
            self.handle_validate_link(link_id)
            return

        self.send_json(404, {"error": "rota não encontrada"})

    def do_PATCH(self):
        path = urlparse(self.path).path
        if path.startswith("/api/github-findings/"):
            finding_id = path.removeprefix("/api/github-findings/").strip("/")
            self.handle_update_finding_status(finding_id)
            return

        self.send_json(404, {"error": "rota não encontrada"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/github-links/"):
            link_id = path.removeprefix("/api/github-links/").strip("/")
            self.handle_remove_link(link_id)
            return

        self.send_json(404, {"error": "rota não encontrada"})

    def handle_create_link(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(raw_body or "{}")
            row = append_link(payload.get("url", ""))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON inválido"})
            return
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return

        self.send_json(201, {"link": row})

    def handle_fetch_link(self, link_id):
        started_at = dt.datetime.now().isoformat(timespec="seconds")
        try:
            link = get_link(link_id)
            if link.get("status") == "falhou":
                raise ValueError(link.get("error") or "link marcado como falha")
            link = update_link(
                link_id,
                {
                    "status": "baixando",
                    "error": "",
                    "started_at": started_at,
                    "finished_at": "",
                },
            )
            result = fetch_repository(link)
            row = update_link(
                link_id,
                {
                    "status": "concluido",
                    "local_path": result["local_path"],
                    "error": "",
                    "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except Exception as exc:
            row = update_link(
                link_id,
                {
                    "status": "falhou",
                    "error": str(exc),
                    "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )
            self.send_json(500, {"link": row, "error": str(exc)})
            return

        self.send_json(200, {"link": row})

    def handle_discover_files(self, link_id):
        try:
            link = get_link(link_id)
            local_path = link.get("local_path", "")
            if not local_path:
                raise ValueError("repositório ainda não foi baixado")
            files = discover_code_files(resolve_local_path(local_path))
            rows = replace_files_for_link(link_id, files)
            row = update_link(
                link_id,
                {
                    "status": "arquivos_descobertos",
                    "error": "" if rows else "nenhum arquivo C/C++ encontrado",
                    "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except Exception as exc:
            row = update_link(
                link_id,
                {
                    "status": "falhou",
                    "error": str(exc),
                    "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )
            self.send_json(500, {"link": row, "error": str(exc)})
            return

        enriched = dict(row)
        enriched["file_count"] = len(rows)
        self.send_json(200, {"link": enriched, "files": rows})

    def handle_triage_link(self, link_id):
        try:
            files = [row for row in read_files() if row.get("link_id") == link_id]
            if not files:
                raise ValueError("nenhum arquivo C/C++ descoberto para este link")
            findings = replace_findings_for_link(link_id, files)
            row = update_link(
                link_id,
                {
                    "status": "triagem_concluida",
                    "error": "" if findings else "nenhum padrao suspeito encontrado",
                    "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return
        except Exception as exc:
            row = update_link(
                link_id,
                {
                    "status": "falhou",
                    "error": str(exc),
                    "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
                },
            )
            self.send_json(500, {"link": row, "error": str(exc)})
            return

        enriched = dict(row)
        enriched["file_count"] = len(files)
        enriched["finding_count"] = len(findings)
        self.send_json(200, {"link": enriched, "findings": findings})

    def handle_remove_link(self, link_id):
        try:
            removed_id = remove_link(link_id)
            remove_files_for_link(link_id)
            remove_findings_for_link(link_id)
        except ValueError as exc:
            self.send_json(404, {"error": str(exc)})
            return

        self.send_json(200, {"removed_id": removed_id})

    def handle_update_finding_status(self, finding_id):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(raw_body or "{}")
            row = update_finding_status(finding_id, payload.get("status", ""))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "JSON inválido"})
            return
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
            return

        self.send_json(200, {"finding": row})

    def handle_run_validations(self):
        state = github_validation_run_status()
        if state.get("status") == "running":
            self.send_json(409, {"run": state, "error": "já existe uma validação em andamento"})
            return

        update_github_validation_run_state(
            status="running",
            started_at=dt.datetime.now().isoformat(timespec="seconds"),
            finished_at="",
            count=0,
            processed=0,
            total=0,
            current_finding_id="",
            current_tool="",
            limit="",
            timeout="",
            log_file=str(GITHUB_VALIDATION_RUN_LOG.relative_to(PROJECT_ROOT)),
            error="",
        )
        thread = threading.Thread(target=run_github_validations, daemon=True)
        thread.start()
        self.send_json(202, {"run": github_validation_run_status()})

    def handle_run_benchmarks(self):
        state = benchmark_run_status()
        if state.get("status") == "running":
            self.send_json(409, {"run": state, "error": "já existe uma execução em andamento"})
            return

        update_benchmark_run_state(
            status="running",
            started_at=dt.datetime.now().isoformat(timespec="seconds"),
            finished_at="",
            returncode=None,
            log_file=str(BENCHMARK_RUN_LOG.relative_to(PROJECT_ROOT)),
            error="",
        )
        thread = threading.Thread(target=run_benchmark_pipeline, daemon=True)
        thread.start()
        self.send_json(202, {"run": benchmark_run_status()})

    def handle_validate_link(self, link_id):
        limit = env_int("GITHUB_LINK_VALIDATION_LIMIT", 10)
        timeout = env_int("GITHUB_VALIDATION_TIMEOUT", 10)

        try:
            rows = validate_findings_file(link_id=link_id, limit=limit, timeout=timeout)
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})
            return

        self.send_json(
            200,
            {
                "validations": rows,
                "count": len(rows),
                "link_id": link_id,
                "limit": limit,
                "timeout": timeout,
            },
        )

    def handle_validate_finding(self, finding_id):
        timeout = env_int("GITHUB_VALIDATION_TIMEOUT", 10)

        try:
            rows = validate_findings_file(finding_id=finding_id, timeout=timeout)
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})
            return

        self.send_json(
            200,
            {
                "validations": rows,
                "count": len(rows),
                "finding_id": finding_id,
                "timeout": timeout,
            },
        )


class LocalThreadingHTTPServer(ThreadingHTTPServer):
    def server_bind(self):
        TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


def main():
    args = build_parser().parse_args()
    server = LocalThreadingHTTPServer((args.host, args.port), GitHubLinkHandler)
    print(f"Servidor iniciado em http://{args.host}:{args.port}")
    print("Pressione Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
