"""ru_lint — deterministic regex linter for Russian text edited by the ru-editor skill.

Phase 2 (v2.4.0) of the ru-editor overhaul. Pure Python 3.11+, no third-party deps.

Public surface (built incrementally — each task adds one piece):
  - Document        : named views over a markdown source string
  - Finding         : single lint result
  - register / REGISTRY : check-function registry decorator + dict
  - main()          : CLI entry point

CLI:
  python ru_lint.py check <edited.md>
  python ru_lint.py diff  <orig.md> <edited.md>
  python ru_lint.py both  <orig.md> <edited.md>     (default semantics)

Add --format=json for machine output (schema_version "1.0"). Default is human.
Exit code: 0 if no HARD_FAIL findings; 1 otherwise. Use --strict to also fail on WARN.
"""

__version__ = "0.1.0"
SCHEMA_VERSION = "1.0"
