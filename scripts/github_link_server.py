#!/usr/bin/env python3
"""Servidor local para entrada de links do GitHub."""

import argparse
import datetime as dt
import hmac
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socketserver import TCPServer
from urllib.parse import parse_qs, quote, urlparse

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
VALIDATIONS_FILE = WEB_DIR / "validations.html"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
SESSION_COOKIE_NAME = "vss_session"
AUTH_USERNAME = os.environ.get("VSS_AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("VSS_AUTH_PASSWORD", "vss")
AUTH_SESSIONS = {}
AUTH_SESSIONS_LOCK = threading.Lock()
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


SESSION_TTL_SECONDS = env_int("VSS_SESSION_TTL_SECONDS", 12 * 60 * 60)


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


def is_auth_configured_with_default():
    return AUTH_USERNAME == "admin" and AUTH_PASSWORD == "vss"


def create_session():
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + SESSION_TTL_SECONDS
    with AUTH_SESSIONS_LOCK:
        AUTH_SESSIONS[token] = expires_at
    return token, expires_at


def delete_session(token):
    if not token:
        return
    with AUTH_SESSIONS_LOCK:
        AUTH_SESSIONS.pop(token, None)


def valid_session(token):
    if not token:
        return False
    now = time.time()
    with AUTH_SESSIONS_LOCK:
        expires_at = AUTH_SESSIONS.get(token)
        if not expires_at:
            return False
        if expires_at <= now:
            AUTH_SESSIONS.pop(token, None)
            return False
    return True


def login_page(error="", next_path="/github"):
    error_html = (
        f'<p class="message error">{html_escape(error)}</p>'
        if error
        else '<p class="message">Entre para acessar o painel.</p>'
    )
    default_warning = (
        '<p class="message warning">Usando credenciais padrao de desenvolvimento. '
        'Na AWS, defina VSS_AUTH_USERNAME e VSS_AUTH_PASSWORD.</p>'
        if is_auth_configured_with_default()
        else ""
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Login - Pipeline VSS-LLM</title>
  <style>
    :root {{
      --bg: #f3f6f8;
      --surface: #ffffff;
      --line: #d9e2ec;
      --text: #1f2933;
      --muted: #52606d;
      --accent: #2563eb;
      --danger: #b42318;
      --warning: #8a5a00;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      align-items: center;
      background: var(--bg);
      color: var(--text);
      display: flex;
      font-family: Inter, Arial, sans-serif;
      justify-content: center;
      margin: 0;
      min-height: 100vh;
      padding: 20px;
    }}
    main {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      display: grid;
      gap: 14px;
      padding: 22px;
      width: min(420px, 100%);
    }}
    h1 {{ font-size: 24px; margin: 0; }}
    p {{ margin: 0; }}
    label {{
      color: var(--muted);
      display: grid;
      font-size: 13px;
      gap: 6px;
    }}
    input, button {{
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--text);
      font: inherit;
      min-height: 40px;
      padding: 8px 10px;
    }}
    button {{
      background: var(--accent);
      border-color: var(--accent);
      color: #ffffff;
      cursor: pointer;
    }}
    .message {{ color: var(--muted); }}
    .message.error {{ color: var(--danger); }}
    .message.warning {{ color: var(--warning); }}
  </style>
</head>
<body>
  <main>
    <h1>Pipeline VSS-LLM</h1>
    {error_html}
    {default_warning}
    <form method="post" action="/login">
      <input type="hidden" name="next" value="{html_escape(next_path)}">
      <label>Usuário
        <input name="username" autocomplete="username" required>
      </label>
      <label>Senha
        <input name="password" type="password" autocomplete="current-password" required>
      </label>
      <button type="submit">Entrar</button>
    </form>
  </main>
