# pj-py

Spawn and ship Python projects from templates.

```bash
pip install pj-py
pj-py init my-lib   # create
# ... code, commit, push ...
pj-py ship           # release
```

## Commands

### `init` — create a project

```bash
pj-py init my-lib -d "Does one thing well"
```

Spawns a new GitHub repo from [1iis/py](https://github.com/1iis/py) (the reference Python template),
clones it locally, renames `my_package` to your project name, installs dependencies, and makes the
initial commit.

```python
from pj_py import init

p = init("my-lib")
# → Project(owner="1iis", repo="my-lib", path=Path("my-lib"))
```

| Param | Default | Description |
|-------|---------|-------------|
| `name` | (required) | Repo name and local directory |
| `desc` | `""` | Short project description |
| `template` | `"py"` | Alias → `1iis/py`. Full `owner/repo` also accepted |
| `org` | `"1iis"` | GitHub owner for the new repo |
| `private` | `True` | Whether the repo is private |
| `path` | `cwd` | Parent directory for the clone |
| `token` | `$GITHUB_TOKEN` | GitHub PAT |

### `ship` — release a new version

```bash
pj-py ship "### Added\n\n- Feature X"
pj-py ship                    # auto-generates boilerplate
```

Non-interactive, one-call release: bumps the version via `fastship`, writes the changelog entry,
commits and pushes, creates a GitHub release, and uploads to PyPI.

```python
from pj_py import ship

v = ship()                     # patch bump
v = ship("minor")              # minor bump
v = ship("major")              # major bump
# → "0.0.3"
```

| Param | Default | Description |
|-------|---------|-------------|
| `msg` | `""` | Changelog entry. Empty → boilerplate |
| `bump` | `"patch"` | Version part to bump |
| `path` | `cwd` | Project root |
| `token` | `$GITHUB_TOKEN` / `$FASTSHIP_TOKEN` | For GitHub releases (optional, falls back to no GH release) |

Requires `.pypirc` configured for PyPI uploads.

## Prerequisites

- **Python 3.10+**
- **uv** ([install](https://docs.astral.sh/uv/#installation))
- **git**
- **[GitHub token](https://github.com/settings/tokens/new)** with repo scope for `init` — set `GITHUB_TOKEN`
- **`.pypirc`** with **[PyPI token](https://pypi.org/manage/account/token/)** for `ship`
- **[fastship](https://github.com/AnswerDotAI/fastship)**


## What you get

```
my-lib/
├── src/
│   └── my_lib/          # renamed from my_package
│       ├── __init__.py   # version + main entry point
│       ├── __main__.py   # python -m support
│       └── py.typed     # typed marker
├── tests/
│   └── test_main.py     # smoke test
├── pyproject.toml        # hatchling, ruff, fastship
├── .python-version      # 3.12
├── CHANGELOG.md         # fastship-ready
├── .github/workflows/ci.yml
└── LICENSE              # Apache 2.0
```

## Architecture

```
1iis/py    — Language template (hatchling, ruff, uv, fastship)
    ↓
pj-py      — init() + ship() from templates
 ↓
pj         — (future) Language-agnostic wrapper
```

## Design

- **Pure library** — all UX (colors, progress bars, interactive prompts) lives in a higher-level wrapper
- **Raise, don't print** — errors are exceptions (`PjPyError`, `AuthError`, `ShipError`)
- **Blocking** — `init()` and `ship()` return only when the project is fully ready
- **Single responsibility** — knows Python templates and Python packaging. That's it.
- **Lean** — delegates to `fastship` for version bumping and PyPI upload, to `ghapi` for GitHub API, to `uv` for dependency management
