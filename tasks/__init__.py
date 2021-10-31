"""
Runnable tasks for this project. Project tooling for build, distribute, etc.

Invoked with the Python `invoke` framework. Tasks should be invoked from the project root directory, not
the `tasks` dir.

Task code is for tooling only and should strictly not be mixed with `src` code.
"""

from invoke import Collection

from tasks.docker_build import docker_build
from tasks.format import run_format
from tasks.lint import lint, lint_pycodestyle, lint_pydocstyle, lint_pylint
from tasks.test import coverage_open, coverage_report, test, test_integration, test_unit
from tasks.typecheck import typecheck
from tasks.upload import upload
from tasks.utils import switch_python_version
from tasks.verify_all import verify_all

namespace = Collection()  # pylint: disable=invalid-name

namespace.add_task(run_format)
namespace.add_task(typecheck)

namespace.add_task(lint)
namespace.add_task(lint_pylint)
namespace.add_task(lint_pycodestyle)
namespace.add_task(lint_pydocstyle)

namespace.add_task(test_unit)
namespace.add_task(test_integration)
namespace.add_task(test)
namespace.add_task(coverage_report)
namespace.add_task(coverage_open)

namespace.add_task(verify_all)

namespace.add_task(upload)
namespace.add_task(switch_python_version)

namespace.add_task(docker_build)
