"""
Helper methods for helm deployments
"""


def convert_name_to_helm_release_name(name: str, tag: str) -> str:
    """
    Converts all _ and . into -, lowercases the name and returns the first letter of each bit
    for a short helm release name to respect the 63 character limit
    """
    name = "".join(
        [n[0] for n in name.replace("_", "-").replace(".", "-").lower().split("-")]
    )
    tag = tag.replace("_", "-").lower()
    return f"{name}{tag}"
