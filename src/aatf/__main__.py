"""Entrypoint stub for ``python -m aatf`` (and ``make run``).

The experiment loop is delivered by later features. This stub reserves the one-command run
surface (FR-009) and exits cleanly with an explicit not-yet-implemented signal.
"""

import sys


def main() -> int:
    print(
        "Adaptive Adversarial Testing Framework — scaffold only.\n"
        "The experiment loop is not yet implemented. "
        "See docs/backlog.md for the upcoming features."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
