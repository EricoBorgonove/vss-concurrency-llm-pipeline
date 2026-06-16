"""Download isolado de links do GitHub."""

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from pipeline_runner.paths import PROJECT_ROOT, display_path

GITHUB_INPUTS_DIR = PROJECT_ROOT / "inputs" / "github_repos"


def repository_clone_url(url):
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("url deve informar usuario e repositorio")
    return f"https://github.com/{parts[0]}/{parts[1]}.git"


def target_path_for(link_id, base_dir=GITHUB_INPUTS_DIR):
    return Path(base_dir) / link_id


def build_shallow_clone_command(url, target_path):
    return [
        "git",
        "clone",
        "--depth",
        "1",
        repository_clone_url(url),
        str(target_path),
    ]


def fetch_repository(link, base_dir=GITHUB_INPUTS_DIR, timeout=120):
    if link.get("url_type") != "repo":
        raise ValueError("download automatico inicial suporta apenas repositorios")
    if link.get("status") == "falhou":
        raise ValueError(link.get("error") or "link marcado como falha")

    target_path = target_path_for(link["id"], base_dir)
    if target_path.exists():
        shutil.rmtree(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    command = build_shallow_clone_command(link["url"], target_path)
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(stderr or f"git clone falhou com codigo {result.returncode}")

    return {
        "local_path": display_path(target_path),
        "command": command,
    }
