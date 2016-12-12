import os
import sys
import tomlkit


def _get_project_meta():
    pyproject_path = os.path.join(
        (os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.argv[0])))))),
