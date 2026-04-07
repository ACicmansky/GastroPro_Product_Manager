"""Output column definitions — generated, not hardcoded."""


# Base columns in the 138-column output format.
# These are the non-image, non-repeating columns.
BASE_COLUMNS = [
    "code", "name", "pairCode", "defaultCategory", "categoryText",
    "shortDescription", "description", "price", "standardPrice",
    "availability", "manufacturer", "warranty", "ean",
    "weight", "unit", "seoTitle", "metaDescription",
    "internalNote", "visibility", "actionPrice", "actionPriceFrom",
    "actionPriceTo", "stock", "minimalAmount", "source",
    "aiProcessed", "aiProcessedDate", "newCategory",
    "variantVisibility",
]

# Number of image slots in the output format
IMAGE_SLOT_COUNT = 150


def get_output_columns() -> list:
    """Generate the full list of output columns.

    Returns ~338 columns: base + image1..150 + imageDesc1..150
    """
    images = [f"image{i}" for i in range(1, IMAGE_SLOT_COUNT + 1)]
    image_descs = [f"imageDesc{i}" for i in range(1, IMAGE_SLOT_COUNT + 1)]
    return BASE_COLUMNS + images + image_descs
