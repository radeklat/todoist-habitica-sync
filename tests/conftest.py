from pathlib import Path

import pytest
import toml
from delfino.constants import PYPROJECT_TOML_FILENAME
from delfino.models import PyprojectToml


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def pyproject_toml(project_root):
    return PyprojectToml(**toml.load(project_root / PYPROJECT_TOML_FILENAME))


@pytest.fixture(scope="session")
def poetry(pyproject_toml):
    assert pyproject_toml.tool.poetry
    return pyproject_toml.tool.poetry
