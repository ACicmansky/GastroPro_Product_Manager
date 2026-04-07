"""Output column definitions — generated, not hardcoded.

The e-shop format is conventionally referred to as "138-column" but the
actual generated count is 329 = 29 base + 150 image + 150 imageDesc.
"""


# Base (non-image) columns in the e-shop output format.
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

    Returns 329 columns: 29 base + image,image2..image150 + imageDesc,imageDesc2..imageDesc150.
    First image slot is "image" (not "image1") to match the e-shop convention.
    """
    images = ["image"] + [f"image{i}" for i in range(2, IMAGE_SLOT_COUNT + 1)]
    image_descs = ["imageDesc"] + [f"imageDesc{i}" for i in range(2, IMAGE_SLOT_COUNT + 1)]
    return BASE_COLUMNS + images + image_descs
