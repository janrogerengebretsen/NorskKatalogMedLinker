from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import base64
import html as html_lib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import traceback
import unicodedata
import webbrowser


APP_HOST = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
APP_PORT = int(os.environ.get("PORT", "8787"))
USER_AGENT = "Mozilla/5.0"
NODE_EXE = shutil.which("node") or os.path.expanduser(
    r"~\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)
FRENCH_CATALOG_URL = "https://tupperware-eu.com/products.json"
NORWEGIAN_CATALOG_URL = "https://tupperware-eu.com/no/products.json"
ENGLISH_CATALOG_URL = "https://tupperware-eu.com/en/products.json"
FRENCH_CATALOG = []
FRENCH_CATALOG_LOCK = threading.Lock()

NORWEGIAN_FRENCH_TERMS = {
    "bake": ("patisserie", "four", "cuisson", "gateau"),
    "bolle": ("bol", "saladier"),
    "brød": ("pain",),
    "barn": ("enfant", "bebe"),
    "drikke": ("boisson", "gourde", "bouteille"),
    "flaske": ("bouteille", "gourde"),
    "fryse": ("congeler", "congelateur", "congelation"),
    "grønnsak": ("legume",),
    "hakke": ("hacher", "hachoir", "couper"),
    "hakker": ("hachoir", "hacher"),
    "kaffe": ("cafe", "mug"),
    "kjøleskap": ("refrigerateur", "frigo"),
    "kniv": ("couteau",),
    "koke": ("cuire", "cuisson", "casserole"),
    "kutte": ("couper", "decouper", "couteau"),
    "løk": ("oignon",),
    "matboks": ("repas", "lunch", "emporter"),
    "mikrobølgeovn": ("micro-ondes", "micro onde"),
    "måle": ("mesure", "doseur", "gradue"),
    "oppbevaring": ("conservation", "conserver", "rangement", "stockage"),
    "ost": ("fromage",),
    "salat": ("salade", "saladier"),
    "servere": ("service", "servir"),
    "slikkepott": ("spatule",),
    "tørrvarer": ("sec", "placard"),
    "varm": ("chaud", "isotherme"),
    "vann": ("eau", "boisson"),
    "vispe": ("fouet", "fouetter"),
}
NORWEGIAN_PRODUCT_HINTS = {
    "brød": ("boite a pain", "viennoiserie"),
    "hakke": ("chopper", "hachoir", "dicer"),
    "hakker": ("chopper", "hachoir", "dicer"),
    "matboks": ("lunch", "repas", "emporter"),
    "mikrobølgeovn": ("micro", "crystalwave", "microcook"),
    "oppbevaring": ("boite", "conservation", "modulaire"),
}


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.ld_json = []
        self.in_ld_json = False
        self.ld_buffer = []
        self.title_parts = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            content = attrs.get("content")
            if key and content:
                self.meta[key.lower()] = content.strip()
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.in_ld_json = True
            self.ld_buffer = []
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "script" and self.in_ld_json:
            text = "".join(self.ld_buffer).strip()
            if text:
                self.ld_json.append(text)
            self.in_ld_json = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_ld_json:
            self.ld_buffer.append(data)
        if self.in_title:
            self.title_parts.append(data)


class SearchResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.in_link = False
        self.current_href = ""
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        class_name = attrs.get("class", "")
        if tag == "a" and ("result__a" in class_name or attrs.get("data-testid") == "result-title-a"):
            self.in_link = True
            self.current_href = attrs.get("href", "")
            self.current_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self.in_link:
            title = clean_text(" ".join(self.current_text))
            href = normalize_duckduckgo_url(self.current_href)
            if title and href and href.startswith("http"):
                self.results.append({"title": title, "url": href})
            self.in_link = False

    def handle_data(self, data):
        if self.in_link:
            self.current_text.append(data)


class PlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if clean_text(data):
            self.parts.append(data)

    def text(self):
        return clean_text(" ".join(self.parts))


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def html_to_text(value):
    parser = PlainTextParser()
    parser.feed(value or "")
    return parser.text()


def normalize_search_text(value):
    value = clean_text(value).lower().translate(
        str.maketrans({"ø": "o", "æ": "ae", "å": "a", "œ": "oe"})
    )
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def fetch_shopify_catalog(catalog_url, country=""):
    products = []
    for page in range(1, 5):
        parsed_url = urlparse(catalog_url)
        query = parse_qs(parsed_url.query)
        query.update({"limit": ["250"], "page": [str(page)]})
        if country:
            query["country"] = [country]
        request_url = urlunparse(
            parsed_url._replace(query=urlencode(query, doseq=True))
        )
        payload = json.loads(fetch_url(request_url, timeout=30))
        page_products = payload.get("products") or []
        products.extend(page_products)
        if len(page_products) < 250:
            break
    return products


def catalog_product_keys(product):
    variants = product.get("variants") or []
    sku = clean_text(variants[0].get("sku")) if variants else ""
    handle = clean_text(product.get("handle"))
    return [key for key in (sku, handle) if key]


def load_french_catalog():
    if FRENCH_CATALOG:
        return FRENCH_CATALOG
    with FRENCH_CATALOG_LOCK:
        if FRENCH_CATALOG:
            return FRENCH_CATALOG
        french_products = fetch_shopify_catalog(FRENCH_CATALOG_URL, country="FR")
        norwegian_products = fetch_shopify_catalog(NORWEGIAN_CATALOG_URL, country="NO")
        english_products = fetch_shopify_catalog(ENGLISH_CATALOG_URL, country="GB")
        norwegian_by_key = {
            key: product for product in norwegian_products for key in catalog_product_keys(product)
        }
        english_by_key = {
            key: product for product in english_products for key in catalog_product_keys(product)
        }
        products = []
        for product in french_products:
            variants = product.get("variants") or []
            sku = clean_text(variants[0].get("sku")) if variants else ""
            french_handle = clean_text(product.get("handle"))
            norwegian_product = norwegian_by_key.get(sku) or norwegian_by_key.get(french_handle) or {}
            english_product = english_by_key.get(sku) or english_by_key.get(french_handle) or {}
            norwegian_variants = norwegian_product.get("variants") or []
            english_variants = english_product.get("variants") or []
            norwegian_sku = clean_text(norwegian_variants[0].get("sku")) if norwegian_variants else ""
            english_sku = clean_text(english_variants[0].get("sku")) if english_variants else ""
            article_number = first_value(
                sku,
                norwegian_sku,
                english_sku,
                french_handle if french_handle.isdigit() else "",
            )
            title = first_value(
                norwegian_product.get("title"),
                english_product.get("title"),
                product.get("title"),
            )
            english_title = clean_text(english_product.get("title"))
            if normalize_search_text(english_title) == normalize_search_text(title):
                english_title = ""
            description = first_value(
                html_to_text(norwegian_product.get("body_html")),
                html_to_text(english_product.get("body_html")),
                html_to_text(product.get("body_html")),
            )
            handle = first_value(
                norwegian_product.get("handle"),
                english_product.get("handle"),
                french_handle,
            )
            display_product = norwegian_product or english_product or product
            display_variants = display_product.get("variants") or []
            display_variant = display_variants[0] if display_variants else {}
            availability_values = [
                variant.get("available")
                for variant in display_variants
                if "available" in variant
            ]
            if any(value is True for value in availability_values):
                availability = "available"
            elif availability_values:
                availability = "unavailable"
            else:
                availability = "unknown"
            norwegian_variant = norwegian_variants[0] if norwegian_variants else {}
            price_value = clean_text(norwegian_variant.get("price"))
            price = format_price(price_value, "NOK")
            compare_value = clean_text(norwegian_variant.get("compare_at_price"))
            compare_price = (
                ""
                if is_zero_price(compare_value)
                else format_price(compare_value, "NOK")
            )
            display_images = display_product.get("images") or []
            image = ""
            if display_images:
                first_image = display_images[0]
                image = first_image.get("src", "") if isinstance(first_image, dict) else str(first_image)
            image = normalize_image_url(image)
            if not title or not handle:
                continue
            searchable = normalize_search_text(
                " ".join(
                    [
                        article_number,
                        title,
                        description,
                        clean_text(product.get("title")),
                        html_to_text(product.get("body_html")),
                        clean_text(english_product.get("title")),
                        html_to_text(english_product.get("body_html")),
                        clean_text(" ".join(product.get("tags") or [])),
                    ]
                )
            )
            products.append(
                {
                    "articleNumber": article_number,
                    "title": title,
                    "englishTitle": english_title,
                    "description": description,
                    "handle": handle,
                    "image": image,
                    "price": price,
                    "comparePrice": compare_price,
                    "isSale": bool(compare_price and price and compare_price != price),
                    "availability": availability,
                    "searchable": searchable,
                }
            )
        products.sort(key=lambda item: normalize_search_text(item["title"]))
        FRENCH_CATALOG.extend(products)
    return FRENCH_CATALOG


def search_french_catalog_products(reference, limit=None):
    query = normalize_search_text(reference)
    catalog = load_french_catalog()
    if not query:
        return catalog if limit is None else catalog[:limit]
    for product in catalog:
        if query in (
            normalize_search_text(product["articleNumber"]),
            normalize_search_text(product["handle"]),
        ):
            return [product]

    query_words = [word for word in query.split() if len(word) > 1]
    expanded_words = []
    title_hints = []
    for word in query_words:
        expanded_words.append((word, 14))
        for norwegian, french_terms in NORWEGIAN_FRENCH_TERMS.items():
            normalized_norwegian = normalize_search_text(norwegian)
            if word == normalized_norwegian or word.startswith(normalized_norwegian):
                expanded_words.extend((normalize_search_text(term), 10) for term in french_terms)
        for norwegian, hints in NORWEGIAN_PRODUCT_HINTS.items():
            normalized_norwegian = normalize_search_text(norwegian)
            if word == normalized_norwegian or word.startswith(normalized_norwegian):
                title_hints.extend(normalize_search_text(hint) for hint in hints)

    matches = []
    for product in catalog:
        title = normalize_search_text(product["title"])
        searchable = product["searchable"]
        score = 0
        if query == title:
            score += 120
        elif query in title:
            score += 60
        elif query in searchable:
            score += 32
        for hint in title_hints:
            if hint in title:
                score += 45
        for term, weight in expanded_words:
            if not term:
                continue
            if term in title:
                score += weight * 2
            elif term in searchable:
                score += weight
        if title.startswith("set "):
            score -= 12
        if score >= 10:
            matches.append((score, normalize_search_text(product["title"]), product))
    matches.sort(key=lambda item: (-item[0], item[1]))
    ordered = [item[2] for item in matches]
    return ordered if limit is None else ordered[:limit]


def find_french_catalog_product(reference):
    matches = search_french_catalog_products(reference, limit=1)
    return matches[0] if matches else None


def find_catalog_product_exact(reference):
    normalized = normalize_search_text(reference)
    if not normalized:
        return None
    for product in load_french_catalog():
        if normalized in (
            normalize_search_text(product.get("articleNumber")),
            normalize_search_text(product.get("handle")),
        ):
            return product
    return None


def fetch_url(url, timeout=18):
    if sys.platform.startswith("win") and url.startswith("https://"):
        return fetch_url_node(url, timeout)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "no,en;q=0.8"})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def fetch_url_curl(url, timeout):
    result = subprocess.run(
        ["curl.exe", "-k", "-L", "-A", USER_AGENT, "-H", "Accept-Language: no,en;q=0.8", "--max-time", str(int(timeout)), url],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout + 8,
    )
    if result.returncode != 0 or not result.stdout:
        raise URLError(clean_text(result.stderr) or "Kunne ikke hente siden.")
    return result.stdout


