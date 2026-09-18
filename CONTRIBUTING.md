# Contributing

devprep's default is a complete curated workstation. Keep custom setup explicit and easy to automate. Prefer a useful common default over many overlapping alternatives.

## Structure

- `catalog.json`: tools, categories, native package names, dependencies, platform restrictions, and activation notes.
- `platforms.py`: host identification and supported family routing.
- `managers.py`: package-manager argument vectors and return-code interpretation.
- `planner.py`: a serializable plan shared by previews and execution.
- `recipes.py`: isolated Python environments and verified upstream fallbacks.
- `runner.py`: privilege boundaries, execution, dependency failures, and reports.
- `cli.py`: full/custom selection and confirmation.
- `install.sh` / `install.ps1`: minimal prerequisite bootstrap and argument forwarding.

The CLI has no runtime dependencies outside Python's standard library. Native installers are executed with argument arrays, never a shell. Keep network requests, privilege escalation, and mutations out of planning. `--dry-run`, `--json`, `--list`, and help must never bootstrap or install software.

## Validation

Run `python -m unittest discover -s tests -v`, `sh -n install.sh`, and preview any changed platform with `python -m devprep --manager NAME --json`. For a new package mapping, verify the exact ID against the publisher or native repository, then test installation and rerun behavior in a disposable machine/container. A passing unit test is not proof of native package availability.

Add targeted regression tests for selection bugs, platform routing, privilege handling, failure reporting, and downloaded archive handling. Do not install the full catalog onto the machine used to develop devprep. Check installer failures, interrupted runs, and recovery as well as a successful install.

Keep the README and `docs/catalog.md` synchronized with the catalog. For new distro families, implement identity routing, bootstrap, manager commands, package mappings, and an appropriate CI smoke job together. Explicitly document architecture, repository, or immutable-host limitations.
