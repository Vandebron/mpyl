from setuptools import setup, find_packages
import toml

with open("README.md", "r") as readme_file:
    readme = readme_file.read()


def get_install_requirements():
    try:
        with open('Pipfile', 'r') as fh:
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
    name="pympl",
    version="0.0.2",
    description="A python rewrite of mpl-modules",
    long_description=readme,
    long_description_content_type="text/markdown",
    install_requires=get_install_requirements(),
    packages=['pympl']
)
