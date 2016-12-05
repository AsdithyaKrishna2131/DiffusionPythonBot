import os
import sys
import tomlkit


def _get_project_meta():
    pyproject_path = os.path.join(
