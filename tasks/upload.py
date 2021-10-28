"""Type checking on source code."""
import os

from invoke import task
from termcolor import cprint

from tasks.utils import print_header


@task()
def upload(ctx):
    print_header("Uploading library to pypi", icon="⬆")

    pypi_api_token = os.getenv("PYPI_API_TOKEN")
    if not pypi_api_token:
        cprint(
            "PYPI_API_TOKEN environment variable to authenticate with PyPI is not set.", color="red",
        )
        raise RuntimeError()

    if not pypi_api_token.startswith("pypi-"):
        pypi_api_token = f"pypi-{pypi_api_token}"

    ctx.run(
        "twine upload --skip-existing --non-interactive dist/*",
        pty=True,
        # See https://pypi.org/help/#apitoken
        env={"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": pypi_api_token},
    )
