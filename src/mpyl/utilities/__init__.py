"""Common utility functions"""

from typing import Optional

from ..constants import PR_NUMBER_PLACEHOLDER


def replace_pr_number(original_value: Optional[str], pr_number: Optional[int]):
    return (
        original_value.replace(PR_NUMBER_PLACEHOLDER, str(pr_number))
        if original_value and pr_number
        else original_value
    )
