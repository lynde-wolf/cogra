# Contributing to cogra

Thank you for helping. Questions, bugs and ideas are welcome as
[issues](https://github.com/lynde-wolf/cogra/issues). For a new style, wear
look or paper layout, please open an issue to talk it over before you start a
pull request.

## Setting up

cogra uses [uv](https://docs.astral.sh/uv/) for its environment.

```bash
uv sync --extra dev          # creates .venv from uv.lock, with the test and lint tools
uv run pre-commit install    # ruff and a secret scan run on every commit
```

## Before a pull request

```bash
uv run ruff check src tests examples      # lint
uv run ruff format src tests examples     # format
uv run mypy                               # type check the package
uv run pytest --cov                       # tests, with coverage
```

CI runs the same four steps on Python 3.10 (with the oldest supported
matplotlib), 3.12 and 3.13.

- **Tests first for bugs.** Add a test that fails without your fix.
- **Public functions** have type hints and a docstring that says what each
  argument means and what comes back. Keep docstrings true to the code.
- **Invalid input raises.** A function given an impossible value (a p of 1.7,
  a missing file) raises a `ValueError` or `FileNotFoundError` with a message
  that names the value. It does not return a plausible-looking result.
- **Randomness is seeded.** Anything random takes a `seed=` and gives the
  same output for the same seed.
- **Changes** go in `CHANGES.md`, under the unreleased version.
- **Documentation.** The site is built from the repository's own files
  (`uv run python docs/build.py`, then `python3 -m http.server --directory
  docs/_site`): the tutorial from `TUTORIAL.md`, the API page from
  docstrings, the gallery from `examples/gallery.py`. A new public function
  must be added to a group in `_api_groups()` in `docs/build.py`; the build
  stops if one is missing. GitHub Pages publishes it on every push to `main`.
- **Pictures.** If you change how something looks, rerun
  `uv run python examples/readme_figures.py` and include the new figures.

## Releasing (maintainer)

1. Update `version` in `pyproject.toml` and `CITATION.cff` ([semantic
   versioning](https://semver.org): patch for fixes, minor for new features,
   major for breaking changes) and date the entry in `CHANGES.md`.
2. `uv lock`, commit, and make a GitHub release tagged `v<version>`. Zenodo
   archives each release and gives it a DOI once the repository is switched
   on at zenodo.org.
3. `uv build` and `uv publish` to put it on PyPI.
