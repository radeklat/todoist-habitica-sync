from invoke import task

from tasks.format import run_format
from tasks.lint import lint
from tasks.test import test
from tasks.typecheck import typecheck


@task(post=[run_format, lint, typecheck, test])
def verify_all(_ctx):
    """Run the 'format', 'lint', 'test-all' and 'typecheck' targets."""
