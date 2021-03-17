"""Type checking on source code."""

from invoke import Result, task
from termcolor import cprint

from tasks.utils import PROJECT_INFO, ensure_reports_dir, print_header

_REPORTS_DIR = PROJECT_INFO.reports_directory / "typecheck/junit.xml"


def _handle_unexpected_pass(expected_to_fail: bool, result: Result, path: str):
    if expected_to_fail and not result.failed:
        result.exited = 1  # force failure
        cprint(
            f"\nThis folder was expected to fail but no errors were found.\n\nPlease edit the "
            f"'{__file__}' file and move '{path}' from `broken_directories` to `fixed_directories`.",
            "red",
            attrs=["bold"],
        )


@task()
def typecheck(ctx, summary_only=False):
    """
    Run type checking on source code.
    A non-zero return code from this task indicates invalid types were discovered.

    Args:
        ctx (invoke.Context): Invoke context.
        summary_only (bool): Suppress error messages and show only summary error count.
    """
    print_header("RUNNING TYPE CHECKER")

    tail = " | tail -n 1" if summary_only else ""

    ensure_reports_dir()

    ctx.run(
        f"set -o pipefail; "
        f'export MYPYPATH="$MYPYPATH:{PROJECT_INFO.source_directory}"; '
        f"mypy --show-column-numbers --show-error-codes --color-output --warn-unused-config --warn-unused-ignores "
        f"--follow-imports silent "
        f"--junit-xml {_REPORTS_DIR} "
        f"{PROJECT_INFO.source_directory} {PROJECT_INFO.tests_directory} {PROJECT_INFO.tasks_directory}"
        f"{tail}",
        pty=True,
    )
