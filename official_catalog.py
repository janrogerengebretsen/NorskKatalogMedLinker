import os

from consultant_registry import _request, is_configured


CATALOG_SYNC_TOKEN = os.environ.get("CATALOG_SYNC_TOKEN", "")
CATALOG_SYNC_KEY = "official_products"
CATALOG_REFRESH_SECONDS = int(os.environ.get("CATALOG_REFRESH_SECONDS", "900"))


def archive_is_configured():
    return is_configured()


def sync_is_configured():
    return archive_is_configured() and bool(CATALOG_SYNC_TOKEN)


def sync_official_products(products):
    if not sync_is_configured():
        return None
    payload = []
    for product in products:
        payload.append(
            {
                "id": product.get("id"),
                "handle": product.get("handle"),
                "articleNumber": product.get("articleNumber"),
                "title": product.get("title"),
                "description": product.get("description"),
                "price": product.get("price"),
                "compareAtPrice": product.get("compareAtPrice"),
                "available": product.get("available"),
                "image": product.get("image"),
                "images": product.get("images") or [],
                "series": product.get("series"),
                "tags": product.get("tags") or [],
                "url": product.get("url"),
                "publishedAt": product.get("publishedAt"),
                "createdAt": product.get("createdAt"),
                "sourceUpdatedAt": product.get("sourceUpdatedAt"),
            }
        )
    return _request(
        "rpc/sync_official_product_catalog",
        method="POST",
        payload={
            "p_sync_token": CATALOG_SYNC_TOKEN,
            "p_products": payload,
        },
    )


def begin_official_catalog_sync():
    if not sync_is_configured():
        return {"should_sync": False, "status": "not_configured"}
    rows = _request(
        "rpc/begin_catalog_sync",
        method="POST",
        payload={
            "p_sync_token": CATALOG_SYNC_TOKEN,
            "p_key": CATALOG_SYNC_KEY,
            "p_min_age_seconds": CATALOG_REFRESH_SECONDS,
        },
    )
    return rows[0] if rows else {"should_sync": False}


def finish_official_catalog_sync(
    status,
    source_url,
    http_status=None,
    duration_ms=None,
    error_message=None,
    products_found=None,
    details=None,
):
    if not sync_is_configured():
        return None
    return _request(
        "rpc/finish_catalog_sync",
        method="POST",
        payload={
            "p_sync_token": CATALOG_SYNC_TOKEN,
            "p_key": CATALOG_SYNC_KEY,
            "p_source_url": source_url,
            "p_status": status,
            "p_http_status": http_status,
            "p_duration_ms": duration_ms,
            "p_error_message": error_message,
            "p_products_found": products_found,
            "p_details": details or {},
        },
    )


def list_official_product_archive():
    if not archive_is_configured():
        return []
    return _request(
        "official_products",
        {
            "select": (
                "shopify_product_id,handle,article_number,title,description,"
                "price_nok,compare_at_price_nok,available,image_url,images,"
                "series,tags,source_url,in_official_catalog,last_seen_at,removed_at"
                ",first_seen_at,title_no,description_no,translation_source_language,"
                "translation_source_title,translation_source_description,translated_at"
            ),
            "order": "in_official_catalog.desc,title.asc",
            "limit": "2000",
        },
    )


def save_official_product_translation(
    handle,
    source_title,
    source_description,
    title_no,
    description_no,
    source_language,
):
    if not sync_is_configured():
        return False
    return bool(
        _request(
            "rpc/save_official_product_translation",
            method="POST",
            payload={
                "p_sync_token": CATALOG_SYNC_TOKEN,
                "p_handle": handle,
                "p_source_title": source_title,
                "p_source_description": source_description,
                "p_title_no": title_no,
                "p_description_no": description_no,
                "p_source_language": source_language,
            },
        )
    )
