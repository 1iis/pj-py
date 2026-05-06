# pj-py

Spawn Python projects from templates.

## What it does

Create a new Python project ready for `uv run pytest`:

```bash
pip install pj-py
pj-py init my-lib
```

This spawns a new GitHub repo from [1iis/py](https://github.com/1iis/py) (the reference Python template),
clones it locally, renames everything to match your project, installs deps, and makes the initial commit.
You start coding immediately — no scaffolding, no boilerplate.

## Prerequisites

- **Python 3.10+**
- **uv** ([install](https://docs.astral.sh/uv/#installation))
- **GitHub token** with repo scope — set `GITHUB_TOKEN` in your environment or pass `token=...`
- **git**

## Usage

```python
from pj_py import init

p = init("my-lib")
# → Project(owner="1iis", repo="my-lib", path=Path("my-lib"))
```

### CLI (for testing)

```bash
pj-py init my-lib -d "Does one thing well"
```

The full CLI experience lives in the higher-level `pj` wrapper (coming soon).

### Options

| Param | Default | Description |
|-------|---------|-------------|
| `name` | (required) | Repo name and local directory |
| `desc` | `""` | Short project description |
| `template` | `"py"` | Alias resolves to `1iis/py`. Full `owner/repo` also accepted |
| `org` | `"1iis"` | GitHub org/owner for the new repo |
| `private` | `True` | Whether the new repo is private |
| `path` | `cwd` | Parent directory for the local clone |
| `token` | `$GITHUB_TOKEN` | GitHub personal access token |

### What you get

A project following the `1iis/py` template conventions:

```
my-lib/
├── src/
│   └── my_lib/          # package directory, renamed from my_package
│       ├── __init__.py   # version + main entry point
│       ├── __main__.py   # python -m support
│       └── py.typed     # typed package marker
├── tests/
│   └── test_main.py     # smoke test, imports from your package
├── pyproject.toml        # hatchling build, ruff linting, fastship deploy
├── .python-version      # pinned to 3.12
├── CHANGELOG.md         # fastship-ready
├── .github/workflows/ci.yml
└── LICENSE              # Apache 2.0
```

## Why not just use `gh repo create --template`?

That command creates the repo but leaves you with:
- `pyproject.toml` still says `my-package`
- `src/my_package/` hasn't been renamed
- Tests import from `my_package`
- No `uv sync` has run
- No initial commit

`pj-py` automates all of that.

## Architecture

```
1iis/py    — Language template (hatchling, ruff, uv, fastship)
    ↓
pj-py      — Spawns + renames + syncs + commits from templates
 ↓
pj         — Language-agnostic wrapper routing to pj-py, pj-js, etc.
```

## Design

- **Pure library** — all UX (colors, progress bars, interactive prompts) lives in a higher-level wrapper
- **Raise, don't print** — errors are exceptions (`PjPyError`, `AuthError`) for programmatic consumption
- **Blocking** — `init()` returns only when the project is fully ready
- **Single responsibility** — knows Python templates. That's it.
