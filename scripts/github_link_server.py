#!/usr/bin/env python3
"""Servidor local para entrada de links do GitHub."""

import argparse
import datetime as dt
import json
import sys
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
    replace_files_for_link,
    resolve_local_path,
)
from pipeline_runner.github_findings import (  # noqa: E402
    finding_counts_by_link,
    read_findings,
    replace_findings_for_link,
)
from pipeline_runner.github_links import append_link, get_link, read_links, update_link  # noqa: E402

WEB_DIR = PROJECT_ROOT / "web"
INDEX_FILE = WEB_DIR / "github_input.html"


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

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/github"):
            self.send_html(200, INDEX_FILE.read_text(encoding="utf-8"))
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

        self.send_json(404, {"error": "rota nao encontrada"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/github-links":
            self.handle_create_link()
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

        self.send_json(404, {"error": "rota nao encontrada"})

    def handle_create_link(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(raw_body or "{}")
            row = append_link(payload.get("url", ""))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "json invalido"})
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
                raise ValueError("repositorio ainda nao foi baixado")
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