</body>
</html>"""


def html_escape(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


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

    def session_token(self):
        raw_cookie = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel else ""

    def is_authenticated(self):
        return valid_session(self.session_token())

    def is_login_route(self, path):
        return path in ("/login", "/logout")

    def wants_json(self, path):
        accept = self.headers.get("Accept", "")
        return path.startswith("/api/") or "application/json" in accept

    def require_auth(self, path):
        if self.is_login_route(path):
            return True
        if self.is_authenticated():
            return True

        if self.wants_json(path):
            self.send_json(401, {"error": "autenticação necessária"})
            return False

        next_path = quote(self.path or "/github", safe="/:?&=%")
        self.send_redirect(f"/login?next={next_path}")
        return False

    def send_json(self, status, payload):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_redirect(self, location, extra_headers=None):
        self.send_response(303)
        self.send_header("Location", location)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def session_cookie_header(self, token, expires_at):
        max_age = max(int(expires_at - time.time()), 0)
        cookie = SimpleCookie()
        cookie[SESSION_COOKIE_NAME] = token
        cookie[SESSION_COOKIE_NAME]["path"] = "/"
        cookie[SESSION_COOKIE_NAME]["httponly"] = True
        cookie[SESSION_COOKIE_NAME]["samesite"] = "Lax"
        cookie[SESSION_COOKIE_NAME]["max-age"] = str(max_age)
        return cookie.output(header="").strip()

    def expired_session_cookie_header(self):
        cookie = SimpleCookie()
        cookie[SESSION_COOKIE_NAME] = ""
        cookie[SESSION_COOKIE_NAME]["path"] = "/"
        cookie[SESSION_COOKIE_NAME]["httponly"] = True
        cookie[SESSION_COOKIE_NAME]["samesite"] = "Lax"
        cookie[SESSION_COOKIE_NAME]["max-age"] = "0"
        return cookie.output(header="").strip()

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
        if path == "/login":
            query = parse_qs(urlparse(self.path).query)
            next_path = query.get("next", ["/github"])[0] or "/github"
            if self.is_authenticated():
                self.send_redirect(next_path)
                return
            self.send_html(200, login_page(next_path=next_path))
            return

        if path == "/logout":
            token = self.session_token()
            delete_session(token)
            self.send_redirect(
                "/login",
                {"Set-Cookie": self.expired_session_cookie_header()},
            )
            return

        if not self.require_auth(path):
            return

        if path in ("/", "/github"):
            self.send_html(200, INDEX_FILE.read_text(encoding="utf-8"))
            return

        if path == "/validacoes":
            self.send_html(200, VALIDATIONS_FILE.read_text(encoding="utf-8"))
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
        if path == "/login":
            self.handle_login()
            return

        if not self.require_auth(path):
            return

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
        if not self.require_auth(path):
            return

        if path.startswith("/api/github-findings/"):
            finding_id = path.removeprefix("/api/github-findings/").strip("/")
            self.handle_update_finding_status(finding_id)
            return

        self.send_json(404, {"error": "rota não encontrada"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not self.require_auth(path):
            return

        if path.startswith("/api/github-links/"):
            link_id = path.removeprefix("/api/github-links/").strip("/")
            self.handle_remove_link(link_id)
            return

        self.send_json(404, {"error": "rota não encontrada"})

    def handle_login(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(length).decode("utf-8")
        payload = parse_qs(raw_body)
        username = payload.get("username", [""])[0]
        password = payload.get("password", [""])[0]
        next_path = payload.get("next", ["/github"])[0] or "/github"
        if not next_path.startswith("/"):
            next_path = "/github"

        user_ok = hmac.compare_digest(username, AUTH_USERNAME)
        password_ok = hmac.compare_digest(password, AUTH_PASSWORD)
        if not user_ok or not password_ok:
            self.send_html(401, login_page("Usuário ou senha inválidos.", next_path))
            return

        token, expires_at = create_session()
        self.send_redirect(
            next_path,
            {"Set-Cookie": self.session_cookie_header(token, expires_at)},
        )

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
