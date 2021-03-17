"""Tests on source code."""

import re
import shutil
import webbrowser
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from invoke import Exit, task
from termcolor import cprint

from tasks.utils import PROJECT_INFO, ensure_reports_dir, print_header

_COVERAGE_DAT_COMBINED = PROJECT_INFO.reports_directory / "coverage.dat"
_COVERAGE_HTML = PROJECT_INFO.reports_directory / "coverage-report/"


@dataclass(frozen=True)
class TestConfiguration:
    """Configuration for a particular suite of tests; e.g., integration vs unit."""

    name: str
    tests_directory: Path

    @property
    def coverage_dat(self) -> Path:
        return PROJECT_INFO.reports_directory / f"coverage-{self.name}.dat"

    @property
    def coverage_xml(self) -> Path:
        return PROJECT_INFO.reports_directory / f"coverage-{self.name}.xml"

    @property
    def exports(self) -> str:
        """Return exports (of env vars) that should be present when executing tests."""
        return f'export COVERAGE_FILE="{self.coverage_dat}"'


class TestType(Enum):
    INTEGRATION = TestConfiguration("integration", PROJECT_INFO.integration_tests_directory)
    UNIT = TestConfiguration("unit", PROJECT_INFO.unit_tests_directory)


def _run_tests(ctx, test_type: TestType, maxfail=0, debug=False):
    """Execute the tests for a given test type."""
    print_header(f"️Running {test_type.value.name} tests️", icon="🔎🐛")
    ensure_reports_dir()
    params: TestConfiguration = test_type.value
    debug = "-s" if debug else ""
    ctx.run(
        f"""
        {params.exports}
        pytest \
            --cov={PROJECT_INFO.source_directory} \
            --cov-report="xml:{params.coverage_xml}" \
            --cov-branch -vv --maxfail={int(maxfail)} {debug}\
            {params.tests_directory}
        """,
        pty=True,
    )


@task(name="test-unit", optional=["maxfail"])
def test_unit(ctx, maxfail=0, debug=False):
    """Run unit tests.

    The `--debug` flag disables capture, allowing debuggers like `pdb` to be used.
    """
    _run_tests(ctx, TestType.UNIT, maxfail=maxfail, debug=debug)


@task(name="test-integration", optional=["maxfail"])
def test_integration(ctx, maxfail=0, debug=False):
    """Run unit tests.

    The `--debug` flag disables capture, allowing debuggers like `pdb` to be used.
    """
    _run_tests(ctx, TestType.INTEGRATION, maxfail=maxfail, debug=debug)


def get_total_coverage(ctx, coverage_dat: Path) -> str:
    """Return coverage percentage, as captured in coverage dat file; e.g., returns "100%"."""
    output = ctx.run(
        f"""
        export COVERAGE_FILE="{coverage_dat}"
        coverage report""",
        hide=True,
    ).stdout
    match = re.search(r"TOTAL.*?([\d.]+%)", output)
    if match is None:
        raise RuntimeError(f"Regex failed on output: {output}")
    return match.group(1)


@task(name="coverage-report")
def coverage_report(ctx):
    """Analyse coverage and generate a report to term and HTML; from combined unit and integration tests."""
    print_header("Generating coverage report", icon="📃")
    ensure_reports_dir()

    coverage_files = []  # we'll make a copy because `combine` will erase them
    for test_enum in TestType.__members__.values():
        tests_config: TestConfiguration = test_enum.value
        if not tests_config.coverage_dat.exists():
            cprint(
                f"Could not find coverage dat file for {tests_config.name} tests: {tests_config.coverage_dat}",
                "yellow",
            )
        else:
            print(f"{tests_config.name.title()} test coverage: {get_total_coverage(ctx, tests_config.coverage_dat)}")

            temp_copy = tests_config.coverage_dat.with_name(tests_config.coverage_dat.name.replace(".dat", "-copy.dat"))
            shutil.copy(tests_config.coverage_dat, temp_copy)
            coverage_files.append(str(temp_copy))

    ctx.run(
        f"""
            export COVERAGE_FILE="{_COVERAGE_DAT_COMBINED}"
            coverage combine {" ".join(coverage_files)}
            coverage html -d {_COVERAGE_HTML}
        """
    )
    print(f"Total coverage: {get_total_coverage(ctx, _COVERAGE_DAT_COMBINED)}\n")
    print(
        f"Refer to coverage report for full analysis in '{_COVERAGE_HTML}/index.html'\n"
        f"Or open the report in your default browser with:\n"
        f"  pipenv run inv coverage-open"
    )


@task(pre=[test_unit, test_integration, coverage_report], name="test-all")
def test(_ctx):
    """Run all tests, and generate coverage report."""


@task(name="coverage-open")
def coverage_open(_ctx):
    """Open coverage results in default browser."""
    report_index = _COVERAGE_HTML / "index.html"
    if not report_index.exists():
        raise Exit(
            f"Could not find coverage report '{report_index}'. Ensure that the report has been built.\n"
            "Try one of the following:\n"
            f"  pipenv run inv {coverage_report.name}\n"
            f"or\n"
            f"  pipenv run inv {test.name}",
            1,
        )
    webbrowser.open(f"file:///{report_index.absolute()}")
