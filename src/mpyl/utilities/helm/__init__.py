"""
Helper methods for helm deployments
"""


def convert_to_helm_release_name(name: str, tag: str) -> str:
    """
    Converts all _ and . into -, lowercases the name to adhere to helm's naming conventions
    and appends a tag

    For more information check: https://helm.sh/docs/chart_best_practices/conventions/
    """
    return _clean_release_name(f"{name}{tag}")


def _clean_release_name(name: str):
    return name.replace("_", "-").replace(".", "-").lower()


def shorten_name(name: str) -> str:
    """
    Condenses a name to the first letter of each segment to respect a 63 character limit
    that is sometimes exceeded
    """
    shortened_name = "".join([n[0] for n in _clean_release_name(name).split("-")])
    return shortened_name
