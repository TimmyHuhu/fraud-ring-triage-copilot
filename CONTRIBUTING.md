# Contributing to Fraud Ring Triage Copilot

Thanks for your interest in improving the project! Contributions of all kinds are
welcome — bug reports, feature ideas, documentation, and code.

## Getting started

1. Fork and clone the repository.
2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. Run the test suite to confirm your environment is set up:

   ```bash
   pytest
   ```

4. Run the dashboard locally:

   ```bash
   python -m streamlit run app.py
   ```

## Making changes

- Create a feature branch off `main`.
- Keep each agent focused on a single responsibility (see `agents/`).
- **Add or update tests** under `tests/` for any behavior you change. CI runs
  `pytest` on Python 3.10–3.12 and must pass before a PR can be merged.
- Keep commits small and write clear, imperative commit messages
  (e.g. `Add entity resolution to risk ranker`).

## Reporting bugs and requesting features

Please open an issue using the templates under
[`.github/ISSUE_TEMPLATE`](.github/ISSUE_TEMPLATE). Include reproduction steps
and a small sample dataset where relevant (with no real or sensitive data).

## Code of conduct

Be respectful and constructive. This is a learning-focused project; assume good
intent and help others learn.
