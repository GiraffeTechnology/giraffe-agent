# Contributing to Giraffe Agent

Thank you for your interest in contributing to Giraffe Agent.

## Project Status

This repository is the **v0.1.0-mvp** developer preview — an MVP baseline and
reference implementation. It is **not** production-ready. Contributions that
improve correctness, test coverage, documentation, and code clarity are
especially welcome.

## How to Contribute

### Reporting Issues

- Use GitHub Issues to report bugs, unexpected behavior, or documentation gaps.
- Include: Python version, OS, steps to reproduce, expected vs. actual behavior.
- For security issues, see `SECURITY.md` instead.

### Submitting Pull Requests

1. **Fork** the repository and create a feature branch.
2. **Write tests** — new features should come with pytest tests in `apps/bside/tests/`
   or `apps/mside/tests/` as appropriate.
3. **Run the test suite** before submitting:
   ```bash
   # From repo root
   pytest apps/bside/tests/ -q
   python apps/bside/run_tests.py
   pytest apps/mside/tests/ -q
   ```
4. **Keep PRs focused** — one logical change per PR.
5. **Follow the code style** — deterministic parsing, no LLM calls in core
   business logic, Pydantic v2 models for all data structures.

### Architecture Guidelines

- **No LLM in core logic** — the MVP uses deterministic regex parsing. LLM
  integration is planned for v0.2.0 but must be an optional, swappable layer.
- **B↔M contract** — changes to the B+M bridge must preserve the contract
  defined in `docs/BM_CONTRACT.md`.
- **JSON file storage** — the MVP uses flat JSON files under `data/`. Database
  migration will come in a later release.
- **Bilingual messages** — all supplier-facing messages must have both EN and ZH
  variants.

### Known Issue (help wanted)

> M-side unknown supplier dispatch currently returns HTTP 200 with `ok=true`
> and `dispatched=0`. It should return 404/422 or explicit `partial_success`
> with `missing_supplier_ids`.

See `docs/ROADMAP.md` for the full list of known issues and planned features.

## Code of Conduct

Be respectful, constructive, and collaborative. We follow the
[Contributor Covenant](https://www.contributor-covenant.org/) v2.1.

## License

By contributing, you agree that your contributions will be licensed under the
same Apache 2.0 license as the rest of the project. See `LICENSE` for details.
