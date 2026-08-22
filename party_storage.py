from urllib.error import HTTPError
from urllib.parse import urlencode
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


def _request(path, query=None, method="GET", payload=None, prefer=None):
    if not is_configured():
        raise RuntimeError("Supabase er ikke konfigurert.")
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    request = Request(url, data=body, method=method, headers=headers)
    if sys.platform.startswith("win") and os.path.isfile(NODE_EXE):
        return _request_node(url, method, payload, prefer)
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(detail or str(error)) from error


def _request_node(url, method="GET", payload=None, prefer=None):
    script = r"""
const [url, key, method, encodedBody, prefer] = process.argv.slice(1);
const headers = {
  apikey: key,
  authorization: `Bearer ${key}`,
  accept: "application/json",
  "content-type": "application/json"
};
if (prefer) headers.prefer = prefer;
fetch(url, {
  method,
  headers,
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
        [NODE_EXE, "--no-warnings", "-e", script, url, SUPABASE_ANON_KEY, method, encoded_body, prefer or ""],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=25,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Kunne ikke koble til party-lagring.")
    return json.loads(result.stdout) if result.stdout else None


def _normalize_featured_ids(featured):
    values = []
    for product_id in featured or []:
        value = str(product_id or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def _normalize_consultant_ref(consultant_ref):
    return str(consultant_ref or "").strip().upper()


def list_parties(consultant_ref):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    parties = _request(
        "party_events",
        {
            "select": (
                "id,title,party_type,consultant_ref,starts_at,ends_at,host_mode,host_name,location,"
                "message,host_intro,video_url,vipps_message,featured_product_ids,"
                "orders:party_orders(id,customer_name,customer_email,customer_phone,customer_address,customer_postal_code,customer_city,customer_country,status,created_at,lines:party_order_lines("
                "product_id,product_name,article_number,quantity,observed_price_nok"
                "))"
            ),
            "consultant_ref": f"eq.{consultant_ref}",
            "order": "starts_at.asc.nullslast,created_at.desc",
        },
    )
    return [_map_party(row) for row in parties or []]


def create_party(consultant_ref, payload=None):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    payload = payload or {}
    body = {
        "title": str(payload.get("title") or "Nytt party").strip() or "Nytt party",
        "consultant_ref": consultant_ref,
        "party_type": str(payload.get("type") or "combined").strip() or "combined",
        "starts_at": payload.get("startsAt") or None,
        "ends_at": payload.get("endsAt") or None,
        "host_mode": str(payload.get("hostMode") or "manual").strip() or "manual",
        "host_name": str(payload.get("hostName") or "").strip(),
        "location": str(payload.get("location") or "").strip(),
        "message": str(payload.get("message") or "").strip(),
        "host_intro": str(payload.get("hostIntro") or "").strip(),
        "video_url": str(payload.get("video") or "").strip(),
        "vipps_message": str(payload.get("vipps") or "").strip(),
        "featured_product_ids": _normalize_featured_ids(payload.get("featured")),
    }
    rows = _request(
        "party_events",
        {"select": "*"},
        method="POST",
        payload=body,
        prefer="return=representation",
    )
    if not rows:
        raise RuntimeError("Kunne ikke opprette partyet.")
    return rows[0]


def save_party(consultant_ref, party_id, payload):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    body = {
        "title": str(payload.get("title") or "").strip(),
        "party_type": str(payload.get("type") or "combined").strip() or "combined",
        "starts_at": payload.get("startsAt") or None,
        "ends_at": payload.get("endsAt") or None,
        "host_mode": str(payload.get("hostMode") or "manual").strip() or "manual",
        "host_name": str(payload.get("hostName") or "").strip(),
        "location": str(payload.get("location") or "").strip(),
        "message": str(payload.get("message") or "").strip(),
        "host_intro": str(payload.get("hostIntro") or "").strip(),
        "video_url": str(payload.get("video") or "").strip(),
        "vipps_message": str(payload.get("vipps") or "").strip(),
        "featured_product_ids": _normalize_featured_ids(payload.get("featured")),
    }
    rows = _request(
        "party_events",
        {"id": f"eq.{party_id}", "consultant_ref": f"eq.{consultant_ref}", "select": "*"},
        method="PATCH",
        payload=body,
        prefer="return=representation",
    )
    if not rows:
        raise RuntimeError("Fant ikke partyet i delt lagring.")
    return rows[0]


def copy_party(consultant_ref, party_id):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    parties = _request(
        "party_events",
        {"id": f"eq.{party_id}", "consultant_ref": f"eq.{consultant_ref}", "select": "*", "limit": "1"},
    )
    if not parties:
        raise RuntimeError("Fant ikke partyet i delt lagring.")
    party = parties[0]
    copied = {
        "title": f"{party.get('title') or 'Party'} (kopi)",
        "consultant_ref": consultant_ref,
        "party_type": party.get("party_type") or "combined",
        "starts_at": None,
        "ends_at": None,
        "host_mode": party.get("host_mode") or "manual",
        "host_name": party.get("host_name") or "",
        "location": party.get("location") or "",
        "message": party.get("message") or "",
        "host_intro": party.get("host_intro") or "",
        "video_url": party.get("video_url") or "",
        "vipps_message": party.get("vipps_message") or "",
        "featured_product_ids": _normalize_featured_ids(party.get("featured_product_ids")),
    }
    rows = _request(
        "party_events",
        {"select": "*"},
        method="POST",
        payload=copied,
        prefer="return=representation",
    )
    return rows[0] if rows else None


def delete_party(consultant_ref, party_id):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    _request("party_events", {"id": f"eq.{party_id}", "consultant_ref": f"eq.{consultant_ref}"}, method="DELETE", prefer="return=minimal")
    return True


def add_featured_product(consultant_ref, party_id, product_id):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    parties = _request(
        "party_events",
        {"id": f"eq.{party_id}", "consultant_ref": f"eq.{consultant_ref}", "select": "id,featured_product_ids", "limit": "1"},
    )
    if not parties:
        raise RuntimeError("Fant ikke partyet i delt lagring.")
    featured = _normalize_featured_ids((parties[0] or {}).get("featured_product_ids"))
    product_id = str(product_id or "").strip()
    if product_id and product_id not in featured:
        featured.append(product_id)
    rows = _request(
        "party_events",
        {"id": f"eq.{party_id}", "consultant_ref": f"eq.{consultant_ref}", "select": "*"},
        method="PATCH",
        payload={"featured_product_ids": featured},
        prefer="return=representation",
    )
    return rows[0] if rows else None


def submit_order(consultant_ref, party_id, customer, lines, order_id=None, contact=None):
    consultant_ref = _normalize_consultant_ref(consultant_ref)
    customer_name = str(customer or "").strip() or "Ny kunde"
    contact = contact or {}
    customer_email = str(contact.get("email") or "").strip()
    customer_phone = str(contact.get("phone") or "").strip()
    customer_address = str(contact.get("address") or "").strip()
    customer_postal_code = str(contact.get("postalCode") or "").strip()
    customer_city = str(contact.get("city") or "").strip()
    customer_country = str(contact.get("country") or "").strip()
    normalized_lines = _normalize_order_lines(lines)
    order = None
    if order_id:
        existing = _request(
            "party_orders",
            {
                "id": f"eq.{order_id}",
                "party_id": f"eq.{party_id}",
                "select": "*,lines:party_order_lines(product_id,product_name,article_number,quantity,observed_price_nok)",
                "limit": "1",
            },
        )
        if existing:
            order = existing[0]
            if str(order.get("status") or "").strip().lower() == "registrert hos tupperware":
                raise RuntimeError("Bestillingen er allerede registrert hos Tupperware og kan ikke endres.")
            existing_signature = _order_signature(
                [
                    {
                        "article": line.get("article_number") or "",
                        "name": line.get("product_name") or "",
                        "qty": line.get("quantity") or 0,
                        "price": line.get("observed_price_nok") or 0,
                    }
                    for line in order.get("lines") or []
                ]
            )
            incoming_signature = _order_signature(normalized_lines)
            if existing_signature == incoming_signature:
                return order
            updated = _request(
                "party_orders",
                {"id": f"eq.{order_id}", "select": "*"},
                method="PATCH",
                payload={
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "customer_address": customer_address,
                    "customer_postal_code": customer_postal_code,
                    "customer_city": customer_city,
                    "customer_country": customer_country,
                    "status": "Oppdatert",
                },
                prefer="return=representation",
            )
            order = updated[0] if updated else order
            _request("party_order_lines", {"party_order_id": f"eq.{order_id}"}, method="DELETE", prefer="return=minimal")
    if not order:
        existing = _request(
            "party_orders",
            {
                "party_id": f"eq.{party_id}",
                "customer_name": f"eq.{customer_name}",
                "select": "*,lines:party_order_lines(product_id,product_name,article_number,quantity,observed_price_nok)",
                "order": "created_at.desc",
                "limit": "1",
            },
        )
        if existing:
            candidate = existing[0]
            if str(candidate.get("status") or "").strip().lower() != "registrert hos tupperware":
                existing_signature = _order_signature(
                    [
                        {
                            "article": line.get("article_number") or "",
                            "name": line.get("product_name") or "",
                            "qty": line.get("quantity") or 0,
                            "price": line.get("observed_price_nok") or 0,
                        }
                        for line in candidate.get("lines") or []
                    ]
                )
                incoming_signature = _order_signature(normalized_lines)
                if existing_signature == incoming_signature:
                    return candidate
                updated = _request(
                    "party_orders",
                    {"id": f"eq.{candidate['id']}", "select": "*"},
                    method="PATCH",
                    payload={
                        "customer_name": customer_name,
                        "customer_email": customer_email,
                        "customer_phone": customer_phone,
                        "customer_address": customer_address,
                        "customer_postal_code": customer_postal_code,
                        "customer_city": customer_city,
                        "customer_country": customer_country,
                        "status": "Oppdatert",
                    },
                    prefer="return=representation",
                )
                order = updated[0] if updated else candidate
                _request(
                    "party_order_lines",
                    {"party_order_id": f"eq.{candidate['id']}"},
                    method="DELETE",
                    prefer="return=minimal",
                )
    if not order:
        order_rows = _request(
            "party_orders",
            {"select": "*"},
            method="POST",
            payload={
                "party_id": party_id,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_address": customer_address,
                "customer_postal_code": customer_postal_code,
                "customer_city": customer_city,
                "customer_country": customer_country,
                "status": "Ny",
            },
            prefer="return=representation",
        )
        if not order_rows:
            raise RuntimeError("Kunne ikke lagre bestillingen.")
        order = order_rows[0]
    items = []
    for line in normalized_lines:
        items.append(
            {
                "party_order_id": order["id"],
                "product_id": str(line.get("productId") or "").strip(),
                "product_name": str(line.get("name") or "").strip(),
                "article_number": str(line.get("article") or "").strip(),
                "quantity": int(line.get("qty") or 0),
                "observed_price_nok": line.get("price"),
            }
        )
    if items:
        _request("party_order_lines", method="POST", payload=items, prefer="return=minimal")
    return order


def _normalize_order_lines(lines):
    normalized = []
    for line in lines or []:
        quantity = int(line.get("qty") or 0)
        if quantity <= 0:
            continue
        normalized.append(
            {
                "productId": str(line.get("productId") or "").strip(),
                "article": str(line.get("article") or "").strip(),
                "name": str(line.get("name") or "").strip(),
                "qty": quantity,
                "price": float(line.get("price") or 0),
            }
        )
    return normalized


def _order_signature(lines):
    parts = []
    for line in sorted(
        lines or [],
        key=lambda item: (
            str(item.get("article") or ""),
            str(item.get("name") or ""),
            int(item.get("qty") or 0),
            float(item.get("price") or 0),
        ),
    ):
        parts.append(
            "|".join(
                [
                    str(line.get("article") or ""),
                    str(line.get("name") or ""),
                    str(int(line.get("qty") or 0)),
                    f"{float(line.get('price') or 0):.2f}",
                ]
            )
        )
    return "||".join(parts)


def update_order_status(consultant_ref, party_id, order_id, status):
    _normalize_consultant_ref(consultant_ref)
    rows = _request(
        "party_orders",
        {"id": f"eq.{order_id}", "party_id": f"eq.{party_id}", "select": "*"},
        method="PATCH",
        payload={"status": str(status or "Ny").strip() or "Ny"},
        prefer="return=representation",
    )
    if not rows:
        raise RuntimeError("Fant ikke bestillingen.")
    return rows[0]


def delete_order(consultant_ref, party_id, order_id):
    _normalize_consultant_ref(consultant_ref)
    _request(
        "party_orders",
        {"id": f"eq.{order_id}", "party_id": f"eq.{party_id}"},
        method="DELETE",
        prefer="return=minimal",
    )
    return True


def _map_party(row):
    orders = []
    for order in row.get("orders") or []:
        lines = [
            {
                "productId": line.get("product_id") or "",
                "name": line.get("product_name") or "",
                "article": line.get("article_number") or "",
                "qty": line.get("quantity") or 1,
                "price": line.get("observed_price_nok") or 0,
            }
            for line in order.get("lines") or []
        ]
        total_qty = sum(int(line.get("qty") or 0) for line in lines)
        total_amount = sum((float(line.get("price") or 0) * int(line.get("qty") or 0)) for line in lines)
        orders.append(
            {
                "id": order.get("id"),
                "customer": order.get("customer_name") or "Kunde",
                "email": order.get("customer_email") or "",
                "phone": order.get("customer_phone") or "",
                "address": order.get("customer_address") or "",
                "postalCode": order.get("customer_postal_code") or "",
                "city": order.get("customer_city") or "",
                "country": order.get("customer_country") or "",
                "status": order.get("status") or "Ny",
                "createdAt": order.get("created_at") or "",
                "totalQty": total_qty,
                "totalAmount": total_amount,
                "lines": lines,
            }
        )
    return {
        "id": row.get("id"),
        "title": row.get("title") or "",
        "consultantRef": row.get("consultant_ref") or "",
        "type": row.get("party_type") or "combined",
        "startsAt": _to_local_datetime(row.get("starts_at")),
        "endsAt": _to_local_datetime(row.get("ends_at")),
        "hostMode": row.get("host_mode") or "manual",
        "hostName": row.get("host_name") or "",
        "location": row.get("location") or "",
        "message": row.get("message") or "",
        "hostIntro": row.get("host_intro") or "",
        "video": row.get("video_url") or "",
        "vipps": row.get("vipps_message") or "",
        "featured": _normalize_featured_ids(row.get("featured_product_ids")),
        "orders": orders,
    }


def _to_local_datetime(value):
    if not value:
        return ""
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1]
    if "+" in text:
        text = text.split("+", 1)[0]
    return text[:16]
