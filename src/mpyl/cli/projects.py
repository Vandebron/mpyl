"""Commands related to projects and how they relate"""
import click


@click.group('projects')
def projects():
    """Commands related to projects"""


@projects.command(name='list')
def list_projects():
    click.echo('projects list')


@projects.command()
def lint():
    click.echo('projects list')


if __name__ == '__main__':
    projects()
