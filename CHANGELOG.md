<!-- do not remove -->

## 0.0.3

### Added\n\n- `ship()` — bump, changelog, GH release, PyPI publish in one call\n- `_parse_remote_owner_repo()` — helper to extract owner/repo from git origin


## 0.0.2

### Added

- `init()` — spawn Python projects from the `1iis/py` template with one call
- `_rename_template()` — renames package directory, updates pyproject.toml and imports
- CLI entry point (`pj-py init <name>`) for manual testing
- Error classes (`PjPyError`, `AuthError`) for clean programmatic consumption