def fetch_url_node(url, timeout):
    script = """
const url = process.argv[1];
fetch(url, {
  headers: {"user-agent": "Mozilla/5.0", "accept-language": "no,en;q=0.8"}
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
        raise URLError(clean_text(result.stderr) or "Kunne ikke hente siden.")
    raw = base64.b64decode(result.stdout)
    return raw.decode("utf-8", errors="replace")


def first_value(*values):
    for value in values:
        if value:
            return clean_text(str(value))
    return ""


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk_json(item)


def extract_product_json(parser):
    for block in parser.ld_json:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for node in walk_json(data):
            node_type = node.get("@type")
            if isinstance(node_type, list):
                is_product = "Product" in node_type
            else:
                is_product = node_type == "Product"
            if is_product:
                return node
    return {}


def parse_product(url):
    html = fetch_url(url)
    product_url = find_product_url_from_search(url, html)
    if product_url and product_url != url:
        url = product_url
        html = fetch_url(url)
    parser = MetadataParser()
    parser.feed(html)
    product = extract_product_json(parser)
    offers = product.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}

    images = collect_product_images(html, product, parser)
    image = images[0] if images else ""

    title = first_value(
        parser.meta.get("og:title"),
        product.get("name"),
        " ".join(parser.title_parts).replace("| Tupperware", ""),
    )
    description = first_value(parser.meta.get("og:description"), product.get("description"))
    price = first_value(
        offers.get("price"),
        parser.meta.get("product:price:amount"),
        parser.meta.get("og:price:amount"),
    )
    currency = first_value(offers.get("priceCurrency"), parser.meta.get("product:price:currency"), "NOK")
    compare_price = extract_compare_price(html, currency)
    formatted_price = format_price(price, currency)
    english_title = ""
    product_path = urlparse(url).path
    catalog_reference = (
        product_path.rsplit("/products/", 1)[-1].strip("/")
        if "/products/" in product_path
        else ""
    )
    catalog_product = find_catalog_product_exact(catalog_reference) if catalog_reference else None
    if not catalog_product and catalog_reference:
        catalog_product = find_french_catalog_product(catalog_reference)
    if catalog_product:
        formatted_price = catalog_product.get("price") or ""
        compare_price = catalog_product.get("comparePrice") or ""
        english_title = catalog_product.get("englishTitle") or ""
    elif is_tupperware_product_url(url):
        formatted_price = ""
        compare_price = ""

    return sanitize_product_prices({
        "title": title,
        "englishTitle": english_title,
        "description": description,
        "price": formatted_price,
        "comparePrice": compare_price,
        "isSale": bool(compare_price and formatted_price and compare_price != formatted_price),
        "image": image or "",
        "images": images,
        "sourceUrl": url,
    })


def collect_product_images(page_html, product, parser):
    images = []

    product_image = product.get("image")
    if isinstance(product_image, list):
        for image in product_image:
            add_image(images, image)
    else:
        add_image(images, product_image)
    add_image(images, parser.meta.get("og:image"))
    add_image(images, parser.meta.get("og:image:secure_url"))

    media_blocks = re.findall(
        r'<[^>]+class=["\'][^"\']*product__media-item[^"\']*["\'][\s\S]*?(?=<[^>]+class=["\'][^"\']*product__media-item|</media-gallery>)',
        page_html,
        flags=re.IGNORECASE,
    )
    for block in media_blocks:
        data_src_match = re.search(r'data-src=["\']([^"\']+)["\']', block, flags=re.IGNORECASE)
        if data_src_match:
            add_image(images, data_src_match.group(1))
            continue
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, flags=re.IGNORECASE)
        if img_match:
            add_image(images, img_match.group(1))

    if len(images) <= 1:
        for match in re.findall(r'["\']((?:https?:)?//tupperware-eu\.com/cdn/shop/files/[^"\']+\.(?:png|jpe?g|webp)[^"\']*)["\']', page_html, flags=re.IGNORECASE):
            lowered = match.lower()
            if any(skip in lowered for skip in ("logo", "icon", "sharing", "background")):
                continue
            add_image(images, match)
            if len(images) >= 10:
                break

    return images[:10]


def add_image(images, image_url):
    normalized = normalize_image_url(image_url)
    if not normalized:
        return
    key = re.sub(r'([?&])width=\d+&?', r'\1', normalized).rstrip("?&")
    existing_keys = {re.sub(r'([?&])width=\d+&?', r'\1', item).rstrip("?&") for item in images}
    if key not in existing_keys:
        images.append(normalized)


def normalize_image_url(image_url):
    if not image_url:
        return ""
    image_url = html_lib.unescape(str(image_url)).replace("\\u0026", "&").strip()
    if image_url.startswith("//"):
        image_url = "https:" + image_url
    if not image_url.startswith(("http://", "https://")):
        return ""
    image_url = re.sub(r'([?&])width=\d+', r'\g<1>width=1200', image_url)
    return image_url.rstrip(",")


def find_product_url_from_search(url, html):
    parsed = urlparse(url)
    if "/search" not in parsed.path:
        return ""
    query = parse_qs(parsed.query)
    search_term = (query.get("q") or [""])[0]
    product_links = re.findall(r'href=["\']([^"\']*/products/[^"\'?#]+)', html)
    if not product_links:
        return ""

    selected = ""
    for href in product_links:
        if search_term and search_term in href:
            selected = href
            break
    if not selected:
        selected = product_links[0]

    if selected.startswith("//"):
        selected = f"{parsed.scheme}:{selected}"
    elif selected.startswith("/"):
        selected = f"{parsed.scheme}://{parsed.netloc}{selected}"
    elif not selected.startswith(("http://", "https://")):
        selected = f"{parsed.scheme}://{parsed.netloc}/{selected.lstrip('/')}"

    target = urlparse(selected)
    target_query = parse_qs(target.query)
    for key in ("ref", "consultant", "affiliate"):
        if key in query and key not in target_query:
            target_query[key] = query[key]
    return urlunparse(target._replace(query=urlencode(target_query, doseq=True)))


def resolve_product_reference(reference, consultant):
    reference = clean_text(reference)
    if not reference:
        return ""
    catalog_product = find_french_catalog_product(reference)
    if catalog_product:
        product_url = f"https://tupperware-eu.com/no/products/{catalog_product['handle']}"
        return consultant_url(product_url, consultant)
    search_url = consultant_url(
        f"https://tupperware-eu.com/no/search?q={quote_plus(reference)}",
        consultant,
    )
    search_html = fetch_url(search_url, timeout=20)
    product_url = find_product_url_from_search(search_url, search_html)
    if not product_url:
        raise ValueError(f"Fant ikke et Tupperware-produkt for '{reference}'.")
    return product_url


def format_price(price, currency):
    if not price:
        return ""
    normalized = str(price).replace(".", ",")
    if currency and currency.upper() not in normalized.upper():
        return f"{normalized} {currency.upper()}"
    return normalized


def is_tupperware_product_url(url):
    host = urlparse(clean_text(url)).netloc.lower().split(":", 1)[0]
    return host == "tupperware-eu.com" or host.endswith(".tupperware-eu.com")


def is_nok_price(value):
    return bool(re.search(r"(?:^|\s)NOK(?:\s|$)", clean_text(value), flags=re.IGNORECASE))


def sanitize_product_prices(product):
    price = clean_text(product.get("price"))
    compare_price = clean_text(product.get("comparePrice"))
    if is_tupperware_product_url(product.get("sourceUrl")):
        if not is_nok_price(price):
            price = ""
        if not is_nok_price(compare_price):
            compare_price = ""
    if is_zero_price(compare_price) or compare_price == price:
        compare_price = ""
    product["price"] = price
    product["comparePrice"] = compare_price
    product["isSale"] = bool(price and compare_price)
    return product


def is_zero_price(value):
    number = re.search(r"-?\d+(?:[.,]\d+)?", clean_text(str(value)))
    if not number:
        return False
    try:
        return float(number.group(0).replace(",", ".")) <= 0
    except ValueError:
        return False


def extract_compare_price(page_html, currency):
    patterns = [
        r'"compare_at_price"\s*:\s*(\d+)',
        r'"CompareAtPrice"\s*:\s*"([^"]+)"',
        r'CompareAtPrice:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(1)
        if value.isdigit():
            amount = int(value) / 100
            if amount <= 0:
                continue
            return format_price(f"{amount:.2f}", currency)
        normalized = normalize_price_text(value, currency)
        if normalized:
            return normalized
    return ""


def normalize_price_text(value, currency):
    value = clean_text(html_lib.unescape(str(value))).replace("kr", "").strip()
    if is_zero_price(value):
        return ""
    value = value.replace(".", ",")
    if currency and currency.upper() not in value.upper():
        return f"{value} {currency.upper()}"
    return value


def normalize_duckduckgo_url(href):
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        if query.get("uddg"):
            return query["uddg"][0]
    return href


def search_recipes(product):
    query = make_recipe_query(product)
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    html = fetch_url(url, timeout=10)
    parser = SearchResultParser()
    parser.feed(html)
    seen = set()
    results = []
    checked_candidates = 0
    for item in parser.results:
        host = urlparse(item["url"]).netloc.lower()
        key = item["url"].split("#", 1)[0]
        if (
            key in seen
            or "duckduckgo.com" in host
            or "bing.com" in host
            or "google." in host
            or "/products/" in urlparse(item["url"]).path
            or is_competitor_link(host)
        ):
            continue
        seen.add(key)
        checked_candidates += 1
        if checked_candidates > 3:
            break
        try:
            candidate_html = fetch_url(item["url"], timeout=6)
        except Exception:
            continue
        if not page_uses_product(candidate_html, host, product):
            continue
        results.append(item)
        if len(results) >= 4:
            break
    return results


def is_competitor_link(host):
    blocked_hosts = (
        "amazon.",
        "ebay.",
        "temu.",
        "aliexpress.",
        "ikea.",
        "clasohlson.",
        "obs.",
        "jula.",
        "kitchn.",
    )
    return any(blocked in host for blocked in blocked_hosts)


def product_identity_terms(product):
    title = re.sub(r"Tupperware|®|™", " ", product.get("title") or "", flags=re.IGNORECASE)
    words = normalize_search_text(title).split()
    generic = {
        "collection",
        "produkt",
        "product",
        "tupperware",
        "the",
        "for",
        "med",
        "uten",
        "manual",
        "manuell",
        "kitchen",
    }
    return [word for word in words if len(word) >= 4 and word not in generic]


def page_uses_product(page_html, host, product):
    page_text = normalize_search_text(html_to_text(page_html))
    if "tupperware" not in page_text and "tupperware" not in host:
        return False

    source_path = urlparse(product.get("sourceUrl") or "").path
    handle = normalize_search_text(source_path.rstrip("/").split("/")[-1])
    if handle.isdigit() and handle in page_text:
        return True

    terms = product_identity_terms(product)
    if not terms:
        return False
    matched_terms = {term for term in terms if term in page_text}
    required_matches = 1 if len(terms) == 1 else 2
    return len(matched_terms) >= required_matches


def make_recipe_query(product):
    terms = product_identity_terms(product)
    product_name = " ".join(terms[:5]) or clean_text(product.get("title") or "")
    return f'Tupperware "{product_name}" recipe tips'


def generate_recipe_content(recipe_name, consultant):
    recipe_name = clean_text(recipe_name)
    if not recipe_name:
        raise ValueError("Skriv inn navnet på en oppskrift.")
    source = find_recipe_source(recipe_name)
    details = extract_recipe_details(source["url"]) if source.get("url") else {}
    ingredients = details.get("ingredients") or []
    instructions = details.get("instructions") or fallback_instructions(recipe_name)
    recipe_image = details.get("image") or ""
    if details.get("title"):
        source["title"] = details["title"]
    if not ingredients:
        ingredients = fallback_ingredients(recipe_name)
    inspirations = find_tupperware_recipe_inspiration(recipe_name)
    product_needs = product_queries_for_recipe(recipe_name, ingredients, instructions, inspirations)
    products = find_tupperware_products(product_needs, consultant)
    products = add_product_use_tips(products, recipe_name, ingredients, instructions, inspirations)
    guided_instructions = build_guided_instructions(instructions, products, recipe_name)
    recipe = {
        "name": recipe_name,
        "title": source.get("title") or recipe_name.title(),
        "sourceUrl": source.get("url") or "",
        "image": recipe_image,
        "ingredients": ingredients,
        "instructions": instructions,
        "guidedInstructions": guided_instructions,
        "inspirations": inspirations,
        "products": products,
    }
    return {
        "mode": "recipe",
        "recipe": recipe,
        "email": make_recipe_email(recipe, consultant),
        "emailHtml": make_recipe_email_html(recipe, consultant),
    }


def find_recipe_source(recipe_name):
    for query in (f"site:matprat.no {recipe_name} oppskrift", f"{recipe_name} oppskrift ingredienser"):
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        html = fetch_url(url, timeout=15)
        parser = SearchResultParser()
        parser.feed(html)
        for item in parser.results:
            host = urlparse(item["url"]).netloc.lower()
            if "duckduckgo.com" in host or "bing.com" in host or "google." in host:
                continue
            if "matprat.no" in host or not query.startswith("site:matprat.no"):
                return item
    return {"title": recipe_name.title(), "url": ""}


def find_tupperware_recipe_inspiration(recipe_name):
    results = []
    seen = set()
    queries = [
        f"Tupperware {recipe_name} recipe products",
        f"site:tupperware.com {recipe_name} recipe",
        f"Tupperware avocado dip recipe" if "guac" in recipe_name.lower() else f"Tupperware {recipe_name} recipe",
    ]
    for query in queries:
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            html = fetch_url(url, timeout=15)
        except Exception:
            continue
        parser = SearchResultParser()
        parser.feed(html)
        for item in parser.results:
            host = urlparse(item["url"]).netloc.lower()
            if "duckduckgo.com" in host or "bing.com" in host or "google." in host:
                continue
            if "tupperware" not in (item["title"] + " " + item["url"]).lower():
                continue
            key = item["url"].split("#", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
            if len(results) >= 4:
                return results
    return results


def extract_recipe_ingredients(url):
    return extract_recipe_details(url).get("ingredients", [])


def extract_recipe_details(url):
    try:
        html = fetch_url(url, timeout=15)
    except Exception:
        return {}
    parser = MetadataParser()
    parser.feed(html)
    for block in parser.ld_json:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for node in walk_json(data):
            node_type = node.get("@type")
            is_recipe = "Recipe" in node_type if isinstance(node_type, list) else node_type == "Recipe"
            if is_recipe:
                ingredients = [clean_text(item) for item in node.get("recipeIngredient", []) if clean_text(item)]
                instructions = parse_recipe_instructions(node.get("recipeInstructions"))
                image = extract_recipe_image(node.get("image"))
                return {
                    "title": clean_text(node.get("name")),
                    "image": image,
                    "ingredients": ingredients[:14],
                    "instructions": instructions[:8],
                }
    return {}


def parse_recipe_instructions(value):
    steps = []
    if isinstance(value, str):
        steps = re.split(r"\s*(?:\d+\.|[\r\n]+)\s*", value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                steps.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("name")
                if text:
                    steps.append(text)
                elif isinstance(item.get("itemListElement"), list):
                    steps.extend(parse_recipe_instructions(item["itemListElement"]))
    elif isinstance(value, dict):
        steps.extend(parse_recipe_instructions(value.get("itemListElement") or value.get("text")))
    return [clean_text(step) for step in steps if clean_text(step)]


def extract_recipe_image(value):
    if isinstance(value, str):
        return normalize_image_url(value)
    if isinstance(value, list):
        for item in value:
            image = extract_recipe_image(item)
            if image:
                return image
    if isinstance(value, dict):
        return normalize_image_url(value.get("url") or value.get("contentUrl"))
    return ""


def fallback_ingredients(recipe_name):
    name = recipe_name.lower()
    if "guac" in name or "avokado" in name:
        return [
            "2 modne avokado",
            "1 lime",
            "1 liten tomat",
            "1/2 rødløk",
            "1 fedd hvitløk",
            "Frisk koriander",
            "Salt og pepper",
            "Litt chili eller jalapeño",
        ]
    return ["Hovedråvare", "Noe syrlig", "Krydder", "Friske urter", "Salt og pepper"]


def fallback_instructions(recipe_name):
    name = recipe_name.lower()
    if "guac" in name or "avokado" in name:
        return [
            "Del avokadoene, fjern steinene og mos fruktkjøttet med limesaft.",
            "Finhakk tomat, rødløk, hvitløk, chili og koriander.",
            "Bland alt forsiktig sammen og smak til med salt og pepper.",
            "Server med en gang, eller legg tett lokk på og oppbevar kjølig.",
        ]
    return [
        "Gjør klart ingrediensene.",
        "Kutt, bland og smak til.",
        "Server eller oppbevar i en tett boks.",
    ]


def product_queries_for_recipe(recipe_name, ingredients, instructions, inspirations=None):
    ingredient_text = " ".join(ingredients).lower()
    instruction_text = " ".join(instructions).lower()
    inspiration_text = " ".join(item.get("title", "") for item in (inspirations or [])).lower()
    all_text = " ".join((recipe_name, ingredient_text, instruction_text))
    needs = []

    chop_action = bool(
        re.search(r"\b(?:finhakk|hakk|kutt)\b", instruction_text)
        or re.search(r"\b(?:finhakket|hakket)\b", ingredient_text)
    )
    chop_foods = [
        label
        for label in ("løk", "hvitløk", "chili", "urter", "koriander", "nøtter", "grønnsaker")
        if label in all_text
    ]
    inspiration_uses_chopper = any(
        phrase in inspiration_text for phrase in ("quick chef", "chopper", "supersonic")
    )
    if (chop_action and chop_foods) or inspiration_uses_chopper:
        foods = ", ".join(chop_foods[:4]) or "ingrediensene som skal hakkes"
        needs.append(
            {
                "role": "chopper",
                "query": "SuperSonic Chopper",
                "reason": f"Passer til finhakking av {foods}. Bruk den bare på råvarene oppskriften faktisk ber deg hakke.",
            }
        )

    cut_action = bool(re.search(r"\b(?:skjær|del|kutt)\b", instruction_text))
    if cut_action:
        needs.append(
            {
                "role": "knife",
                "query": "kniv",
                "reason": "Passer til råvarene som oppskriften uttrykkelig ber deg dele eller skjære for hånd.",
            }
        )

    mix_steps = [
        step
        for step in instructions
        if re.search(r"\b(?:bland\w*|vend\w*|rør\w*)\b", step.lower())
        and not any(tool in step.lower() for tool in ("kjele", "gryte", "stekepanne"))
    ]
    if mix_steps:
        needs.append(
            {
                "role": "bowl",
                "query": "skål",
                "reason": "Passer til trinnet der ingrediensene skal blandes uten bruk av kjele eller stekepanne.",
            }
        )

    if any(word in instruction_text for word in ("vend", "skrap")):
        needs.append(
            {
                "role": "spatula",
                "query": "slikkepott",
                "reason": "Passer til å vende blandingen eller få med innhold fra bollen i trinnet som beskriver dette.",
            }
        )

    if re.search(r"\b\d+(?:[,.]\d+)?\s*(?:dl|ml|l)\b", ingredient_text):
        needs.append(
            {
                "role": "measure",
                "query": "målebeger",
                "reason": "Oppskriften inneholder væskemengder i dl, ml eller liter som skal måles opp.",
            }
        )

    if any(word in instruction_text for word in ("kjølig", "kjøleskap", "oppbevar", "dekk til")):
        needs.append(
            {
                "role": "storage",
                "query": "One Touch",
                "reason": "Oppskriften har et uttrykkelig trinn for tildekking eller kjølig oppbevaring.",
            }
        )

    return needs[:6]


def find_tupperware_products(needs, consultant):
    products = []
    seen = set()
    for need in needs:
        query = need["query"]
        search_url = consultant_url(f"https://tupperware-eu.com/no/search?q={quote_plus(query)}", consultant)
        try:
            html = fetch_url(search_url, timeout=15)
            product_url = find_product_url_from_search(search_url, html)
            if product_url and product_url not in seen:
                product = parse_product(product_url)
                if not product_matches_need(product, need["role"]):
                    continue
                product["recipeReason"] = need["reason"]
                product["recipeRole"] = need["role"]
                products.append(product)
                seen.add(product_url)
        except Exception:
            pass
        if len(products) >= 4:
            break
    return products


def product_matches_need(product, role):
    title = product.get("title", "").lower()
    role_words = {
        "chopper": ("hakke", "chopper", "supersonic", "quick chef"),
        "knife": ("kniv", "knife"),
        "bowl": ("skål", "bolle", "bowl"),
        "spatula": ("slikkepott", "spatel", "spatula"),
        "measure": ("måle", "measure", "mug"),
        "storage": ("oppbevaring", "boks", "beholder", "storage"),
    }
    return any(word in title for word in role_words.get(role, ()))


def add_product_use_tips(products, recipe_name, ingredients, instructions, inspirations=None):
    inspiration_text = " ".join(item.get("title", "") for item in (inspirations or []))
    full_text = " ".join([recipe_name, *ingredients, *instructions, inspiration_text]).lower()
    result = []
    for product in products:
        product = dict(product)
        title = product.get("title", "").lower()
        product["useTip"] = product.get("recipeReason") or product_use_tip(title, full_text)
        result.append(product)
    return result


def product_use_tip(title, recipe_text):
    if any(word in title for word in ("hakke", "chopper", "super sonic", "supersonic")):
        if "quick chef" in recipe_text or "guacamole" in recipe_text:
            return "Brukes slik Tupperware ofte viser i guacamole-oppskrifter: hakk løk, chili, hvitløk og urter raskt, og bland deretter med avokado."
        return "Brukes til å finhakke løk, chili, hvitløk og urter raskt og jevnt."
    if any(word in title for word in ("skål", "bolle", "server")):
        return "Brukes til å mose, blande og servere retten direkte på bordet."
    if any(word in title for word in ("slikkepott", "spatel", "sleiv")):
        return "Brukes til å vende ingrediensene forsiktig sammen og få med alt fra bollen."
    if any(word in title for word in ("oppbevaring", "boks", "beholder", "lokk")):
        return "Brukes til å oppbevare rester tett i kjøleskapet."
    if any(word in title for word in ("måle", "measure")):
        return "Brukes til å måle opp væske, krydder og andre ingredienser før du starter."
    if "guac" in recipe_text or "avokado" in recipe_text:
        return "Passer inn i forberedelse, blanding eller oppbevaring av guacamole."
    return "Passer som praktisk hjelp under forberedelse, servering eller oppbevaring."


def product_role(title):
    title = title.lower()
    if any(word in title for word in ("hakke", "chopper", "super sonic", "supersonic")):
        return "chopper"
    if any(word in title for word in ("slikkepott", "spatel", "sleiv")):
        return "spatula"
    if any(word in title for word in ("måle", "measure")):
        return "measure"
    if any(word in title for word in ("oppbevaring", "boks", "beholder")):
        return "storage"
    if any(word in title for word in ("skål", "bolle", "server")):
        return "bowl"
    return "other"


def build_guided_instructions(instructions, products, recipe_name):
    products_by_role = {}
    for product in products:
        role = product_role(product.get("title", ""))
        if role == "other":
            continue
        if role == "storage" and role in products_by_role:
            current_size = product_capacity_litres(products_by_role[role].get("title", ""))
            candidate_size = product_capacity_litres(product.get("title", ""))
            if candidate_size < current_size:
                products_by_role[role] = product
        elif role not in products_by_role:
            products_by_role[role] = product

    is_guacamole = "guac" in recipe_name.lower() or "avokado" in recipe_name.lower()
    guided = []
    for step in instructions:
        step_text = clean_text(step)
        lower = step_text.lower()
        uses = []
        used_titles = set()

        def add_use(role, message):
            product = products_by_role.get(role)
            if not product or product.get("title") in used_titles:
                return
            title = product.get("title", "Tupperware-produkt")
            used_titles.add(title)
            uses.append({"productTitle": title, "text": message.format(title=title)})

        chop_action = bool(
            re.search(r"\b(?:finhakk|kutt)\b", lower)
            or (re.search(r"\bhakk\b", lower) and "kniven" not in lower)
        )
        storage_action = any(word in lower for word in ("kjølig", "kjøleskap", "oppbevar", "dekk til", "lokk"))
        named_equipment = any(
            word in lower
            for word in ("foodprosessor", "stavmikser", "potetmoser", "stekepanne", "kjele", "gryte")
        )

        if is_guacamole:
            if chop_action and "tomat" in lower:
                add_use(
                    "chopper",
                    "Skjær tomaten i terninger for hånd som beskrevet. Bruk {title} bare til hvitløk, chili og eventuelle urter, så tomaten ikke blir most.",
                )
            elif chop_action:
                add_use("chopper", "Bruk {title} til finhakkingen, og stopp mens du fortsatt har ønsket konsistens.")

            if re.search(r"\bmos\b", lower):
                add_use(
                    "bowl",
                    "Mos avokadoen med en gaffel direkte i {title}. Da beholder du kontroll på hvor grov konsistensen blir.",
                )

            if any(word in lower for word in ("bland", "vend", "rør")):
                if "spatula" in products_by_role:
                    add_use("spatula", "Bruk {title} til å vende ingrediensene sammen uten å arbeide blandingen mer enn nødvendig.")
                else:
                    add_use("bowl", "Bland ingrediensene i {title}, som også kan brukes til servering.")

            if storage_action:
                add_use("storage", "Legg ferdig rett i {title}, lukk tett og sett den kjølig frem til servering.")

        else:
            if chop_action and not named_equipment:
                add_use(
                    "chopper",
                    "Bruk {title} bare til ingrediensene som skal finhakkes i dette trinnet. Følg oppskriftens øvrige redskaper og metode.",
                )
            mix_action = bool(re.search(r"\b(?:bland\w*|vend\w*|rør\w*)\b", lower))
            if mix_action and "for hånd" in lower:
                add_use(
                    "bowl",
                    "Hvis du velger oppskriftens alternativ med håndblanding, kan du bruke {title}. Dette erstatter ikke foodprosessoren dersom du velger maskinmetoden.",
                )
            elif mix_action and not named_equipment:
                add_use(
                    "bowl",
                    "Bruk {title} til blandingen i dette trinnet. Behold oppskriftens angitte kjele, panne eller maskin der slike redskaper er nevnt.",
                )
            if storage_action:
                add_use(
                    "storage",
                    "Bruk {title} til oppbevaring bare dersom størrelse og temperatur passer maten i dette trinnet.",
                )

        guided.append({"text": step_text, "productUses": uses})
    return guided


def product_capacity_litres(title):
    match = re.search(r"(\d+(?:[,.]\d+)?)\s*l\b", title.lower())
    if not match:
        return float("inf")
    return float(match.group(1).replace(",", "."))


def consultant_url(product_url, consultant):
    consultant = clean_text(consultant) or "ref=LISBETHOVERBYE"
    if consultant.startswith("http://") or consultant.startswith("https://"):
        return consultant
    parsed = urlparse(product_url)
    query = parse_qs(parsed.query)
    if "=" in consultant:
        key, value = consultant.split("=", 1)
    else:
        key, value = "consultant", consultant
    query[key.strip()] = [value.strip()]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def make_email(product, recipes, consultant):
    product = sanitize_product_prices(dict(product))
    link = consultant_url(product["sourceUrl"], consultant)
    recipe_lines = ""
    if recipes:
        recipe_lines = "\n\nOppskrifter som kan passe til produktet:\n" + "\n".join(
            f"- {item['title']}: {item['url']}" for item in recipes[:4]
        )

    description = product.get("description") or "Dette er et praktisk Tupperware-produkt som passer godt inn i hverdagen."
    if product.get("isSale") and product.get("comparePrice"):
        price = f"\nTilbud: før {product['comparePrice']} - nå {product['price']}"
    else:
        price = f"\nPris: {product['price']}" if product.get("price") else ""
    return clean_text_block(
        f"""Hei!

