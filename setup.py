import os
import sys

import setuptools
import toml
from setuptools import setup

VERSION_NAME = "MPYL_VERSION"
version = os.environ.get(VERSION_NAME, None)

if not version:
    print(f"Version needs to be specified via {VERSION_NAME} environment variable")
    sys.exit(1)

with open("README.md", "r", encoding="utf-8") as readme_file:
    readme = readme_file.read()


def get_install_requirements():
    try:
        with open("Pipfile", "r", encoding="utf-8") as fh:
            pipfile = fh.read()
        pipfile_toml = toml.loads(pipfile)
    except FileNotFoundError:
        return []
    try:
        required_packages = pipfile_toml["packages"].items()
    except KeyError:
        return []
    return [
        "{0}{1}".format(pkg, ver) if ver != "*" else pkg
        for pkg, ver in required_packages
    ]


setup(
    name="mpyl",
    version=version,
    description="Modular Pipeline Library",
    author="Vandebron Energie BV",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://vandebron.github.io/mpyl",
    entry_points={"console_scripts": ["mpyl=mpyl:main"]},
    project_urls={
        "Documentation": "https://vandebron.github.io/mpyl",
        "Source": "https://github.com/Vandebron/mpyl",
        "Tracker": "https://github.com/Vandebron/mpyl/issues",
    },
    classifiers=[
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
    ],
    install_requires=get_install_requirements(),
    package_dir={"": "src"},
    include_package_data=True,
    packages=setuptools.find_packages(where="./src"),
    python_requires=">= 3.9",
    package_data={"mpyl": ["py.typed"]},
)
