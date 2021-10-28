"""Linting checks on source code."""

import os
from typing import List

from invoke import task
from termcolor import cprint

from tasks.utils import PROJECT_INFO, ensure_reports_dir, format_messages, print_header, read_contents

PYLINT_CONFIG_SOURCE_FPATH = ".pylintrc"
PYLINT_CONFIG_TESTS_FPATH = PROJECT_INFO.tests_directory / ".pylintrc"

REPORT_PYDOCSTYLE_FPATH = PROJECT_INFO.reports_directory / "pydocstyle-report.log"
REPORT_PYCODESTYLE_FPATH = PROJECT_INFO.reports_directory / "pycodestyle-report.log"
REPORT_PYLINT_SOURCE_FPATH = PROJECT_INFO.reports_directory / "pylint-report.log"
REPORT_PYLINT_TESTS_FPATH = PROJECT_INFO.reports_directory / "pylint-report-tests.log"


@task(name="lint-docstyle")
def lint_pydocstyle(ctx):
    """
    Run docstring linting on source code.
    Docstring linting is done via pydocstyle. The pydocstyle config can be found in the `.pydocstyle` file.
    This ensures compliance with PEP 257, with a few exceptions. Note that pylint also carries out additional
    docstyle checks.
    """
    print_header("documentation style", level=2)
    ensure_reports_dir()
    try:
        ctx.run(f"pydocstyle {PROJECT_INFO.source_directory} > {REPORT_PYDOCSTYLE_FPATH}")
    finally:
        if os.path.exists(REPORT_PYDOCSTYLE_FPATH):
            format_messages(read_contents(REPORT_PYDOCSTYLE_FPATH))


@task(name="lint-pycodestyle")
def lint_pycodestyle(ctx):
    """
    Run PEP8 checking on code; this includes primary code (source) and secondary code (tests, tasks, etc.).
    PEP8 checking is done via pycodestyle.
    """
    # Why pycodestyle and pylint? So far, pylint does not check against every convention in PEP8. As pylint's
    # functionality grows, we should move all PEP8 checking to pylint and remove pycodestyle
    print_header("code style (PEP8)", level=2)

    ensure_reports_dir()

    dirs = f"{PROJECT_INFO.source_directory} {PROJECT_INFO.tests_directory} {PROJECT_INFO.tasks_directory}"
    try:
        ctx.run(
            f"pycodestyle --ignore=E501,W503,E231,E203,E402 "
            "--exclude=.svn,CVS,.bzr,.hg,.git,__pycache__,.tox,*_config_parser.py "
            f"{dirs} > {REPORT_PYCODESTYLE_FPATH}"
        )
        # Ignores explained:
        # - E501: Line length is checked by PyLint
        # - W503: Disable checking of "Line break before binary operator". PEP8 recently (~2019) switched to
        #         "line break before the operator" style, so we should permit this usage.
        # - E231: "missing whitespace after ','" is a false positive. Handled by black formatter.
    finally:
        if os.path.exists(REPORT_PYCODESTYLE_FPATH):
            format_messages(read_contents(REPORT_PYCODESTYLE_FPATH))


def run_pylint(ctx, source_dirs: List[str], report_path: str, pylintrc_fpath: str):
    """Run pylint with a given configuration on a given code tree and output to a given report file."""
    print_header(", ".join(map(str, source_dirs)), level=3)
    ensure_reports_dir()

    command = f"pylint --rcfile {pylintrc_fpath} {' '.join(map(str, source_dirs))} > {report_path}"
    try:
        ctx.run(command)
    except Exception as runtime_error:  # pylint: disable=broad-except
        if os.path.exists(report_path):
            print(read_contents(report_path))
        raise runtime_error
    else:
        cprint("✔ No issues found.", "green")


@task(name="lint-pylint")
def lint_pylint(ctx):
    """
    Run pylint on code; this includes primary code (source) and secondary code (tests, tasks, etc.).
    The bulk of our code conventions are enforced via pylint. The pylint config can be found in the `.pylintrc` file.
    """
    print_header("pylint", level=2)

    run_pylint(
        ctx, [PROJECT_INFO.source_directory], REPORT_PYLINT_SOURCE_FPATH, PYLINT_CONFIG_SOURCE_FPATH,
    )
    run_pylint(
        ctx,
        [PROJECT_INFO.tests_directory, PROJECT_INFO.tasks_directory],
        REPORT_PYLINT_TESTS_FPATH,
        PYLINT_CONFIG_TESTS_FPATH,
    )


@task(post=[lint_pylint, lint_pycodestyle, lint_pydocstyle])
def lint(_ctx):
    """Run linting on the entire code base (source code, tasks, tests)."""
    print_header("Linting", icon="🔎")
