from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import os
import shutil
import subprocess
import sys


SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
NODE_EXE = shutil.which("node") or os.path.expanduser(
    r"~\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
)


def is_configured():
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def _request(path, query=None, method="GET", payload=None):
    if not is_configured():
        return []
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    if sys.platform.startswith("win") and os.path.isfile(NODE_EXE):
        return _request_node(url, method, payload)
    try:
        with urlopen(request, timeout=15) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or str(error)) from error


def _request_node(url, method="GET", payload=None):
    script = r"""
const [url, key, method, encodedBody] = process.argv.slice(1);
fetch(url, {
  method,
  headers: {
    apikey: key,
    authorization: `Bearer ${key}`,
    accept: "application/json",
    "content-type": "application/json"
  },
  body: encodedBody ? Buffer.from(encodedBody, "base64").toString("utf8") : undefined
}).then(async response => {
  const body = await response.text();
  if (!response.ok) {
    console.error(`${response.status} ${body}`);
    process.exit(2);
  }
  process.stdout.write(body);
}).catch(error => {
  console.error(error && error.message ? error.message : String(error));
  process.exit(1);
});
"""
    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    encoded_body = ""
    if payload is not None:
        encoded_body = __import__("base64").b64encode(
            json.dumps(payload).encode("utf-8")
        ).decode("ascii")
    result = subprocess.run(
        [
            NODE_EXE,
            "--no-warnings",
            "-e",
            script,
            url,
            SUPABASE_ANON_KEY,
            method,
            encoded_body,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=23,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Kunne ikke hente konsulentregisteret.")
    return json.loads(result.stdout) if result.stdout else None


def list_consultants(search="", limit=50):
    limit = min(100, max(1, int(limit)))
    query = {
        "select": (
            "id,reference_code,display_name,municipality,county,"
            "profile_image_url,catalog_slug"
        ),
        "status": "eq.active",
        "public_listing": "eq.true",
        "order": "display_name.asc",
        "limit": str(limit),
    }
    cleaned = " ".join(str(search or "").split())
    if cleaned:
        escaped = cleaned.replace(",", r"\,").replace("*", "")
        query["or"] = (
            f"(display_name.ilike.*{escaped}*,"
            f"municipality.ilike.*{escaped}*,county.ilike.*{escaped}*)"
        )
    return _request("public_consultants", query)


def find_consultant(reference_code):
    reference_code = str(reference_code or "").strip().upper()
    if not reference_code or not is_configured():
        return None
    rows = _request(
        "public_consultants",
        {
            "select": (
                "id,reference_code,display_name,municipality,county,"
                "profile_image_url,catalog_slug"
            ),
            "reference_code": f"eq.{quote(reference_code, safe='')}",
            "status": "eq.active",
            "public_listing": "eq.true",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def find_consultant_contact(reference_code):
    reference_code = str(reference_code or "").strip().upper()
    if not reference_code or not is_configured():
        return {}
    try:
        rows = _request(
            "rpc/public_consultant_contact",
            method="POST",
            payload={"p_reference_code": reference_code},
        )
    except Exception:
        return {}
    row = rows[0] if rows else {}
    if row.get("email"):
        return {"email": row["email"]}
    return {}


def consultant_shop_status(reference_code):
    reference_code = str(reference_code or "").strip().upper()
    if not reference_code or not is_configured():
        return None
    rows = _request(
        "rpc/consultant_shop_status",
        method="POST",
        payload={"p_reference_code": reference_code},
    )
    return rows[0] if rows else None


def consultant_product_access(reference_code):
    reference_code = str(reference_code or "").strip().upper()
    if not reference_code or not is_configured():
        return []
    rows = _request(
        "rpc/consultant_product_access_list",
        method="POST",
        payload={"p_reference_code": reference_code},
    )
    return [
        str(row.get("product_key") or "").strip()
        for row in rows
        if row.get("product_key")
    ]


def list_own_inventory(reference_code, access_code=None):
    reference_code = str(reference_code or "").strip().upper()
    if not reference_code or not is_configured():
        return []
    return _request(
        "rpc/get_consultant_shop_inventory",
        method="POST",
        payload={
            "p_reference_code": reference_code,
            "p_access_code": str(access_code or "").strip() or None,
        },
    )


def submit_own_inventory_order(reference_code, customer, items, access_code=None):
    if not is_configured():
        raise RuntimeError("Konsulentregisteret er ikke konfigurert.")
    return _request(
        "rpc/submit_consultant_inventory_order",
        method="POST",
        payload={
            "p_reference_code": str(reference_code or "").strip().upper(),
            "p_customer": customer,
            "p_items": items,
            "p_access_code": str(access_code or "").strip() or None,
        },
    )


def public_config():
    return {
        "supabaseUrl": SUPABASE_URL,
        "supabaseAnonKey": SUPABASE_ANON_KEY,
        "configured": is_configured(),
    }
