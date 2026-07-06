import logging
from collections.abc import Callable
from typing import Any

from app.config import get_settings
from app.job_repository import delete_uploaded_image_metadata, list_expired_uploaded_images
from app.object_storage import delete_research_image

logger = logging.getLogger(__name__)

DeleteImageFn = Callable[[str], None]


async def cleanup_expired_uploaded_images(
    *,
    limit: int | None = None,
    delete_image: DeleteImageFn = delete_research_image,
) -> dict[str, Any]:
    settings = get_settings()
    batch_limit = limit or settings.image_cleanup_batch_size
    expired_images = await list_expired_uploaded_images(batch_limit)

    deleted_objects = 0
    deleted_metadata = 0
    failed = 0

    for image in expired_images:
        object_key = str(image["object_key"])
        try:
            delete_image(object_key)
        except Exception:
            failed += 1
            logger.warning("Expired image object cleanup failed for metadata row %s", image["id"], exc_info=True)
            continue

        deleted_objects += 1
        if await delete_uploaded_image_metadata(str(image["id"])):
            deleted_metadata += 1

    return {
        "scanned": len(expired_images),
        "deletedObjects": deleted_objects,
        "deletedMetadata": deleted_metadata,
        "failed": failed,
    }