Jeg vil gjerne tipse deg om {product['title']}.

{description}{price}

Du kan se produktet og bestille via min konsulentlenke her:
{link}{recipe_lines}

Du kan sende meg en e-post med hva du ønsker å bestille, så bestiller jeg det for deg.

Frakt kan komme i tillegg, og vi velger alltid den rimeligste fraktmåten. Det kan også hende at vi har produktet på lager i Norge. Da kan du få det raskere.

Vennlig hilsen"""
    )


def make_recipe_email(recipe, consultant):
    ingredient_lines = "\n".join(f"- {item}" for item in recipe.get("ingredients", []))
    guided = recipe.get("guidedInstructions") or [
        {"text": item, "productUses": []} for item in recipe.get("instructions", [])
    ]
    instruction_parts = []
    for index, item in enumerate(guided):
        instruction_parts.append(f"{index + 1}. {item['text']}")
        for use in item.get("productUses", []):
            instruction_parts.append(f"   Tupperware i dette trinnet: {use['text']}")
    instruction_lines = "\n".join(instruction_parts)
    product_lines = "\n".join(
        f"- {item['title']}: {item.get('useTip', 'Passer godt til oppskriften.')}\n  {consultant_url(item['sourceUrl'], consultant)}"
        for item in recipe.get("products", [])
    )
    inspiration_lines = "\n".join(
        f"- {item['title']}: {item['url']}" for item in recipe.get("inspirations", [])[:3]
    )
    inspiration_block = f"\n\nTupperware-inspirasjon:\n{inspiration_lines}" if inspiration_lines else ""
    source = f"\nOppskrift fra: {recipe.get('title') or recipe['sourceUrl']}\n{recipe['sourceUrl']}" if recipe.get("sourceUrl") else ""
    return clean_text_block(
        f"""Hei!

