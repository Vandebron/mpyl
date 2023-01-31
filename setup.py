import setuptools
from setuptools import setup
import toml

with open("README.md", "r", encoding='utf-8') as readme_file:
    readme = readme_file.read()


def get_install_requirements():
    try:
        with open('Pipfile', 'r', encoding='utf-8') as fh:
            pipfile = fh.read()
        pipfile_toml = toml.loads(pipfile)
    except FileNotFoundError:
        return []
    try:
        required_packages = pipfile_toml['packages'].items()
    except KeyError:
        return []
    return ["{0}{1}".format(pkg, ver) if ver != "*"
            else pkg for pkg, ver in required_packages]


setup(
    name="mpyl",
    version="0.0.1",
    description="Modular Pipeline Library",
    long_description=readme,
    long_description_content_type="text/markdown",
    install_requires=get_install_requirements(),
    package_dir={'': 'src'},
    include_package_data=True,
    packages=setuptools.find_packages(where="./src")
)
