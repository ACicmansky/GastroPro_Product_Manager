"""Product variant logic — pair code extraction."""

VALID_SUFFIXES = {"BAR", "DINING", "COFFEE"}


def get_pair_code(code) -> str:
    """Extract pair code by removing variant suffix.

    Products with suffixes like 'BAR', 'DINING', 'COFFEE' are variants
    of a base product. This returns the base code without the suffix.

    Returns empty string if code has no valid variant suffix.
    """
    code_str = str(code).strip() if code is not None else ""
    if not code_str:
        return ""

    parts = code_str.split()
    if len(parts) > 1 and parts[-1] in VALID_SUFFIXES:
        return " ".join(parts[:-1])
    return ""