Her er et lite tips til {recipe['name']}.

Ingredienser:
{ingredient_lines}

Fremgangsmåte:
{instruction_lines}

Tupperware-produkter som passer godt:
{product_lines or "- En god skål, hakker og oppbevaringsboks gjør jobben enklere."}{inspiration_block}{source}

Du kan sende meg en e-post med hva du ønsker å bestille, så bestiller jeg det for deg.

Frakt kan komme i tillegg, og vi velger alltid den rimeligste fraktmåten. Det kan også hende at vi har produktet på lager i Norge. Da kan du få det raskere.

Vennlig hilsen"""
    )


def make_recipe_email_html(recipe, consultant):
    title = html_lib.escape(recipe.get("name", "Oppskrift").title())
    recipe_image = html_lib.escape(recipe.get("image") or "")
    ingredients = "".join(
        f"<li style=\"margin:0 0 7px;\">{html_lib.escape(item)}</li>"
        for item in recipe.get("ingredients", [])
    )
    guided = recipe.get("guidedInstructions") or [
        {"text": item, "productUses": []} for item in recipe.get("instructions", [])
    ]
    instructions = "".join(
        f"<li style=\"margin:0 0 14px;\">{html_lib.escape(item['text'])}"
        + "".join(
            f'<div style="margin-top:7px;padding:9px 11px;background:#ffffff;border-left:4px solid #ef7b45;color:#4d4944;font-size:14px;"><strong>Tupperware i dette trinnet:</strong> {html_lib.escape(use["text"])}</div>'
            for use in item.get("productUses", [])
        )
        + "</li>"
        for item in guided
    )
    product_cards = "".join(
        recipe_product_card(product, consultant) for product in recipe.get("products", [])
    )
    inspiration_links = "".join(
        f"""<li style="margin:0 0 7px;"><a href="{html_lib.escape(item['url'])}" target="recipe-source" style="color:#006b5f;font-weight:800;">{html_lib.escape(item['title'])}</a></li>"""
        for item in recipe.get("inspirations", [])[:3]
    )
    source_link = ""
    if recipe.get("sourceUrl"):
        source_label = "Oppskrift fra MatPrat" if "matprat.no" in recipe["sourceUrl"] else "Oppskrift fra"
        source_link = f"""<p style="font-size:13px;color:#6b655f;margin:18px 0 0;">{source_label}:
          <a href="{html_lib.escape(recipe['sourceUrl'])}" target="recipe-source" style="color:#006b5f;font-weight:800;">{html_lib.escape(recipe.get('title') or recipe['sourceUrl'])}</a>
        </p>"""
    hero = f'<img src="{recipe_image}" alt="{title}" style="width:100%;max-height:360px;object-fit:cover;display:block;">' if recipe_image else ""
    return clean_text_block(
        f"""
