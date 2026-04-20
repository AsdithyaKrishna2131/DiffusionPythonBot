import os
import sys
import tomlkit


def _get_project_meta():
    pyproject_path = os.path.join(
        (os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.argv[0])))))),
        "pyproject.toml",
    )
    with open(pyproject_path) as pyproject:
        file_contents = pyproject.read()

    return tomlkit.parse(file_contents)["tool"]["poetry"]
