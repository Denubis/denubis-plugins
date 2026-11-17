# Fixture instructions

- Planning only; do not edit implementation files.
- Use `python -m unittest discover -s tests -p '*_tests.py' -q` as the project test command.
- Keep tests and documentation with the behavior they establish.
- Every user-visible change adds one line under `## Unreleased` in `CHANGELOG.md`.
- Implementation is carried out by a coordinating session that can delegate work to
  subagents.
- Do not commit during planning.
