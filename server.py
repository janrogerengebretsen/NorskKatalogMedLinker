from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
from html.parser import HTMLParser
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime

_local_env = Path(__file__).resolve().parent / ".env"
if _local_env.is_file():
    for _line in _local_env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip())

from consultant_registry import (
    consultant_product_access,
    consultant_shop_status,
    find_consultant as find_registered_consultant,
    is_configured as registry_is_configured,
    list_consultants as list_registered_consultants,
    list_own_inventory,
    public_config,
    submit_own_inventory_order,
)
from official_catalog import (
    list_official_product_archive,
    save_official_product_translation,
    sync_is_configured,
    sync_official_products,
)


APP_HOST = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
APP_PORT = int(os.environ.get("PORT", "8789"))
BASE_URL = "https://tupperware-eu.com"
SHOP_PATH = "/no"
CONSULTANT_REF = "LISBETHOVERBYE"
CONSULTANT_API_URL = "https://api-server-3.goaffpro.com/v1/sdk/affiliate"
CONSULTANT_SHOP = "tupp-shop.myshopify.com"
ROOT = Path(__file__).resolve().parent
NODE_EXE = shutil.which("node") or os.path.expanduser(
    r"~\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)
CACHE_TTL = 15 * 60
CACHE = {}
CACHE_LOCK = threading.Lock()

NORWEGIAN_PRODUCT_TITLES = {
    "set-voila\u2122-rectangulaire-3-l-et-ecumoire-ergo": (
        "Sett: Voil\u00e0 rektangul\u00e6rt glassfat 3 l med Ergo hullsleiv"
    ),
}

NORWEGIAN_PRODUCT_DESCRIPTIONS = {
    "set-voila\u2122-rectangulaire-3-l-et-ecumoire-ergo": (
        "Komplett sett med Voil\u00e0 rektangul\u00e6rt glassfat 3 l og Ergo hullsleiv. "
        "Glassformen kan brukes til tilberedning i stekeovn og mikrob\u00f8lgeovn, "
        "servering ved bordet og oppbevaring i kj\u00f8leskap eller fryser. "
        "Den ergonomiske hullsleiven gj\u00f8r det enkelt \u00e5 blande, servere og l\u00f8fte "
        "mat fra v\u00e6ske, og kan brukes sammen med slippbelegg."
    ),
}


NAVIGATION = [
    {
        "title": "Spesialtilbud",
        "handle": "special-sales",
        "children": [
            ("Tupperware-salg", "soldes-tupperware"),
            ("Ukens tilbud", "weekly-offer"),
        ],
    },
    {
        "title": "Oppbevaring",
        "handle": "conservation",
        "children": [
            ("Sek - Skap", "dry-storage"),
            ("Kjøleskap", "refregirator-storage"),
            ("Fryser", "freezer_storage"),
            ("Tupperware i glass", "tupperware-verre"),
        ],
    },
    {
        "title": "Forberedelse",
        "handle": "preparation",
        "children": [
            ("Bakverk", "baking"),
            ("Kjøkkenredskaper", "kitchen-utensils"),
            ("Boller", "bowls"),
            ("Kniver", "knives"),
            ("Robot", "kitchen-tools"),
            ("Silikonformer", "moule-silicone"),
        ],
    },
    {
        "title": "Steking og oppvarming",
        "handle": "cooking-and-reheatable",
        "children": [
            ("Mikrobølgeovn", "microwave"),
            ("Ovn", "oven"),
            ("Luftfrityrkoker", "air-fryer"),
            ("Panner, kasseroller og gryter", "poeles-casseroles-et-fetou"),
        ],
    },
    {
        "title": "Servering",
        "handle": "serving-and-entertaining",
        "children": [
            ("Skåler og fat", "plates-and-bowls"),
            ("Bestikk", "cultery"),
            ("Drikkevarer", "beverage"),
            ("Kopper", "mugs"),
        ],
    },
    {
        "title": "Ta med",
        "handle": "on-the-go",
        "children": [
            ("Lunsj og snacks", "lunch-and-snacks"),
            ("Termoflasker", "thermal-drinkware"),
            ("Flasker", "bottles"),
        ],
    },
    {
        "title": "Andre",
        "handle": "other",
        "children": [
            ("Hjem og vedlikehold", "home-and-care"),
            ("Barn og baby", "kids-and-toys"),
            ("Recycline-serien", "eco"),
            ("Multifunksjonell", "multi-usage"),
            ("Reservedeler", "pieces-detachees"),
        ],
    },
]


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = clean_text(data)
        if text:
            self.parts.append(text)


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def html_to_text(value):
    parser = TextParser()
    parser.feed(value or "")
    return clean_text(" ".join(parser.parts))


def search_key(value):
    value = unicodedata.normalize("NFKD", clean_text(value).lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def product_series(title):
    match = re.search(
        r"(?:^|\s[-\u2013\u2014]\s)(Collection\s+.+?)\s*$",
        clean_text(title),
        flags=re.IGNORECASE,
    )
    return clean_text(match.group(1)) if match else ""


def fetch_url(url, timeout=35):
    if sys.platform.startswith("win") and url.startswith("https://"):
        return fetch_url_node(url, timeout)
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "no,en;q=0.8",
            "Accept": "application/json,text/html;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_url_node(url, timeout):
    script = r"""
const url = process.argv[1];
fetch(url, {
  headers: {
    "user-agent": "Mozilla/5.0",
    "accept-language": "no,en;q=0.8",
    "accept": "application/json,text/html;q=0.8"
  }
}).then(async response => {
  const buffer = Buffer.from(await response.arrayBuffer());
  if (!response.ok) {
    console.error(`${response.status} ${response.statusText}`);
    process.exit(2);
  }
  process.stdout.write(buffer.toString("base64"));
}).catch(error => {
  console.error(error && error.message ? error.message : String(error));
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    result = subprocess.run(
        [NODE_EXE, "--no-warnings", "-e", script, url],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout + 8,
    )
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(clean_text(result.stderr) or "Kunne ikke hente butikkdata.")
    return base64.b64decode(result.stdout).decode("utf-8", errors="replace")


def cached(key, loader):
    now = time.time()
    with CACHE_LOCK:
        item = CACHE.get(key)
        if item and now - item["time"] < CACHE_TTL:
            return item["value"]
    value = loader()
    with CACHE_LOCK:
        CACHE[key] = {"time": now, "value": value}
    return value


def get_consultant(consultant_ref):
    consultant_ref = clean_text(consultant_ref)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", consultant_ref):
        return {"found": False, "ref": consultant_ref}
    registered = find_registered_consultant(consultant_ref)
    if not registered:
        return {"found": False, "ref": consultant_ref}

    def load():
        return {
            "found": True,
            "registered": True,
            "ref": registered.get("reference_code", consultant_ref),
            "name": clean_text(registered.get("display_name") or consultant_ref),
            "consultant": registered,
        }

    return cached(f"consultant:{consultant_ref.lower()}", load)


def fetch_paginated_products(collection=""):
    products = []
    if collection:
        path = f"{SHOP_PATH}/collections/{quote(collection)}/products.json"
    else:
        path = f"{SHOP_PATH}/products.json"
    for page in range(1, 6):
        query = urlencode({"limit": 250, "page": page, "country": "NO"})
        payload = json.loads(fetch_url(f"{BASE_URL}{path}?{query}"))
        page_products = payload.get("products") or []
        products.extend(page_products)
        if len(page_products) < 250:
            break
    return products


def normalize_image(image):
    if isinstance(image, dict):
        return clean_text(image.get("src"))
    return clean_text(image)


def normalize_product(product):
    variants = product.get("variants") or []
    preferred = next((variant for variant in variants if variant.get("available")), None)
    variant = preferred or (variants[0] if variants else {})
    images = [normalize_image(image) for image in (product.get("images") or [])]
    images = [image for image in images if image]
    title = clean_text(product.get("title"))
    series = product_series(title)
    handle = clean_text(product.get("handle"))
    sku = clean_text(variant.get("sku"))
    price = float(variant.get("price") or 0)
    compare_at = float(variant.get("compare_at_price") or 0)
    if compare_at <= price:
        compare_at = 0
    description = html_to_text(product.get("body_html") or product.get("description"))
    tags = [clean_text(tag) for tag in (product.get("tags") or []) if clean_text(tag)]
    searchable = search_key(" ".join([title, sku, description, " ".join(tags)]))
    return {
        "id": product.get("id"),
        "title": title,
        "handle": handle,
        "articleNumber": sku or (handle if handle.isdigit() else ""),
        "description": description,
        "price": price,
        "compareAtPrice": compare_at,
        "available": any(item.get("available") for item in variants),
        "image": images[0] if images else "",
        "images": images[:10],
        "tags": tags,
        "series": series,
        "searchable": searchable,
        "url": f"{BASE_URL}{SHOP_PATH}/products/{quote(handle)}?ref={CONSULTANT_REF}",
        "isInOfficialCatalog": True,
        "catalogStatus": "active" if any(item.get("available") for item in variants) else "temporarily-unavailable",
        "publishedAt": clean_text(product.get("published_at")),
        "createdAt": clean_text(product.get("created_at")),
        "sourceUpdatedAt": clean_text(product.get("updated_at")),
        "firstSeenAt": "",
        "lastSeenAt": "",
        "removedAt": "",
        "titleNo": "",
        "descriptionNo": "",
        "translationSourceLanguage": "",
        "translationSourceTitle": "",
        "translationSourceDescription": "",
    }


def normalize_archived_product(row):
    title = clean_text(row.get("title"))
    article_number = clean_text(row.get("article_number"))
    description = clean_text(row.get("description"))
    series = clean_text(row.get("series"))
    tags = row.get("tags") if isinstance(row.get("tags"), list) else []
    images = row.get("images") if isinstance(row.get("images"), list) else []
    image = clean_text(row.get("image_url"))
    if image and image not in images:
        images.insert(0, image)
    searchable = search_key(
        " ".join([title, article_number, description, series, " ".join(tags)])
    )
    return {
        "id": row.get("shopify_product_id"),
        "title": title,
        "handle": clean_text(row.get("handle")),
        "articleNumber": article_number,
        "description": description,
        "price": float(row.get("price_nok") or 0),
        "compareAtPrice": float(row.get("compare_at_price_nok") or 0),
        "available": bool(row.get("available")),
        "image": image or (images[0] if images else ""),
        "images": [clean_text(item) for item in images if clean_text(item)][:10],
        "tags": [clean_text(tag) for tag in tags if clean_text(tag)],
        "series": series,
        "searchable": searchable,
        "url": clean_text(row.get("source_url")),
        "isInOfficialCatalog": False,
        "catalogStatus": "not-in-current-assortment",
        "publishedAt": "",
        "createdAt": "",
        "sourceUpdatedAt": "",
        "firstSeenAt": clean_text(row.get("first_seen_at")),
        "lastSeenAt": clean_text(row.get("last_seen_at")),
        "removedAt": clean_text(row.get("removed_at")),
        "titleNo": clean_text(row.get("title_no")),
        "descriptionNo": clean_text(row.get("description_no")),
        "translationSourceLanguage": clean_text(row.get("translation_source_language")),
        "translationSourceTitle": clean_text(row.get("translation_source_title")),
        "translationSourceDescription": clean_text(row.get("translation_source_description")),
    }


def attach_saved_translation(product, row):
    if not row:
        return product
    product["titleNo"] = clean_text(row.get("title_no"))
    product["descriptionNo"] = clean_text(row.get("description_no"))
    product["translationSourceLanguage"] = clean_text(
        row.get("translation_source_language")
    )
    product["translationSourceTitle"] = clean_text(row.get("translation_source_title"))
    product["translationSourceDescription"] = clean_text(
        row.get("translation_source_description")
    )
    return product


def translate_text_to_norwegian(value):
    source = clean_text(value)
    if not source:
        return "", ""

    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()

    def load():
        query = urlencode(
            {
                "client": "gtx",
                "sl": "auto",
                "tl": "no",
                "dt": "t",
                "q": source,
            }
        )
        payload = json.loads(
            fetch_url(
                f"https://translate.googleapis.com/translate_a/single?{query}",
                timeout=18,
            )
        )
        translated = clean_text(
            "".join(
                clean_text(part[0])
                for part in (payload[0] or [])
                if isinstance(part, list) and part
            )
        )
        language = clean_text(payload[2] if len(payload) > 2 else "")
        return translated or source, language

    return cached(f"translation:no:{digest}", load)


def norwegian_product_text(product):
    source_title = clean_text(product.get("title"))
    source_description = clean_text(product.get("description"))
    saved_is_current = (
        clean_text(product.get("translationSourceTitle")) == source_title
        and clean_text(product.get("translationSourceDescription")) == source_description
    )
    if saved_is_current and product.get("titleNo"):
        localized = dict(product)
        localized["originalTitle"] = source_title
        localized["originalDescription"] = source_description
        localized["title"] = NORWEGIAN_PRODUCT_TITLES.get(
            product.get("handle"), clean_text(product.get("titleNo")) or source_title
        )
        localized["description"] = NORWEGIAN_PRODUCT_DESCRIPTIONS.get(
            product.get("handle"),
            clean_text(product.get("descriptionNo")) or source_description,
        )
        localized["textSource"] = (
            "official-no"
            if product.get("translationSourceLanguage") in ("no", "nb", "nn")
            else "automatic-translation"
        )
        if (
            localized["title"] != clean_text(product.get("titleNo"))
            or localized["description"] != clean_text(product.get("descriptionNo"))
        ):
            try:
                save_official_product_translation(
                    product.get("handle"),
                    source_title,
                    source_description,
                    localized["title"],
                    localized["description"],
                    product.get("translationSourceLanguage"),
                )
            except Exception as error:
                print(f"Norsk produkttekst kunne ikke oppdateres: {error}", file=sys.stderr)
        return localized

    localized = dict(product)
    try:
        title_for_translation = source_title
        if re.match(r"^Set\s+", title_for_translation, flags=re.IGNORECASE):
            title_for_translation = re.sub(
                r"^Set\s+", "Set: ", title_for_translation, count=1, flags=re.IGNORECASE
            )
        title_no, title_language = translate_text_to_norwegian(title_for_translation)
        title_no = NORWEGIAN_PRODUCT_TITLES.get(product.get("handle"), title_no)
        description_no, description_language = translate_text_to_norwegian(
            source_description
        )
        description_no = NORWEGIAN_PRODUCT_DESCRIPTIONS.get(
            product.get("handle"), description_no
        )
        source_language = description_language or title_language
        localized["originalTitle"] = source_title
        localized["originalDescription"] = source_description
        localized["title"] = title_no or source_title
        localized["description"] = description_no or source_description
        localized["textSource"] = (
            "official-no"
            if source_language in ("no", "nb", "nn")
            else "automatic-translation"
        )
        try:
            save_official_product_translation(
                product.get("handle"),
                source_title,
                source_description,
                localized["title"],
                localized["description"],
                source_language,
            )
        except Exception as error:
            print(f"Norsk produkttekst kunne ikke lagres: {error}", file=sys.stderr)
    except Exception as error:
        print(f"Produktteksten kunne ikke oversettes: {error}", file=sys.stderr)
        localized["textSource"] = "source"
    return localized


def product_added_timestamp(product):
    value = (
        product.get("createdAt")
        or product.get("publishedAt")
        or product.get("firstSeenAt")
        or ""
    )
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return 0


def product_updated_timestamp(product):
    if product.get("isInOfficialCatalog") is False:
        value = product.get("removedAt") or product.get("lastSeenAt") or ""
    else:
        value = product.get("sourceUpdatedAt") or product.get("publishedAt") or ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return product_added_timestamp(product)


def get_products(collection=""):
    key = f"products:{collection or 'all'}"
    raw = cached(key, lambda: fetch_paginated_products(collection))
    live_products = [normalize_product(product) for product in raw]
    if collection:
        return live_products

    if sync_is_configured() and len(live_products) >= 300:
        try:
            cached(
                "official-catalog-sync",
                lambda: sync_official_products(live_products),
            )
        except Exception as error:
            print(f"Produktarkivet kunne ikke synkroniseres: {error}", file=sys.stderr)

    try:
        archived_rows = cached(
            "official-product-archive",
            list_official_product_archive,
        )
    except Exception as error:
        print(f"Produktarkivet kunne ikke leses: {error}", file=sys.stderr)
        archived_rows = []

    archived_by_handle = {
        clean_text(row.get("handle")): row
        for row in archived_rows
        if clean_text(row.get("handle"))
    }
    live_products = [
        attach_saved_translation(product, archived_by_handle.get(product["handle"]))
        for product in live_products
    ]

    live_handles = {product["handle"] for product in live_products}
    archived_products = [
        normalize_archived_product(row)
        for row in archived_rows
        if clean_text(row.get("handle")) not in live_handles
    ]
    return live_products + archived_products


def get_raw_collections():
    def load():
        url = f"{BASE_URL}{SHOP_PATH}/collections.json?limit=250"
        return json.loads(fetch_url(url)).get("collections") or []

    return cached("collections", load)


def get_collections(raw=None):
    raw = raw if raw is not None else get_raw_collections()
    by_handle = {item.get("handle"): item for item in raw}
    result = []
    all_item = by_handle.get("tupperware") or {}
    result.append(
        {
            "title": "Alle produkter",
            "handle": "",
            "image": normalize_image(all_item.get("image")),
            "children": [],
        }
    )
    for group in NAVIGATION:
        source = by_handle.get(group["handle"]) or {}
        children = []
        for title, handle in group["children"]:
            child = by_handle.get(handle) or {}
            children.append(
                {
                    "title": clean_text(child.get("title")) or title,
                    "handle": handle,
                    "image": normalize_image(child.get("image")),
                }
            )
        result.append(
            {
                "title": group["title"],
                "handle": group["handle"],
                "image": normalize_image(source.get("image")),
                "children": children,
            }
        )
    return result


def get_series(products=None):
    products = products if products is not None else get_products()
    counts = {}
    for product in products:
        title = clean_text(product.get("series"))
        if title:
            counts[title] = counts.get(title, 0) + 1
    return [
        {"title": title, "count": count}
        for title, count in sorted(counts.items(), key=lambda item: search_key(item[0]))
    ]


def product_detail(handle):
    products = get_products()
    match = next((product for product in products if product["handle"] == handle), None)
    if match and match.get("isInOfficialCatalog") is False:
        return norwegian_product_text(match)

    try:
        url = f"{BASE_URL}{SHOP_PATH}/products/{quote(handle)}.json?country=NO"
        payload = json.loads(fetch_url(url))
        current = normalize_product(payload.get("product") or {})
        if not current.get("handle"):
            raise RuntimeError("Produktet mangler i den norske nettbutikken.")
        if match:
            for field in (
                "price",
                "compareAtPrice",
                "available",
                "catalogStatus",
                "isInOfficialCatalog",
                "firstSeenAt",
                "lastSeenAt",
                "removedAt",
            ):
                current[field] = match.get(field)
            attach_saved_translation(current, {
                "title_no": match.get("titleNo"),
                "description_no": match.get("descriptionNo"),
                "translation_source_language": match.get("translationSourceLanguage"),
                "translation_source_title": match.get("translationSourceTitle"),
                "translation_source_description": match.get("translationSourceDescription"),
            })
        return norwegian_product_text(current)
    except Exception:
        if match:
            return norwegian_product_text(match)
        raise


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[butikk] {self.address_string()} - {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            return self.json_response(
                200,
                {"ok": True, "consultantRegistry": registry_is_configured()},
            )
        if path == "/api/consultants":
            try:
                search = clean_text((query.get("q") or [""])[0])
                try:
                    limit = int((query.get("limit") or ["50"])[0])
                except ValueError:
                    limit = 50
                consultants = list_registered_consultants(search, limit)
                return self.json_response(
                    200,
                    {
                        "consultants": consultants,
                        "count": len(consultants),
                        "configured": registry_is_configured(),
                    },
                )
            except Exception as error:
                return self.json_response(
                    502,
                    {"error": f"Kunne ikke hente konsulentregisteret: {error}"},
                )
        if path == "/api/consultant":
            consultant_ref = clean_text((query.get("ref") or [""])[0])
            try:
                registered = find_registered_consultant(consultant_ref)
                if registered:
                    return self.json_response(
                        200,
                        {
                            "found": True,
                            "registered": True,
                            "ref": registered["reference_code"],
                            "name": registered["display_name"],
                            "consultant": registered,
                        },
                    )
                return self.json_response(200, get_consultant(consultant_ref))
            except Exception as error:
                return self.json_response(
                    502,
                    {"error": f"Kunne ikke kontrollere konsulentreferansen: {error}"},
                )
        if path == "/api/shop-status":
            consultant_ref = clean_text((query.get("ref") or [""])[0]).upper()
            try:
                status = consultant_shop_status(consultant_ref)
                return self.json_response(
                    200,
                    {
                        "enabled": bool(status and status.get("enabled")),
                        "accessMode": (
                            status.get("access_mode") if status else "public"
                        ),
                        "hasProducts": bool(status and status.get("has_products")),
                    },
                )
            except Exception as error:
                return self.json_response(
                    502,
                    {"error": f"Kunne ikke hente butikkstatus: {error}"},
                )
        if path == "/api/product-access":
            consultant_ref = clean_text((query.get("ref") or [""])[0]).upper()
            if not consultant_ref:
                return self.json_response(400, {"error": "Konsulentreferanse mangler."})
            try:
                return self.json_response(
                    200,
                    {"products": consultant_product_access(consultant_ref)},
                )
            except Exception as error:
                return self.json_response(
                    502,
                    {"error": f"Kunne ikke hente produkttilgang: {error}"},
                )
        if path == "/api/public-config":
            return self.json_response(200, public_config())
        if path == "/api/navigation":
            try:
                raw_collections = get_raw_collections()
                return self.json_response(
                    200,
                    {
                        "collections": get_collections(raw_collections),
                        "series": get_series(),
                        "consultant": CONSULTANT_REF,
                        "source": f"{BASE_URL}{SHOP_PATH}",
                    },
                )
            except Exception as error:
                return self.json_response(502, {"error": str(error)})
        if path == "/api/products":
            try:
                collection = clean_text((query.get("collection") or [""])[0])
                series = clean_text((query.get("series") or [""])[0])
                search = search_key((query.get("q") or [""])[0])
                sort = clean_text((query.get("sort") or ["newest"])[0])
                status = clean_text((query.get("status") or ["all"])[0])
                try:
                    offset = max(0, int((query.get("offset") or ["0"])[0]))
                    limit = min(96, max(1, int((query.get("limit") or ["48"])[0])))
                except ValueError:
                    offset, limit = 0, 48
                products = get_products(collection)
                if series:
                    series_key = search_key(series)
                    products = [
                        product
                        for product in products
                        if search_key(product.get("series")) == series_key
                    ]
                if search:
                    words = [word for word in search.split() if word]
                    products = [
                        product
                        for product in products
                        if all(word in product["searchable"] for word in words)
                    ]
                if status != "all":
                    allowed_statuses = {
                        "active",
                        "temporarily-unavailable",
                        "not-in-current-assortment",
                    }
                    if status in allowed_statuses:
                        products = [
                            product
                            for product in products
                            if product.get("catalogStatus") == status
                        ]
                if sort == "newest":
                    products.sort(
                        key=lambda item: (
                            item.get("isInOfficialCatalog") is not False,
                            product_added_timestamp(item),
                        ),
                        reverse=True,
                    )
                elif sort == "updated":
                    products.sort(key=product_updated_timestamp, reverse=True)
                elif sort == "title":
                    products.sort(key=lambda item: search_key(item["title"]))
                elif sort == "price-asc":
                    products.sort(key=lambda item: item["price"])
                elif sort == "price-desc":
                    products.sort(key=lambda item: item["price"], reverse=True)
                elif sort == "sale":
                    products.sort(
                        key=lambda item: (
                            item["compareAtPrice"] <= 0,
                            -(
                                (item["compareAtPrice"] - item["price"])
                                / item["compareAtPrice"]
                                if item["compareAtPrice"]
                                else 0
                            ),
                        )
                    )
                total = len(products)
                products = products[offset : offset + limit]
                return self.json_response(
                    200,
                    {
                        "products": products,
                        "count": total,
                        "collection": collection,
                        "series": series,
                        "offset": offset,
                        "hasMore": offset + len(products) < total,
                    },
                )
            except Exception as error:
                return self.json_response(502, {"error": str(error)})
        if path.startswith("/api/products/"):
            try:
                handle = unquote(path.rsplit("/", 1)[-1])
                return self.json_response(200, {"product": product_detail(handle)})
            except Exception as error:
                return self.json_response(502, {"error": str(error)})

        return self.serve_static(path, query)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("/api/own-products", "/api/own-orders"):
            return self.json_response(404, {"error": "Fant ikke endepunktet."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                return self.json_response(400, {"error": "Ugyldig bestillingsdata."})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if parsed.path == "/api/own-products":
                consultant_ref = clean_text(payload.get("referenceCode")).upper()
                status = consultant_shop_status(consultant_ref)
                if not status or not status.get("enabled") or not status.get("has_products"):
                    return self.json_response(
                        404,
                        {"error": "Denne konsulentbutikken er ikke aktiv."},
                    )
                if status.get("access_mode") == "code" and not clean_text(
                    payload.get("accessCode")
                ):
                    return self.json_response(
                        401,
                        {
                            "error": "Oppgi kundekoden for å se varene.",
                            "accessRequired": True,
                        },
                    )
                try:
                    products = list_own_inventory(
                        consultant_ref,
                        payload.get("accessCode"),
                    )
                except Exception:
                    return self.json_response(
                        403,
                        {
                            "error": "Kundekoden er ikke riktig.",
                            "accessRequired": True,
                        },
                    )
                consultant = find_registered_consultant(consultant_ref)
                return self.json_response(
                    200,
                    {
                        "products": products,
                        "count": len(products),
                        "consultant": consultant,
                        "accessMode": status.get("access_mode"),
                    },
                )
            order_id = submit_own_inventory_order(
                payload.get("referenceCode"),
                payload.get("customer") or {},
                payload.get("items") or [],
                payload.get("accessCode"),
            )
            return self.json_response(
                201,
                {"ok": True, "orderId": order_id},
            )
        except Exception as error:
            return self.json_response(
                400,
                {"error": f"Bestillingen kunne ikke sendes: {error}"},
            )

    def product_access_denied(self, consultant_ref, product_key):
        product_titles = {
            "norsk-nettkatalog": "Norsk Nettkatalog",
            "norsk-produktkatalog": "Norsk produktkatalog",
            "egne-varer": "Egne varer",
        }
        title = product_titles.get(product_key, "Dette produktet")
        reference = consultant_ref or "mangler"
        body = f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#007b68"><title>Tilgang mangler</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;font-family:Arial,sans-serif;color:#202825;background:#f4f8f6}}
header{{height:10px;background:#007b68}} main{{max-width:720px;margin:0 auto;padding:64px 24px}}
.eyebrow{{color:#007b68;font-size:12px;font-weight:800;text-transform:uppercase}} h1{{font-size:clamp(30px,7vw,52px);margin:12px 0 18px}}
p{{font-size:17px;line-height:1.6}} .reference{{margin-top:28px;padding-top:18px;border-top:1px solid #cad8d2;color:#53615c}}
a{{display:inline-block;margin-top:24px;color:#fff;background:#007b68;padding:13px 18px;text-decoration:none;font-weight:750}}
</style></head><body><header></header><main><p class="eyebrow">Produkttilgang</p>
<h1>Tilgang til {title} mangler</h1>
<p>Denne konsulenten har ikke kjøpt tilgang til produktet. Kontakt administrator hvis tilgangen skal åpnes.</p>
<p class="reference">Konsulentreferanse: <strong>{reference}</strong></p>
<a href="/mine-sider?ref={consultant_ref}">Til Mine sider</a></main></body></html>""".encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def required_product(self, path):
        if path in ("/", "/index.html", "/norsk-nettkatalog", "/norsk-nettkatalog/"):
            return "norsk-nettkatalog"
        if path in (
            "/digital-katalog", "/digital-katalog/",
            "/kataloghefte-test", "/kataloghefte-test/",
            "/catalog-demo/", "/catalog-demo/index.html",
        ):
            return "norsk-produktkatalog"
        if path in ("/egne-varer", "/egne-varer/", "/own.html"):
            return "egne-varer"
        return None

    def serve_static(self, path, query=None):
        required_product = self.required_product(path)
        if required_product:
            consultant_ref = clean_text(((query or {}).get("ref") or [""])[0]).upper()
            try:
                access = consultant_product_access(consultant_ref)
            except Exception:
                access = []
            if not consultant_ref or required_product not in access:
                return self.product_access_denied(consultant_ref, required_product)

        filenames = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/norsk-nettkatalog": ("index.html", "text/html; charset=utf-8"),
            "/norsk-nettkatalog/": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/egne-varer": ("own.html", "text/html; charset=utf-8"),
            "/egne-varer/": ("own.html", "text/html; charset=utf-8"),
            "/own.html": ("own.html", "text/html; charset=utf-8"),
            "/own.css": ("own.css", "text/css; charset=utf-8"),
            "/own.js": ("own.js", "application/javascript; charset=utf-8"),
            "/konsulent": ("manage.html", "text/html; charset=utf-8"),
            "/konsulent/": ("manage.html", "text/html; charset=utf-8"),
            "/manage.html": ("manage.html", "text/html; charset=utf-8"),
            "/manage.css": ("manage.css", "text/css; charset=utf-8"),
            "/manage.js": ("manage.js", "application/javascript; charset=utf-8"),
            "/mine-sider": ("hub.html", "text/html; charset=utf-8"),
            "/mine-sider/": ("hub.html", "text/html; charset=utf-8"),
            "/hub.html": ("hub.html", "text/html; charset=utf-8"),
            "/hub.css": ("hub.css", "text/css; charset=utf-8"),
            "/hub.js": ("hub.js", "application/javascript; charset=utf-8"),
            "/kataloghefte-test": ("catalog-demo/index.html", "text/html; charset=utf-8"),
            "/kataloghefte-test/": ("catalog-demo/index.html", "text/html; charset=utf-8"),
            "/digital-katalog": ("catalog-demo/index.html", "text/html; charset=utf-8"),
            "/digital-katalog/": ("catalog-demo/index.html", "text/html; charset=utf-8"),
            "/catalog-demo/": ("catalog-demo/index.html", "text/html; charset=utf-8"),
            "/catalog-demo/index.html": ("catalog-demo/index.html", "text/html; charset=utf-8"),
        }
        item = filenames.get(path)
        if not item and re.fullmatch(r"/catalog-demo/pages/page-\d{2}\.webp", path):
            item = (path.lstrip("/"), "image/webp")
        if not item:
            if path.startswith("/api/"):
                return self.json_response(404, {"error": "Fant ikke endepunktet."})
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if "." not in Path(path).name:
                item = ("index.html", "text/html; charset=utf-8")
            else:
                return self.json_response(404, {"error": "Fant ikke filen."})
        filename, content_type = item
        body = (ROOT / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def json_response(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer((APP_HOST, APP_PORT), Handler)
    print(f"Tupperware Norsk Nettkatalog kjører på http://127.0.0.1:{APP_PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