<div style="margin:0;padding:24px;background:#f6f3ee;font-family:Segoe UI,Arial,sans-serif;color:#252422;">
  <div style="max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #d9d1c7;border-radius:18px;overflow:hidden;">
    {hero}
    <div style="background:#006b5f;color:#ffffff;padding:28px;">
      <div style="font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">Oppskrift + Tupperware-tips</div>
      <h1 style="font-size:34px;line-height:1.08;margin:0;">{title}</h1>
      <p style="font-size:16px;line-height:1.5;margin:12px 0 0;color:#eaf6f3;">Gjør matlagingen enklere med riktig utstyr til kutting, blanding, servering og oppbevaring.</p>
    </div>
    <div style="padding:26px;">
      <div style="background:#fff7e8;border:1px solid #f1d4a3;border-radius:14px;padding:18px;margin-bottom:22px;">
        <h2 style="font-size:20px;margin:0 0 12px;color:#252422;">Ingredienser</h2>
        <ul style="margin:0;padding-left:20px;font-size:15px;line-height:1.45;">{ingredients}</ul>
      </div>
      <div style="background:#eef7f5;border:1px solid #b8d8d2;border-radius:14px;padding:18px;margin-bottom:22px;">
        <h2 style="font-size:20px;margin:0 0 12px;color:#252422;">Fremgangsmåte</h2>
        <ol style="margin:0;padding-left:20px;font-size:15px;line-height:1.45;">{instructions}</ol>
      </div>
      <h2 style="font-size:22px;margin:0 0 12px;color:#252422;">Produkter som passer</h2>
      <div>{product_cards or '<p>En god skål, hakker og oppbevaringsboks gjør jobben enklere.</p>'}</div>
      {f'<div style="background:#f6f3ee;border-radius:14px;padding:18px;margin-top:18px;"><h2 style="font-size:18px;margin:0 0 10px;color:#252422;">Tupperware-inspirasjon</h2><ul style="margin:0;padding-left:20px;">{inspiration_links}</ul></div>' if inspiration_links else ''}
      {source_link}
      <p style="font-size:15px;line-height:1.5;margin:24px 0 0;color:#4d4944;"><strong>Vil du bestille?</strong> Du kan sende meg en e-post med hva du ønsker, så bestiller jeg det for deg.</p>
      <p style="font-size:14px;line-height:1.5;margin:12px 0 0;color:#6b655f;">Frakt kan komme i tillegg, og vi velger alltid den rimeligste fraktmåten. Det kan også hende at vi har produktet på lager i Norge. Da kan du få det raskere.</p>
      <p style="font-size:15px;line-height:1.5;margin:18px 0 0;color:#4d4944;">Vennlig hilsen</p>
    </div>
  </div>
</div>"""
    )


def recipe_product_card(product, consultant):
    product = sanitize_product_prices(dict(product))
    title = html_lib.escape(product.get("title") or "Tupperware-produkt")
    english_title = html_lib.escape(product.get("englishTitle") or "")
    image = html_lib.escape(product.get("image") or "")
    price = html_lib.escape(product.get("price") or "")
    use_tip = html_lib.escape(product.get("useTip") or "")
    link = html_lib.escape(consultant_url(product.get("sourceUrl") or "", consultant))
    img = f'<img src="{image}" alt="{title}" style="width:96px;height:96px;object-fit:contain;background:#f8f8f8;border-radius:10px;border:1px solid #d9d1c7;">' if image else ""
    price_line = f'<div style="font-weight:800;color:#006b5f;margin-top:4px;">{price}</div>' if price else ""
    english_line = f'<div style="font-size:13px;line-height:1.35;color:#6b655f;margin-top:3px;">Engelsk navn: {english_title}</div>' if english_title else ""
    use_line = f'<div style="font-size:14px;line-height:1.4;color:#6b655f;margin-top:5px;">{use_tip}</div>' if use_tip else ""
    return f"""
      <div style="display:flex;gap:14px;align-items:center;border:1px solid #d9d1c7;border-radius:14px;padding:12px;margin:0 0 10px;">
        {img}
        <div style="min-width:0;">
          <div style="font-size:16px;font-weight:900;line-height:1.25;color:#252422;">{title}</div>
          {english_line}
          {price_line}
          {use_line}
          <a href="{link}" target="tupperware-shop" style="display:inline-block;margin-top:8px;color:#006b5f;font-weight:800;text-decoration:underline;">Se produkt</a>
        </div>
      </div>"""


def make_email_html(product, recipes, consultant):
    product = sanitize_product_prices(dict(product))
    link = consultant_url(product["sourceUrl"], consultant)
    title = html_lib.escape(product.get("title") or "Tupperware-produkt")
    english_title = html_lib.escape(product.get("englishTitle") or "")
    english_title_line = (
        f'<div style="font-size:14px;line-height:1.4;color:#6b655f;margin:-7px 0 14px;">Engelsk navn: {english_title}</div>'
        if english_title
        else ""
    )
    description = html_lib.escape(
        product.get("description")
        or "Et praktisk Tupperware-produkt som passer godt inn i hverdagen."
    )
    price = html_lib.escape(product.get("price") or "")
    compare_value = product.get("comparePrice") or ""
    compare_price = "" if is_zero_price(compare_value) else html_lib.escape(compare_value)
    images = product.get("images") or ([product.get("image")] if product.get("image") else [])
    hero_image = html_lib.escape(images[0]) if images else ""
    image_cells = "".join(
        f"""
        <td style="width:33.33%;padding:4px;">
          <img src="{html_lib.escape(src)}" alt="" style="width:100%;height:120px;object-fit:cover;border-radius:10px;border:1px solid #d9d1c7;display:block;">
        </td>"""
        for src in images[1:4]
    )
    recipe_items = "".join(
        f"""
        <li style="margin:0 0 8px;">
          <a href="{html_lib.escape(item['url'])}" target="recipe-source" style="color:#006b5f;text-decoration:underline;font-weight:700;">{html_lib.escape(item['title'])}</a>
        </li>"""
        for item in recipes[:4]
    )
    gallery = ""
    if image_cells:
        gallery = f"""
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:12px 0 2px;">
          <tr>{image_cells}</tr>
        </table>"""
    recipes_block = ""
    if recipe_items:
        recipes_block = f"""
        <div style="background:#f6f3ee;border-radius:14px;padding:18px;margin-top:22px;">
          <h2 style="font-size:18px;line-height:1.25;margin:0 0 12px;color:#252422;">Oppskrifter og tips</h2>
          <ul style="padding-left:20px;margin:0;color:#252422;">{recipe_items}</ul>
        </div>"""
    hero = ""
    if hero_image:
        hero = f"""
        <img src="{hero_image}" alt="{title}" style="width:100%;max-height:380px;object-fit:contain;background:#f8f8f8;border-radius:18px 18px 0 0;display:block;">"""
    if product.get("isSale") and compare_price and price:
        price_badge = f"""
        <div style="margin:4px 0 20px;">
          <div style="display:inline-block;background:#d8603c;color:#ffffff;font-size:13px;font-weight:900;border-radius:999px;padding:7px 11px;margin:0 0 8px;text-transform:uppercase;">Tilbud</div>
          <div style="font-size:15px;color:#7b746d;margin-bottom:3px;">Før: <span style="text-decoration:line-through;">{compare_price}</span></div>
          <div style="font-size:30px;line-height:1.1;color:#006b5f;font-weight:900;">Nå: {price}</div>
        </div>"""
    else:
        price_badge = f"""
        <div style="display:inline-block;background:#fff0ea;color:#8a351d;font-weight:800;border-radius:999px;padding:8px 13px;margin:4px 0 18px;">
          Pris: {price}
        </div>""" if price else ""
    return clean_text_block(
        f"""
<div style="margin:0;padding:24px;background:#f6f3ee;font-family:Segoe UI,Arial,sans-serif;color:#252422;">
  <div style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #d9d1c7;border-radius:18px;overflow:hidden;">
    {hero}
    <div style="padding:26px;">
      <div style="color:#006b5f;font-size:13px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin-bottom:8px;">Tupperware-tips</div>
      <h1 style="font-size:30px;line-height:1.08;margin:0 0 14px;color:#252422;">{title}</h1>
      {english_title_line}
      {price_badge}
      <p style="font-size:16px;line-height:1.55;margin:0 0 20px;color:#4d4944;">{description}</p>
      <a href="{html_lib.escape(link)}" target="tupperware-shop" style="display:inline-block;background:#006b5f;color:#ffffff;text-decoration:none;font-weight:800;border-radius:10px;padding:13px 18px;">Se produktet og bestill</a>
      {gallery}
      {recipes_block}
      <p style="font-size:15px;line-height:1.5;margin:24px 0 0;color:#4d4944;"><strong>Vil du bestille?</strong> Du kan sende meg en e-post med hva du ønsker, så bestiller jeg det for deg.</p>
      <p style="font-size:14px;line-height:1.5;margin:12px 0 0;color:#6b655f;">Frakt kan komme i tillegg, og vi velger alltid den rimeligste fraktmåten. Det kan også hende at vi har produktet på lager i Norge. Da kan du få det raskere.</p>
      <p style="font-size:15px;line-height:1.5;margin:18px 0 0;color:#4d4944;">Vennlig hilsen</p>
    </div>
  </div>
