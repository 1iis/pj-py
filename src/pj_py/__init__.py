"""pj-py: spawn Python projects from templates."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ghapi.all import GhApi

__version__ = "0.0.1"


class PjPyError(Exception):
    """Base error for pj-py operations."""


class AuthError(PjPyError):
    """Missing or invalid GitHub authentication."""


@dataclass(frozen=True)
class Project:
    """A successfully spawned Python project."""

    owner: str
    repo: str
    path: Path


def _rename_template(path: Path, name: str, desc: str) -> None:
    """Rename template placeholders (my_package -> name) after spawn."""
    pkg = name.replace("-", "_")
    old_pkg = "my_package"
    old_name = old_pkg.replace("_", "-")  # "my-package"

    # 1. Rename directory
    (path / "src" / old_pkg).rename(path / "src" / pkg)

    # 2. Update pyproject.toml: name, scripts entry, description
    pp = path / "pyproject.toml"
    text = pp.read_text()
    text = text.replace(f'name = "{old_name}"', f'name = "{name}"')
    text = text.replace(
        f'{old_name} = "{old_pkg}:main"',
        f'{name} = "{pkg}:main"',
    )
    text = text.replace(
        'description = "One thing, done well."',
        f'description = "{desc}"',
    )
    pp.write_text(text)

    # 3. Update test imports
    tf = path / "tests" / "test_main.py"
    text = tf.read_text()
    text = text.replace(f"from {old_pkg} import", f"from {pkg} import")
    tf.write_text(text)


def init(
    name: str,
    *,
    desc: str = "",
    template: str = "py",
    org: str = "1iis",
    private: bool = True,
    path: Optional[Path] = None,
    token: Optional[str] = None,
) -> Project:
    """Create a new Python project from a template repo.

    Spawns from template -> clones locally -> renames -> uv syncs ->
    git commits + pushes. Returns ready-to-use Project.

    Args:
        name: Project/repo name (e.g., "atlas", "my-lib").
        desc: Short project description.
        template: Template alias ("py") or "owner/repo".
        org: GitHub org/owner for the new repo.
        private: Whether the new repo is private.
        path: Parent directory for local clone (default: cwd).
        token: GitHub token (default: $GITHUB_TOKEN env).

    Returns:
        Project with owner, repo, and local path.
    """
    # --- Resolve template ---
    if "/" in template:
        tmpl_owner, tmpl_repo = template.split("/", 1)
    else:
        aliases = {"py": ("1iis", "py")}
        if template not in aliases:
            raise PjPyError(f"Unknown template alias: {template!r}")
        tmpl_owner, tmpl_repo = aliases[template]

    # --- Auth ---
    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise AuthError(
            "GitHub token required. Set GITHUB_TOKEN or pass token=..."
        )

    api = GhApi(token=token)

    # 1. Spawn from template
    _ = api.repos.create_using_template(
        template_owner=tmpl_owner,
        template_repo=tmpl_repo,
        name=name,
        description=desc,
        private=private,
    )

    # 2. Clone locally (token-embedded URL avoids auth prompt)
    local_path = (path or Path.cwd()) / name
    clone_url = f"https://{token}@github.com/{org}/{name}.git"
    subprocess.run(["git", "clone", clone_url, str(local_path)], check=True)

    # 3. Rename template placeholders
    _rename_template(local_path, name, desc)

    # 4. Install dependencies
    subprocess.run(["uv", "sync", "--group", "dev"], cwd=local_path, check=True)

    # 5. Git commit + push
    subprocess.run(["git", "add", "-A"], cwd=local_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=local_path, check=True
    )
    subprocess.run(["git", "push"], cwd=local_path, check=True)

    return Project(owner=org, repo=name, path=local_path)

def main() -> None:
    """CLI entry point. Minimal; full UX lives in higher-level wrappers."""
    try:
        p = init(sys.argv[1])
        print(f"Created {p.owner}/{p.repo} at {p.path}")
    except PjPyError as e:
        print(f"pj-py error: {e}", file=sys.stderr)
        sys.exit(1)
