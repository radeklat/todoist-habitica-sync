from invoke import Result, UnexpectedExit, task
from termcolor import cprint

from tasks.utils import PROJECT_INFO, ensure_pre_commit, print_header


def _check_result(result: Result, check: bool, msg: str):
    if result.return_code == 1 and check:
        cprint(
            f"{msg} before commit. Try following:\n"
            f" * Enable pre-commit hook by running `pre-commit install` in the repository.\n"
            f" * Run formatter manually with `pipenv run inv format` before committing code.",
            color="red",
        )
        raise UnexpectedExit(result)

    if result.return_code > 1:
        raise UnexpectedExit(result)


@task(name="format", pre=[ensure_pre_commit])
def run_format(ctx, check=False, quiet=False):
    """Run black code formatter on source code.

    Args:
        ctx (invoke.Context): Invoke context.
        check (bool): Only check formatting, don't reformat the code.
        quiet (bool): Don't show progress. Only errors.
    """
    dirs = f"{PROJECT_INFO.source_directory} {PROJECT_INFO.tests_directory} {PROJECT_INFO.tasks_directory}"
    flags = []

    if check:
        flags.append("--check")

    print_header("Sorting imports", icon="ℹ")

    _check_result(
        ctx.run(f"isort {dirs} " + " ".join(flags), pty=True, warn=True),
        check,
        "Import were not sorted",
    )

    print_header("Formatting code", icon="🖤")

    if quiet:
        flags.append("--quiet")

    _check_result(
        ctx.run(f"black {dirs} " + " ".join(flags), pty=True, warn=True),
        check,
        "Code was not formatted",
    )