</div>"""
    )


def clean_text_block(value):
    lines = [line.rstrip() for line in value.splitlines()]
    compact = []
    blank = False
    for line in lines:
        if line:
            compact.append(line)
            blank = False
        elif not blank:
            compact.append("")
            blank = True
    return "\n".join(compact).strip()


def format_error(error):
    text = clean_text(str(error))
    if text:
        return text
    return f"{error.__class__.__name__}: {repr(error)}"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        request_url = urlparse(self.path)
        if request_url.path in ("/", "/index.html"):
            self.respond(200, INDEX_HTML, "text/html; charset=utf-8")
            return
        if request_url.path == "/api/catalog":
            try:
                catalog = load_french_catalog()
                self.respond_json(
                    200,
                    {
                        "products": [
                            {
                                "articleNumber": item["articleNumber"],
                                "title": item["title"],
                                "price": item["price"],
                                "image": item["image"],
                                "availability": item["availability"],
                            }
                            for item in catalog
                        ]
                    },
                )
            except Exception as error:
                self.respond_json(500, {"error": f"Kunne ikke hente den franske produktlisten: {format_error(error)}"})
            return
        if request_url.path == "/api/catalog/search":
            try:
                query = clean_text((parse_qs(request_url.query).get("q") or [""])[0])
                matches = search_french_catalog_products(query)
                self.respond_json(
                    200,
                    {
                        "products": [
                            {
                                "articleNumber": item["articleNumber"],
                                "title": item["title"],
                                "price": item["price"],
                                "image": item["image"],
                                "availability": item["availability"],
                            }
                            for item in matches
                        ]
                    },
                )
            except Exception as error:
                self.respond_json(500, {"error": f"Kunne ikke søke i produktlisten: {format_error(error)}"})
            return
        self.respond_json(404, {"error": "Fant ikke siden."})

    def do_POST(self):
        if self.path not in ("/api/generate", "/api/product-recipes"):
            self.respond_json(404, {"error": "Fant ikke endepunktet."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_payload = self.rfile.read(length)
            try:
                payload_text = raw_payload.decode("utf-8")
            except UnicodeDecodeError:
                payload_text = raw_payload.decode("cp1252")
            payload = json.loads(payload_text)
            if self.path == "/api/product-recipes":
                product = sanitize_product_prices(dict(payload.get("product") or {}))
                consultant = clean_text(payload.get("consultant"))
                if not product.get("sourceUrl") or not product.get("title"):
                    raise ValueError("Mangler produktdata for oppskriftssøket.")
                try:
                    recipes = search_recipes(product)
                except Exception:
                    recipes = []
                self.respond_json(
                    200,
                    {
                        "product": product,
                        "recipes": recipes,
                        "email": make_email(product, recipes, consultant),
                        "emailHtml": make_email_html(product, recipes, consultant),
                    },
                )
                return
            mode = clean_text(payload.get("mode") or "product")
            if mode == "recipe":
                result = generate_recipe_content(clean_text(payload.get("recipeName")), clean_text(payload.get("consultant")))
                self.respond_json(200, result)
                return
            product_url = clean_text(payload.get("productUrl"))
            product_query = clean_text(payload.get("productQuery"))
            consultant = clean_text(payload.get("consultant"))
            if product_query:
                product_url = resolve_product_reference(product_query, consultant)
            elif not product_url.startswith(("http://", "https://")):
                raise ValueError("Skriv inn artikkelnummer eller produktnavn, eller lim inn en gyldig produktlenke.")
            product = parse_product(product_url)
            if not product.get("title"):
                raise ValueError("Fant ikke produktnavn på siden.")
            product["sourceUrl"] = consultant_url(product.get("sourceUrl") or product_url, consultant)
            recipes = []
            email = make_email(product, recipes, consultant)
            email_html = make_email_html(product, recipes, consultant)
            self.respond_json(200, {"product": product, "recipes": recipes, "email": email, "emailHtml": email_html})
        except (ValueError, HTTPError, URLError, socket.timeout) as error:
            self.respond_json(400, {"error": format_error(error)})
        except Exception as error:
            traceback.print_exc()
            self.respond_json(500, {"error": f"Noe gikk galt: {format_error(error)}"})

    def respond(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def respond_json(self, status, payload):
        self.respond(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def log_message(self, fmt, *args):
        return


INDEX_HTML = r"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tupperware mailverktøy</title>
  <style>
    :root {
      --bg: #f7f5f0;
      --panel: #ffffff;
      --ink: #252422;
      --muted: #69655f;
      --line: #d9d1c7;
      --brand: #006b5f;
      --brand-strong: #004c45;
      --accent: #d8603c;
      --gold: #f1b94b;
      --soft: #eef7f5;
      font-family: "Segoe UI", Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(216,96,60,.18), transparent 32rem),
        linear-gradient(135deg, #f7f5f0 0%, #eef7f5 54%, #fff6e3 100%);
      color: var(--ink);
    }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 20px;
      margin-bottom: 22px;
      border: 1px solid rgba(0,107,95,.18);
      border-radius: 12px;
      padding: 18px;
      background: rgba(255,255,255,.78);
      box-shadow: 0 18px 45px rgba(37,36,34,.08);
    }
    h1 {
      margin: 0;
      font-size: clamp(28px, 5vw, 46px);
      line-height: 1.02;
      letter-spacing: 0;
    }
    .tagline {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 16px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(300px, 420px) 1fr;
      gap: 18px;
      align-items: start;
    }
    section, aside {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 14px 35px rgba(37,36,34,.07);
    }
    .controls { padding: 18px; }
    label {
      display: block;
      font-weight: 700;
      margin: 16px 0 6px;
    }
    .mode-tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 14px;
    }
    .mode-tab {
      background: var(--soft);
      color: var(--brand-strong);
      border: 1px solid #b8d8d2;
    }
    .mode-tab.active {
      background: var(--brand);
      color: #fff;
      border-color: var(--brand);
    }
    .hidden {
      display: none;
    }
    label:first-child { margin-top: 0; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 11px 12px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }
    select { min-height: 44px; }
    textarea {
      min-height: 360px;
      resize: vertical;
      line-height: 1.45;
    }
    .hint {
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
    }
    .catalog-results {
      margin-top: 8px;
      max-height: 430px;
      overflow-y: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .catalog-results.hidden { display: none; }
    .catalog-result-count {
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    button.catalog-result {
      width: 100%;
      min-height: 76px;
      display: grid;
      grid-template-columns: 58px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      border-radius: 0;
      background: #fff;
      color: var(--ink);
      text-align: left;
      font-weight: 400;
    }
    button.catalog-result:last-child { border-bottom: 0; }
    button.catalog-result:hover { background: var(--soft); }
    button.catalog-result.selected {
      background: var(--soft);
      box-shadow: inset 4px 0 0 var(--brand);
    }
    .catalog-result img,
    .catalog-result-image {
      width: 58px;
      height: 58px;
      object-fit: contain;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f8f8f8;
    }
    .catalog-result-image {
      display: grid;
      place-items: center;
      color: var(--muted);
      font-size: 11px;
    }
    .catalog-result strong {
      display: block;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }
    .catalog-result-number {
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }
    .catalog-result-price {
      color: var(--brand-strong);
      font-weight: 900;
      white-space: nowrap;
    }
    .catalog-result-meta {
      display: grid;
      justify-items: end;
      gap: 7px;
    }
    .availability {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }
    .availability::before {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: #8c8c8c;
      content: "";
    }
    .availability.available::before { background: #16834b; }
    .availability.unavailable::before { background: #c53b32; }
    .availability.unknown::before { background: #8c8c8c; }
    .actions {
      display: flex;
      gap: 10px;
      margin-top: 16px;
      flex-wrap: wrap;
    }
    button, a.button {
      border: 0;
      border-radius: 6px;
      padding: 11px 14px;
      font: inherit;
      font-weight: 800;
      cursor: pointer;
      background: var(--brand);
      color: #fff;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
    }
    button:hover, a.button:hover {
      background: var(--brand-strong);
    }
    button.secondary {
      background: var(--soft);
      color: var(--brand-strong);
      border: 1px solid #b8d8d2;
    }
    button:disabled { opacity: .65; cursor: wait; }
    .result {
      display: grid;
      grid-template-columns: 240px 1fr;
      gap: 18px;
      padding: 18px;
      min-height: 290px;
    }
    .image-box {
      aspect-ratio: 1;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8f8f8;
      display: grid;
      place-items: center;
      overflow: hidden;
    }
    .image-box img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .gallery {
      display: grid;
      gap: 10px;
    }
    .thumbs {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(52px, 1fr));
      gap: 8px;
    }
    .thumb {
      aspect-ratio: 1;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0;
      background: #fff;
      overflow: hidden;
      min-height: 52px;
    }
    .thumb.active {
      border: 2px solid var(--brand);
    }
    .thumb img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .empty {
      color: var(--muted);
      padding: 22px;
      text-align: center;
    }
    h2 {
      margin: 0 0 8px;
      font-size: 24px;
      letter-spacing: 0;
    }
    .english-product-name {
      margin: -2px 0 10px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.4;
    }
    .price {
      display: inline-block;
      margin: 2px 0 12px;
      padding: 6px 9px;
      border-radius: 6px;
      background: #fff0ea;
      color: #7f321d;
      font-weight: 800;
    }
    .sale-price {
      display: inline-grid;
      gap: 4px;
      margin: 2px 0 14px;
      padding: 10px 12px;
      border-radius: 8px;
      background: #fff0ea;
      border: 1px solid #f2c2b2;
    }
    .sale-label {
      width: fit-content;
      border-radius: 999px;
      background: var(--accent);
      color: #fff;
      font-size: 12px;
      font-weight: 900;
      padding: 4px 8px;
      text-transform: uppercase;
    }
    .before-price {
      color: var(--muted);
      font-size: 14px;
    }
    .before-price span {
      text-decoration: line-through;
    }
    .now-price {
      color: var(--brand);
      font-size: 24px;
      font-weight: 900;
      line-height: 1.1;
    }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .description {
      color: var(--muted);
      line-height: 1.5;
      margin: 0 0 16px;
    }
    .recipes {
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: 14px;
    }
    .recipes h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .recipes a {
      color: var(--brand-strong);
      display: block;
      margin: 8px 0;
      line-height: 1.35;
      word-break: break-word;
    }
    .ingredients-list {
      margin: 10px 0 16px;
      padding-left: 20px;
      color: var(--muted);
      line-height: 1.45;
    }
    .instructions-list {
      margin: 10px 0 16px;
      padding-left: 20px;
      color: var(--muted);
      line-height: 1.45;
    }
    .source-link {
      display: inline-block;
      margin: 4px 0 14px;
      color: var(--brand-strong);
      font-weight: 800;
      word-break: break-word;
    }
    .product-mini {
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 12px;
      align-items: center;
      border-top: 1px solid var(--line);
      padding: 12px 0;
    }
    .product-mini img {
      width: 72px;
      height: 72px;
      object-fit: contain;
      background: #f8f8f8;
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .product-mini strong {
      display: block;
      line-height: 1.25;
    }
    .use-tip {
      display: block;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
      margin: 4px 0;
    }
    .recipe-photo img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .mail-panel {
      margin-top: 18px;
      padding: 18px;
    }
    .mail-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }
    .mail-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .mail-grid {
      display: grid;
      grid-template-columns: minmax(280px, .9fr) minmax(320px, 1.1fr);
      gap: 16px;
      align-items: start;
    }
    .mail-preview {
      min-height: 360px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f6f3ee;
      overflow: auto;
      padding: 12px;
    }
    .mail-preview-empty {
      min-height: 334px;
      display: grid;
      place-items: center;
      color: var(--muted);
      text-align: center;
      padding: 18px;
    }
    .field-title {
      display: block;
      font-weight: 800;
      margin: 0 0 8px;
    }
    .status {
      margin-top: 12px;
      min-height: 20px;
      color: var(--accent);
      font-weight: 700;
    }
    @media print {
      body { background: #fff !important; }
      body > main > *:not(.mail-panel) { display: none !important; }
      .mail-panel { display: block !important; margin: 0 !important; padding: 0 !important; border: 0 !important; box-shadow: none !important; }
      .mail-head, .mail-grid > div:first-child { display: none !important; }
      .mail-grid { display: block !important; }
      .mail-preview { border: 0 !important; padding: 0 !important; overflow: visible !important; background: #fff !important; }
    }
    @media (max-width: 860px) {
      .layout, .result, .mail-grid { grid-template-columns: 1fr; }
      header { display: block; }
      .image-box { max-width: 340px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Tupperware mailverktøy</h1>
        <p class="tagline">Skriv inn artikkelnummer, produktnavn eller produktlenke og få et ferdig mailutkast.</p>
      </div>
    </header>

    <div class="layout">
      <aside class="controls">
        <div class="mode-tabs" role="group" aria-label="Velg type mail">
          <button id="modeProduct" class="mode-tab active" type="button">Produkt</button>
          <button id="modeRecipe" class="mode-tab" type="button">Oppskrift</button>
        </div>

        <div id="productFields">
          <label for="productQuery">Norsk søkeord, artikkelnummer eller produktnavn</label>
          <input id="productQuery" placeholder="F.eks. hakke, oppbevaring, 11174474 eller Chopper">
          <p class="hint">La feltet stå tomt for å vise alle produkter. Norske ord matches mot produktnavn og beskrivelser.</p>

          <label id="productCatalogLabel">Velg produkt</label>
          <div id="productCatalog" class="catalog-results" aria-labelledby="productCatalogLabel" aria-live="polite">
            <div class="catalog-result-count">Laster alfabetisk produktliste ...</div>
          </div>
          <p id="catalogHint" class="hint">Norske produktnavn brukes først, med engelske navn som reserve.</p>

          <label for="productUrl">Produktlenke (valgfritt)</label>
          <input id="productUrl" placeholder="Lim inn en full produktlenke hvis du allerede har den">
        </div>

        <div id="recipeFields" class="hidden">
          <label for="recipeName">Oppskrift</label>
          <input id="recipeName" value="guacamole" placeholder="F.eks. guacamole, tacodip, pastasalat">
          <p class="hint">Programmet finner ingredienser og foreslår Tupperware-produkter som passer til oppskriften.</p>
        </div>

        <label for="consultant">Din konsulentlenke eller kode</label>
        <input id="consultant" value="ref=LISBETHOVERBYE" placeholder="F.eks. ref=LISBETHOVERBYE">
        <p class="hint">Hvis du limer inn en full lenke brukes den i mailen. Hvis du skriver en kode, legges den til produktlenken som sporingsparameter.</p>

        <div class="actions">
          <button id="generate">Lag mailinnhold</button>
          <button id="clear" class="secondary">Tøm</button>
        </div>
        <div id="status" class="status"></div>
      </aside>

      <section class="result" id="result">
        <div class="image-box"><div class="empty">Produktbildet vises her</div></div>
        <div>
          <h2>Produktinfo</h2>
          <p class="description">Når du trykker på knappen, henter programmet navn, bilde, tekst og pris fra lenken.</p>
        </div>
      </section>
    </div>

    <section class="mail-panel">
      <div class="mail-head">
        <h2>Mailinnhold</h2>
        <div class="mail-actions">
          <button id="copyHtml">Kopier til e-post</button>
          <button id="copy" class="secondary">Kopier ren tekst</button>
          <button id="downloadPdf" class="secondary">Last ned PDF</button>
        </div>
      </div>
      <div class="mail-grid">
        <div>
          <span class="field-title">Ren tekst</span>
          <textarea id="email" placeholder="Ferdig mailtekst kommer her"></textarea>
        </div>
        <div>
          <div id="emailPreview" class="mail-preview"><div class="mail-preview-empty">Forhåndsvisning av designmailen kommer her</div></div>
        </div>
      </div>
    </section>
  </main>

  <script>
    const productCatalog = document.querySelector("#productCatalog");
    const catalogHint = document.querySelector("#catalogHint");
    const productQuery = document.querySelector("#productQuery");
    const productUrl = document.querySelector("#productUrl");
    const recipeName = document.querySelector("#recipeName");
    const consultant = document.querySelector("#consultant");
    const generate = document.querySelector("#generate");
    const clear = document.querySelector("#clear");
    const modeProduct = document.querySelector("#modeProduct");
    const modeRecipe = document.querySelector("#modeRecipe");
    const productFields = document.querySelector("#productFields");
    const recipeFields = document.querySelector("#recipeFields");
    const status = document.querySelector("#status");
    const result = document.querySelector("#result");
    const email = document.querySelector("#email");
    const emailPreview = document.querySelector("#emailPreview");
    const copy = document.querySelector("#copy");
    const copyHtml = document.querySelector("#copyHtml");
    let currentEmailHtml = "";
    let currentProductTitle = "Tupperware-tilbud";
    let currentMode = "product";
    let catalogSearchTimer = 0;
    let catalogSearchRequest = 0;
    let generationRequest = 0;

    function setStatus(message, isError = false) {
      status.textContent = message;
      status.style.color = isError ? "#b54228" : "#006b5f";
    }

    async function loadProductCatalog() {
      await searchProductCatalog("");
    }

    async function searchProductCatalog(query) {
      const requestNumber = ++catalogSearchRequest;
      const normalizedQuery = query.trim();
      try {
        const endpoint = normalizedQuery
          ? `/api/catalog/search?q=${encodeURIComponent(normalizedQuery)}`
          : "/api/catalog";
        const response = await fetch(endpoint);
        const data = await response.json();
        if (requestNumber !== catalogSearchRequest) return;
        if (!response.ok) throw new Error(data.error || "Søket mislyktes.");
        const products = data.products || [];
        if (!products.length) {
          productCatalog.innerHTML = `<div class="catalog-result-count">Ingen produkter passet til «${escapeHtml(normalizedQuery)}».</div>`;
          catalogHint.textContent = "Prøv et annet eller kortere søkeord.";
          return;
        }
        const countText = normalizedQuery
          ? `${products.length} produkt${products.length === 1 ? "" : "er"} passer til «${escapeHtml(normalizedQuery)}»`
          : `Alle produkter (${products.length}), sortert alfabetisk`;
        productCatalog.innerHTML = `
          <div class="catalog-result-count">${countText}</div>
          ${products.map(product => `
            <button
              class="catalog-result"
              type="button"
              data-product-value="${escapeHtml(product.articleNumber || product.title)}"
              data-product-title="${escapeHtml(product.title)}"
              data-product-price="${escapeHtml(product.price || "")}"
              data-product-image="${escapeHtml(product.image || "")}"
            >
              ${product.image
                ? `<img src="${escapeHtml(product.image)}" alt="">`
                : `<span class="catalog-result-image">Bilde</span>`}
              <span>
                <strong>${escapeHtml(product.title)}</strong>
                <span class="catalog-result-number">Art.nr. ${escapeHtml(product.articleNumber || "ikke oppgitt")}</span>
              </span>
              <span class="catalog-result-meta">
                <span class="catalog-result-price">${escapeHtml(product.price || "Pris mangler")}</span>
                <span class="availability ${escapeHtml(product.availability || "unknown")}">${
                  product.availability === "available"
                    ? "Tilgjengelig"
                    : product.availability === "unavailable"
                      ? "Ikke tilgjengelig"
                      : "Ukjent status"
                }</span>
              </span>
            </button>`).join("")}`;
        catalogHint.textContent = normalizedQuery
          ? "Bare produkter som matcher søket vises."
          : "Norske eller engelske navn, med bilde, pris og tilgjengelighet.";
      } catch (error) {
        if (requestNumber !== catalogSearchRequest) return;
        productCatalog.innerHTML = `<div class="catalog-result-count">${escapeHtml(error.message)}</div>`;
        catalogHint.textContent = "Produktlisten kunne ikke lastes.";
      }
    }

    function escapeHtml(value) {
      return String(value || "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    function isPositivePrice(value) {
      const match = String(value || "").match(/-?\d+(?:[.,]\d+)?/);
      return Boolean(match && Number(match[0].replace(",", ".")) > 0);
    }

    function priceMarkup(product) {
      if (product.isSale && isPositivePrice(product.comparePrice) && product.price) {
        return `<div class="sale-price">
          <span class="sale-label">Tilbud</span>
          <span class="before-price">Før: <span>${escapeHtml(product.comparePrice)}</span></span>
          <span class="now-price">Nå: ${escapeHtml(product.price)}</span>
        </div>`;
      }
      return product.price ? `<div class="price">${escapeHtml(product.price)}</div>` : "";
    }

    function setMode(mode) {
      currentMode = mode;
      const isRecipe = mode === "recipe";
      modeRecipe.classList.toggle("active", isRecipe);
      modeProduct.classList.toggle("active", !isRecipe);
      recipeFields.classList.toggle("hidden", !isRecipe);
      productFields.classList.toggle("hidden", isRecipe);
      generate.textContent = isRecipe ? "Lag oppskriftsmail" : "Lag mailinnhold";
      result.innerHTML = isRecipe
        ? `<div class="image-box"><div class="empty">Oppskriftstips vises her</div></div><div><h2>Oppskriftsmail</h2><p class="description">Skriv inn en rett, så finner programmet ingredienser og Tupperware-produkter som passer.</p></div>`
        : `<div class="image-box"><div class="empty">Produktbildet vises her</div></div><div><h2>Produktinfo</h2><p class="description">Når du trykker på knappen, henter programmet navn, bilde, tekst og pris fra lenken.</p></div>`;
    }

    function showCatalogSelection(button) {
      productCatalog.querySelectorAll(".catalog-result").forEach(item => {
        item.classList.toggle("selected", item === button);
      });
      const title = button.dataset.productTitle || button.dataset.productValue || "Valgt produkt";
      currentProductTitle = title;
      const price = button.dataset.productPrice || "";
      const image = button.dataset.productImage || "";
      result.innerHTML = `
        ${image
          ? `<div class="image-box"><img src="${escapeHtml(image)}" alt="${escapeHtml(title)}"></div>`
          : `<div class="image-box"><div class="empty">Henter produktbilde ...</div></div>`}
        <div>
          <h2>${escapeHtml(title)}</h2>
          ${price ? `<div class="price">${escapeHtml(price)}</div>` : ""}
          <p class="description">Produktet er valgt. Lager mailinnhold ...</p>
        </div>`;
      email.value = "";
      currentEmailHtml = "";
      emailPreview.innerHTML = `<div class="mail-preview-empty">Lager designmail ...</div>`;
    }

    function render(data) {
      if (data.mode === "recipe") {
        renderRecipe(data);
        return;
      }
      const product = data.product;
      productUrl.value = product.sourceUrl || productUrl.value;
      const recipes = data.recipes || [];
      const images = product.images && product.images.length ? product.images : (product.image ? [product.image] : []);
      const imageGallery = images.length
        ? `<div class="gallery">
            <div class="image-box"><img id="mainProductImage" src="${escapeHtml(images[0])}" alt="${escapeHtml(product.title)}"></div>
            ${images.length > 1 ? `<div class="thumbs">${images.map((src, index) => `
              <button class="thumb ${index === 0 ? "active" : ""}" type="button" data-image="${escapeHtml(src)}" aria-label="Vis produktbilde ${index + 1}">
                <img src="${escapeHtml(src)}" alt="">
              </button>`).join("")}</div>` : ""}
          </div>`
        : `<div class="image-box"><div class="empty">Fant ikke produktbilde</div></div>`;
      const recipeSection = recipes.length
        ? `<div class="recipes">
            <h3>Oppskrifter og tips som bruker produktet</h3>
            ${recipes.map(item => `<a href="${escapeHtml(item.url)}" target="recipe-source">${escapeHtml(item.title)}</a>`).join("")}
          </div>`
        : "";
      result.innerHTML = `
        ${imageGallery}
        <div>
          <h2>${escapeHtml(product.title)}</h2>
          ${product.englishTitle ? `<p class="english-product-name">Engelsk navn: ${escapeHtml(product.englishTitle)}</p>` : ""}
          ${priceMarkup(product)}
          <p class="description">${escapeHtml(product.description || "Ingen produkttekst funnet.")}</p>
          <div class="button-row">
            <a class="button" href="${escapeHtml(product.sourceUrl)}" target="tupperware-shop">Åpne produkt</a>
            ${images.length ? `<span class="hint">${images.length} produktbilde${images.length === 1 ? "" : "r"} funnet</span>` : ""}
          </div>
          ${recipeSection}
        </div>`;
      result.querySelectorAll(".thumb").forEach(button => {
        button.addEventListener("click", () => {
          const mainImage = result.querySelector("#mainProductImage");
          if (mainImage) mainImage.src = button.dataset.image;
          result.querySelectorAll(".thumb").forEach(item => item.classList.remove("active"));
          button.classList.add("active");
        });
      });
      email.value = data.email || "";
      currentEmailHtml = data.emailHtml || "";
      emailPreview.innerHTML = currentEmailHtml || `<div class="mail-preview-empty">Fant ikke designmail.</div>`;
    }

    function renderRecipe(data) {
      const recipe = data.recipe || {};
      const products = recipe.products || [];
      const inspirations = recipe.inspirations || [];
      const ingredients = recipe.ingredients || [];
      const instructions = recipe.instructions || [];
      const guidedInstructions = recipe.guidedInstructions || instructions.map(item => ({text: item, productUses: []}));
      const ingredientItems = ingredients.map(item => `<li>${escapeHtml(item)}</li>`).join("");
      const instructionItems = guidedInstructions.map(item => `
        <li>
          ${escapeHtml(item.text)}
          ${(item.productUses || []).map(use => `<span class="use-tip"><strong>Tupperware i dette trinnet:</strong> ${escapeHtml(use.text)}</span>`).join("")}
        </li>`).join("");
      const productItems = products.length
        ? products.map(product => `
          <div class="product-mini">
            ${product.image ? `<img src="${escapeHtml(product.image)}" alt="">` : `<div></div>`}
            <div>
              <strong>${escapeHtml(product.title)}</strong>
              ${product.price ? `<span class="hint">${escapeHtml(product.price)}</span>` : ""}
              ${product.useTip ? `<span class="use-tip">${escapeHtml(product.useTip)}</span>` : ""}
              <a href="${escapeHtml(product.sourceUrl)}" target="tupperware-shop">Åpne produkt</a>
            </div>
          </div>`).join("")
        : `<p class="description">Fant ingen konkrete produkter automatisk.</p>`;
      const inspirationItems = inspirations.length
        ? inspirations.map(item => `<a href="${escapeHtml(item.url)}" target="recipe-source">${escapeHtml(item.title)}</a>`).join("")
        : "";
      result.innerHTML = `
        <div class="image-box recipe-photo">${recipe.image ? `<img src="${escapeHtml(recipe.image)}" alt="${escapeHtml(recipe.name || "Oppskrift")}">` : `<div class="empty">Oppskrift</div>`}</div>
        <div>
          <h2>${escapeHtml(recipe.name || "Oppskrift")}</h2>
          <p class="description">${recipe.sourceUrl ? `Basert på oppskrift og Tupperware-søk.` : `Ingredienser og produktforslag er laget som et praktisk utgangspunkt.`}</p>
          ${recipe.sourceUrl ? `<a class="source-link" href="${escapeHtml(recipe.sourceUrl)}" target="recipe-source">${recipe.sourceUrl.includes("matprat.no") ? "Oppskrift fra MatPrat" : "Åpne oppskriften"}: ${escapeHtml(recipe.title || recipe.sourceUrl)}</a>` : ""}
          <h3>Ingredienser</h3>
          <ul class="ingredients-list">${ingredientItems}</ul>
          <h3>Fremgangsmåte</h3>
          <ol class="instructions-list">${instructionItems}</ol>
          <h3>Tupperware-produkter som passer</h3>
          ${productItems}
          ${inspirationItems ? `<div class="recipes"><h3>Tupperware-inspirasjon på engelsk</h3>${inspirationItems}</div>` : ""}
        </div>`;
      email.value = data.email || "";
      currentEmailHtml = data.emailHtml || "";
      emailPreview.innerHTML = currentEmailHtml || `<div class="mail-preview-empty">Fant ikke designmail.</div>`;
    }

    async function loadProductRecipes(product, requestNumber) {
      try {
        const response = await fetch("/api/product-recipes", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            product,
            consultant: consultant.value
          })
        });
        const data = await response.json();
        if (requestNumber !== generationRequest || currentMode !== "product") return;
        if (!response.ok) throw new Error(data.error || "Kunne ikke hente oppskriftstips.");
        render(data);
        const count = (data.recipes || []).length;
        setStatus(count
          ? `Ferdig. Fant ${count} relevant${count === 1 ? "" : "e"} oppskriftstips.`
          : "Ferdig. Fant ingen sikre oppskriftstips som bruker produktet.");
      } catch (error) {
        if (requestNumber !== generationRequest || currentMode !== "product") return;
        setStatus("Produkt og mail er ferdig. Oppskriftstips kunne ikke hentes.", true);
      }
    }

    async function generateMail() {
      const requestNumber = ++generationRequest;
      generate.disabled = true;
      setStatus(currentMode === "product"
        ? "Henter produkt og lager mail ..."
        : "Henter oppskrift og lager mail ...");
      try {
        const response = await fetch("/api/generate", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            mode: currentMode,
            productQuery: productQuery.value,
            productUrl: productUrl.value,
            recipeName: recipeName.value,
            consultant: consultant.value
          })
        });
        const data = await response.json();
        if (requestNumber !== generationRequest) return;
        if (!response.ok) throw new Error(data.error || "Ukjent feil");
        render(data);
        if (currentMode === "product") {
          setStatus("Produkt og mail er ferdig. Søker etter sikre oppskriftstips ...");
          void loadProductRecipes(data.product, requestNumber);
        } else {
          setStatus("Ferdig.");
        }
      } catch (error) {
        if (requestNumber !== generationRequest) return;
        const message = error instanceof TypeError && /fetch/i.test(error.message)
          ? "Kan ikke kontakte mailgeneratoren. Dobbeltklikk START MAILVERKTOY.cmd for å starte den skjulte serveren."
          : error.message;
        setStatus(message, true);
      } finally {
        if (requestNumber === generationRequest) generate.disabled = false;
      }
    }

    generate.addEventListener("click", generateMail);

    clear.addEventListener("click", () => {
      generationRequest += 1;
      generate.disabled = false;
      productUrl.value = "";
      productQuery.value = "";
      searchProductCatalog("");
      recipeName.value = "";
      consultant.value = "ref=LISBETHOVERBYE";
      email.value = "";
      currentEmailHtml = "";
      emailPreview.innerHTML = `<div class="mail-preview-empty">Forhåndsvisning av designmailen kommer her</div>`;
      result.innerHTML = `<div class="image-box"><div class="empty">Produktbildet vises her</div></div><div><h2>Produktinfo</h2><p class="description">Når du trykker på knappen, henter programmet navn, bilde, tekst og pris fra lenken.</p></div>`;
      setStatus("");
    });

    modeProduct.addEventListener("click", () => setMode("product"));
    modeRecipe.addEventListener("click", () => setMode("recipe"));
    productQuery.addEventListener("input", () => {
      window.clearTimeout(catalogSearchTimer);
      catalogSearchTimer = window.setTimeout(() => searchProductCatalog(productQuery.value), 280);
    });
    productCatalog.addEventListener("click", event => {
      const button = event.target.closest(".catalog-result");
      if (!button) return;
      showCatalogSelection(button);
      productQuery.value = button.dataset.productValue || "";
      productUrl.value = "";
      generateMail();
    });

    copy.addEventListener("click", async () => {
      if (!email.value.trim()) return;
      await navigator.clipboard.writeText(email.value);
      setStatus("Mailteksten er kopiert.");
    });

    copyHtml.addEventListener("click", async () => {
      if (!currentEmailHtml.trim()) return;
      try {
        const copiedRich = copyPreviewAsRichContent();
        if (copiedRich) {
          setStatus("Innholdet er kopiert. Lim det rett inn i en ny e-post.");
          return;
        }
        await copyHtmlToClipboard();
        setStatus("Innholdet er kopiert. Lim det rett inn i en ny e-post.");
      } catch (error) {
        await navigator.clipboard.writeText(email.value || currentEmailHtml);
        setStatus("Ren tekst er kopiert. Mailprogrammet støttet ikke designkopiering.", true);
      }
    });

    document.querySelector("#downloadPdf").addEventListener("click", () => {
      if (!currentEmailHtml.trim()) {
        setStatus("Lag mailinnhold først.", true);
        return;
      }
      const previousTitle = document.title;
      const safeFilename = (currentProductTitle || "Tupperware-tilbud")
        .replace(/[<>:"/\\|?*]+/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 100) || "Tupperware-tilbud";
      document.title = safeFilename;
      const printStyle = document.createElement("style");
      printStyle.id = "pdfPrintStyle";
      printStyle.textContent = "@page { size: A4; margin: 12mm; }";
      document.head.appendChild(printStyle);
      window.print();
      window.setTimeout(() => {
        printStyle.remove();
        document.title = previousTitle;
      }, 1000);
    });

    function copyPreviewAsRichContent() {
      const wrapper = emailPreview.firstElementChild;
      if (!wrapper || wrapper.classList.contains("mail-preview-empty")) return false;
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNode(wrapper);
      selection.removeAllRanges();
      selection.addRange(range);
      const ok = document.execCommand("copy");
      selection.removeAllRanges();
      return ok;
    }

    async function copyHtmlToClipboard() {
      if (window.ClipboardItem) {
        const item = new ClipboardItem({
          "text/html": new Blob([currentEmailHtml], {type: "text/html"}),
          "text/plain": new Blob([email.value], {type: "text/plain"})
        });
        await navigator.clipboard.write([item]);
        return;
      }
      await navigator.clipboard.writeText(email.value || currentEmailHtml);
    }

    loadProductCatalog();
  </script>
</body>
</html>
"""


class MailToolServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def open_mail_tool_in_chrome(url):
    chrome_candidates = [
        shutil.which("chrome"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for chrome_path in chrome_candidates:
        if chrome_path and os.path.isfile(chrome_path):
            subprocess.Popen([chrome_path, "--new-tab", url])
            return
    webbrowser.open(url, new=2)


def main():
    port = APP_PORT
    open_browser = "--open-browser" in sys.argv[1:]
    for argument in sys.argv[1:]:
        if argument.isdigit():
            port = int(argument)

    server = MailToolServer((APP_HOST, port), Handler)
    print(f"Tupperware mailverktøy kjører på http://{APP_HOST}:{port}")
    if open_browser:
        threading.Timer(0.6, open_mail_tool_in_chrome, args=(f"http://{APP_HOST}:{port}/",)).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
