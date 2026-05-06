"""pj-py: spawn Python projects from templates."""
__version__ = "0.0.5"





import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ghapi.all import GhApi


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


def _parse_remote_owner_repo(path: Path) -> tuple[str, str]:
    """Extract owner/repo from git remote origin URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=path, capture_output=True, text=True, check=True,
    )
    url = result.stdout.strip()
    m = re.search(r'(?:github\.com[:/])([\w.-]+)/([\w.-]+?)(?:\.git)?$', url)
    if not m:
        raise PjPyError(f"Cannot parse owner/repo from origin URL: {url}")
    return m.group(1), m.group(2)


def ship(
    msg: str = "",
    bump: str = "patch",
    path: Optional[Path] = None,
) -> str:
    """Bump, write changelog, release on GitHub, publish to PyPI.

    Delegates version bump to fastship's ship-bump and PyPI build+upload
    to fastship's ship-pypi. Expects GITHUB_TOKEN (or FASTSHIP_TOKEN) for
    GitHub releases, and .pypirc configured for PyPI.

    Args:
        msg: Changelog entry text. If empty, generates simple boilerplate.
        bump: "patch" (default), "minor", or "major".
        path: Project root (default: cwd).

    Returns:
        New version string (e.g., "0.0.3").
    """
    path = path or Path.cwd()
    parts = {"patch": 2, "minor": 1, "major": 0}
    if bump not in parts:
        raise PjPyError(f"Invalid bump type: {bump!r}")

    # 1. Bump version via fastship
    subprocess.run(
        ["uv", "run", "ship-bump", "--part", str(parts[bump])],
        cwd=path, check=True,
    )

    # 2. Read bumped version back
    pkg_dirs = [d for d in (path / "src").iterdir() if d.is_dir()]
    if not pkg_dirs:
        raise PjPyError("No package directory found in src/")
    init_file = pkg_dirs[0] / "__init__.py"
    text = init_file.read_text()
    m = re.search(r'__version__\s*=\s*"(\d+\.\d+\.\d+)"', text)
    if not m:
        raise PjPyError("Could not find __version__ in __init__.py")
    new_version = m.group(1)

    # 3. Write changelog entry
    changelog = path / "CHANGELOG.md"
    text = changelog.read_text()
    if not msg:
        msg = f"### What's new\n\n- {bump.capitalize()} release."
    entry = f"\n\n## {new_version}\n\n{msg.strip()}\n"
    text = text.replace("<!-- do not remove -->", f"<!-- do not remove -->{entry}")
    changelog.write_text(text)

    # 4. Git commit + push
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"v{new_version}"],
        cwd=path, check=True,
    )
    subprocess.run(["git", "push"], cwd=path, check=True)

    # 5. Create GitHub release
    token = (os.environ.get("FASTSHIP_TOKEN") or os.environ.get("GITHUB_TOKEN"))
    if token:
        owner, repo_name = _parse_remote_owner_repo(path)
        api = GhApi(token=token)
        api.repos.create_release(
            owner=owner, repo=repo_name,
            tag_name=f"v{new_version}",
            name=f"v{new_version}",
            body=msg,
        )

    # 6. Build + upload to PyPI
    subprocess.run(
        ["uv", "run", "ship-pypi", "--quiet"],
        cwd=path, check=True,
    )


    return new_version


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

    # 1. Spawn from template under the target org
    repo = api.repos.create_using_template(
        template_owner=tmpl_owner,
        template_repo=tmpl_repo,
        owner=org,
        name=name,
        description=desc,
        private=private,
    )

    # 2. Clone locally (token-embedded URL avoids auth prompt)
    local_path = (path or Path.cwd()) / name
    actual_owner = repo.owner.login
    clone_url = f"https://{token}@github.com/{actual_owner}/{name}.git"
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
    if len(sys.argv) < 2:
        print("Usage: pj-py init|ship ...", file=sys.stderr)
        sys.exit(1)
    cmd = sys.argv[1]
    try:
        if cmd == "init":
            p = init(sys.argv[2])
            print(f"Created {p.owner}/{p.repo} at {p.path}")
        elif cmd == "ship":
            msg = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else ""
            v = ship(msg=msg)
            print(f"Shipped v{v}")
        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            sys.exit(1)
    except PjPyError as e:
        print(f"pj-py error: {e}", file=sys.stderr)
        sys.exit(1)
