"""Commands related to build"""
import click


@click.group('build')
def build():
    """Commands related to building"""


@build.command()
def status():
    click.echo('build status')


@build.command()
def run():
    click.echo('build run')


if __name__ == '__main__':
    build()
