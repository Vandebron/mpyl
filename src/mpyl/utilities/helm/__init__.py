"""
Helper methods for helm deployments
"""

from mpyl.project import Target
from mpyl.steps.models import RunProperties


def convert_to_helm_release_name(name: str, tag: str) -> str:
    """
    Converts all _ and . into -, lowercases the name to adhere to helm's naming conventions
    and appends a tag

    For more information check: https://helm.sh/docs/chart_best_practices/conventions/
    """
    return _clean_release_name(f"{name}{tag}")


def _clean_release_name(name: str):
    return name.replace("_", "-").replace(".", "-").lower()


def get_name_suffix(properties: RunProperties) -> str:
    """
    Returns a suffix for the helm release name based on the deploy_target
    """
    if properties.target == Target.PULL_REQUEST:
        return f"-{properties.versioning.identifier}"
    return ""


def shorten_name(name: str) -> str:
    """
    Shortens name by taking the first letter of each hyphened sequence
    """
    if len(name) <= 3:
        return name
    return "".join([word[0] for word in name.split("-")])
