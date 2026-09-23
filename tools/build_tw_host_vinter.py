from __future__ import annotations

import html
import json
import re
import subprocess
from pathlib import Path

import pdfplumber
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = Path(r"C:\Users\janro\Downloads\CATA 27 - A5 EN - Norway BD.pdf")
OUTPUT = ROOT / "tw-host-vinter-2026-27"
PAGES = OUTPUT / "pages"
POPPLER = Path(
    r"C:\Users\janro\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)

OVERLAYS = {
    1: '''<div class="translation-panel cover-translation"><strong>Høst 2026 - vinter 2027</strong><span>Gleden ved å dele hverdagens viktigste øyeblikk</span></div>''',
    2: '''<div class="translation-panel page-two-translation"><h2>Velkommen til den nye Tupperware-katalogen!</h2><p>Høsten senker seg, dagene blir kjøligere og de gode stundene sammen blir enda viktigere.</p><p>Oppdag vårt nye høst- og vinterutvalg for matlaging, oppbevaring, organisering og hyggelige måltider. Her finner du både velkjente favoritter og nye løsninger som gjør hverdagen enklere.</p><p>Enten du liker hjemmelaget mat, smarte løsninger på farten eller orden hjemme, er katalogen full av ideer for sesongen.</p><p><strong>God fornøyelse!</strong></p></div>''',
    3: '''<div class="translation-panel full-text-translation"><h2>Gjør hverdagen enklere</h2><h3>Smart og uunnværlig</h3><p>Tupperware er mer enn oppbevaringsbokser. Produktene er laget for hverdagens behov, med gjennomtenkt funksjon og et moderne uttrykk.</p><h3>Klar for alt</h3><p>Effektiv og intuitiv organisering hjelper deg med oppbevaring, matlaging og forberedelser.</p><h3>Utviklet for å gjøre en forskjell</h3><p>Kvalitet, funksjon og holdbarhet har stått sentralt helt fra starten.</p><h3>Kjøp én gang, bruk lenge</h3><p>Produkter som varer bidrar til mindre matsvinn og færre engangsprodukter.</p></div>''',
    4: '''<div class="translation-panel full-text-translation join-translation"><h2>Bli med</h2><h3>Bli kjent med produktene</h3><p>Start med nyttige Tupperware-produkter og få tilgang til arrangementer, gaver og gode tilbud.</p><h3>Jobb der du vil</h3><p>Arbeid fysisk eller digitalt, og legg opp dagene slik det passer deg.</p><h3>Møt nye mennesker</h3><p>Bli del av et engasjert fellesskap og skap nye kontakter.</p><h3>Kombiner jobb og fritid</h3><p>Du bestemmer selv arbeidstid og ambisjonsnivå.</p><h3>Provisjon fra første salg</h3><p>Du tjener provisjon helt fra starten.</p><h3>Jobb digitalt</h3><p>Bygg nettverk, skap gode kunderelasjoner og selg på nettet.</p></div>''',
    16: '''<div class="translation-panel recipe-intro"><strong>Et magisk måltid</strong><span>Én meny, mange muligheter til å glede. Lett å tilberede og elegant å servere - perfekt for familie og venner.</span></div><div class="translation-panel recipe-bottom"><h3>Butternutgresskarsuppe med parmesan-krem</h3><p><strong>Til 4 personer:</strong> 2 sjalottløk, 15 ml olje, 600 g butternutgresskar, 300 ml varmt vann, 1 grønnsaksbuljongterning, 400 ml kald kremfløte, 30 g parmesan, salt og pepper.</p><p>Hakk løken og varm den med olje. Tilsett skrelt gresskar i terninger, buljong og vann. Kok til mørt og mos. Pisk fløten, bland inn parmesan og smak til. Server suppen med parmesan-kremen.</p></div>''',
    17: '''<div class="translation-panel recipe-top"><h3>Pai med confitert and og sopp</h3><p><strong>Til 4 personer:</strong> andelår, sjalottløk, sjampinjong, hasselnøtter, persille, butterdeig, egg, salt og pepper.</p><p>Varm andelårene, fjern bein og skinn og riv kjøttet. Hakk løk og sopp, stek blandingen og tilsett and, nøtter og persille. Legg fyllet mellom to butterdeigplater, forsegl kantene, pensle med egg og stek ved 200 °C i omtrent 35 minutter.</p></div><div class="translation-panel recipe-lower"><h3>Bakte epler med nougat og sprø brioche</h3><p><strong>Til 4 personer:</strong> 4 epler, 80 g myk nougat, 4 skiver brioche, karamellsaus og 150 ml kremfløte.</p><p>Fjern kjernehuset og fyll eplene med nougat. Stek uten lokk i 40-45 minutter ved 180 °C. Rist brioche, varm karamell og fløte, og server eplene med saus og brioche.</p></div>''',
    18: '''<div class="translation-panel hummus-translation"><h3>Hjemmelaget hummus</h3><p>Kjør 120 g kokte, skylte kikerter sammen med et halvt hvitløksfedd. Tilsett 1 ss olivenolje, 1 ts sitronsaft og 1 ss soyasaus. Kjør til jevn konsistens og oppbevar kjølig.</p><p><strong>Variant:</strong> Tilsett 80 g kokt rødbete.</p></div>''',
    36: '''<div class="consultant-details" id="catalogConsultantDetails"><strong>Din Tupperware-konsulent</strong><span id="catalogConsultantName">Navn lastes inn ...</span><span id="catalogConsultantEmail"></span><span id="catalogConsultantPhone"></span></div>''',
}


def render_pages() -> list[dict[str, int | str]]:
    PAGES.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(POPPLER),
            "-png",
            "-r",
            "180",
            str(SOURCE_PDF),
            str(PAGES / "render"),
        ],
        check=True,
    )
    pages: list[dict[str, int | str]] = []
    for number, png in enumerate(sorted(PAGES.glob("render-*.png")), start=1):
        webp = PAGES / f"page-{number:02d}.webp"
        with Image.open(png) as source:
            image = source.convert("RGB")
            image.save(webp, "WEBP", quality=84, method=6)
            pages.append(
                {
                    "page": number,
                    "file": webp.name,
                    "width": image.width,
                    "height": image.height,
                }
            )
        png.unlink()
    return pages


def product_name(words: list[dict], code_word: dict) -> str:
    code_top = float(code_word["top"])
    code_center = (float(code_word["x0"]) + float(code_word["x1"])) / 2
    candidates = [
        word
        for word in words
        if code_top - 38 <= float(word["top"]) < code_top - 2
        and abs(((float(word["x0"]) + float(word["x1"])) / 2) - code_center) < 100
    ]
    if not candidates:
        return str(code_word["text"])
    nearest_top = max(float(word["top"]) for word in candidates)
    name_words = [
        word
        for word in candidates
        if nearest_top - 18 <= float(word["top"]) <= nearest_top + 3
        and not re.search(r"\d+\s*(?:cm|ml|kr|l)\b", str(word["text"]), re.I)
    ]
    name_words.sort(key=lambda word: (round(float(word["top"]), 1), float(word["x0"])))
    name = " ".join(str(word["text"]) for word in name_words).strip()
    return re.sub(r"\s+", " ", name) or str(code_word["text"])


def extract_products() -> list[dict[str, object]]:
    products: list[dict[str, object]] = []
    seen: set[tuple[int, str]] = set()
    code_pattern = re.compile(r"^(?:\d{7,8}|[A-Z]{1,4}\d{3,}[A-Z0-9]*)$")
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            width, height = float(page.width), float(page.height)
            words = page.extract_words(x_tolerance=2, y_tolerance=4, use_text_flow=False)
            for word in words:
                code = re.sub(r"[^A-Z0-9]", "", str(word.get("text", "")).upper())
                if not code_pattern.fullmatch(code) or (page_number, code) in seen:
                    continue
                seen.add((page_number, code))
                x0, x1 = float(word["x0"]), float(word["x1"])
                top, bottom = float(word["top"]), float(word["bottom"])
                center_x = (x0 + x1) / 2
                nearby = [
                    item
                    for item in words
                    if top - 52 <= float(item["top"]) <= bottom + 22
                    and abs(((float(item["x0"]) + float(item["x1"])) / 2) - center_x) <= 105
                ]
                bx0 = min((float(item["x0"]) for item in nearby), default=x0)
                bx1 = max((float(item["x1"]) for item in nearby), default=x1)
                btop = min((float(item["top"]) for item in nearby), default=top)
                bbottom = max((float(item["bottom"]) for item in nearby), default=bottom)
                block_width = min(42.0, max(18.0, (bx1 - bx0) / width * 100 + 2.4))
                block_height = min(12.0, max(5.2, (bbottom - btop) / height * 100 + 1.8))
                left = max(0.5, min(99.0 - block_width, bx0 / width * 100 - 1.2))
                top_percent = max(0.5, min(99.0 - block_height, btop / height * 100 - 0.9))
                products.append(
                    {
                        "page": page_number,
                        "code": code,
                        "name": product_name(words, word),
                        "left": left,
                        "top": top_percent,
                        "width": block_width,
                        "height": block_height,
                    }
                )
    return products


def product_row(product: dict[str, object]) -> str:
    code = html.escape(str(product["code"]))
    name = html.escape(str(product["name"]))
    page = int(product["page"])
    search = html.escape(f"{name} {code}".lower(), quote=True)
    return f'''<a class="product-row" href="https://tupperware-eu.com/no/search?q={code}" target="tupperware_shop"
      data-search="{search}" data-page="{page}" data-code="{code}">
      <span>{name}</span><strong>{code} · Side {page}</strong>
      <small class="stock-status" data-stock-code="{code}">Sjekker lagerstatus ...</small></a>'''


def hotspot(product: dict[str, object]) -> str:
    code = html.escape(str(product["code"]))
    return (
        f'<a class="hotspot" href="https://tupperware-eu.com/no/search?q={code}" '
        f'target="tupperware_shop" data-code="{code}" aria-label="{code}" title="{code}" '
        f'style="left:{product["left"]:.4f}%;top:{product["top"]:.4f}%;'
        f'width:{product["width"]:.4f}%;height:{product["height"]:.4f}%;"></a>'
    )


def build_html(pages: list[dict[str, int | str]], products: list[dict[str, object]]) -> None:
    template = (ROOT / "september-katalog" / "index.html").read_text(encoding="utf-8")
    by_page: dict[int, list[dict[str, object]]] = {}
    for product in products:
        by_page.setdefault(int(product["page"]), []).append(product)
    ratio = float(pages[0]["width"]) / float(pages[0]["height"])
    sections = []
    for page in pages:
        page_number = int(page["page"])
        page_products = by_page.get(page_number, [])
        sections.append(
            f'''<section class="page" id="page-{page_number}" data-page="{page_number}">
              <div class="page-head"><span>Side {page_number}</span><span>{len(page_products)} lenker</span></div>
              <div class="sheet" style="--page-ratio:{ratio:.8f};">
                <img loading="lazy" decoding="async" src="/tw-host-vinter-2026-27/pages/{page["file"]}"
                  width="{page["width"]}" height="{page["height"]}" alt="Tupperware høst/vinter side {page_number}">
                {''.join(hotspot(product) for product in page_products)}
                {OVERLAYS.get(page_number, '')}
              </div>
            </section>'''
        )
    rows = "\n".join(product_row(product) for product in products)
    main = f'<main><aside>{rows}</aside><div class="pages">{"".join(sections)}</div></main>'
    start, end = template.index("  <main>"), template.index("  </main>") + len("  </main>")
    page_html = template[:start] + "  " + main + template[end:]
    page_html = page_html.replace("Tupperware septemberkatalog", "Tupperware høst/vinter 2026-2027")
    page_html = page_html.replace("Septemberkatalog", "Høst/vinter-katalog")
    page_html = page_html.replace("septemberkatalog", "høst/vinter-katalog")
    page_html = page_html.replace(
        "</style>",
        '''
    .translation-panel { position:absolute; z-index:3; padding:2.1%; background:rgba(249,248,239,.96); color:#262626; border-left:6px solid #d96822; box-shadow:0 8px 22px rgba(0,0,0,.14); font-size:clamp(9px,1.12vw,16px); line-height:1.3; pointer-events:none; }
    .translation-panel h2,.translation-panel h3,.translation-panel p { margin:0 0 .65em; }
    .translation-panel h2 { font-size:1.65em; }
    .translation-panel h3 { font-size:1.05em; }
    .cover-translation { left:12%; top:13%; width:76%; text-align:center; background:rgba(30,24,18,.78); color:#fff; border:0; }
    .cover-translation strong,.cover-translation span { display:block; }
    .cover-translation strong { font-size:1.7em; }
    .page-two-translation { left:40%; top:5%; width:54%; height:86%; font-size:clamp(9px,1.28vw,17px); }
    .full-text-translation { left:7%; top:6%; width:86%; height:84%; }
    .join-translation { height:61%; }
    .recipe-intro { left:4%; top:48%; width:92%; }
    .recipe-bottom { left:32%; top:62%; width:63%; height:31%; }
    .recipe-top { left:31%; top:7%; width:64%; height:46%; }
    .recipe-lower { left:7%; top:61%; width:62%; height:29%; }
    .hummus-translation { left:5%; top:4%; width:45%; height:26%; }
    .consultant-details { position:absolute; z-index:3; left:16%; top:50%; width:62%; min-height:24%; display:flex; flex-direction:column; justify-content:center; gap:.7em; padding:3%; background:rgba(249,248,239,.97); color:#262626; text-align:center; font-size:clamp(11px,1.7vw,22px); }
    .consultant-details strong { font-size:1.25em; text-transform:uppercase; }
        </style>''',
    )
    page_html = page_html.replace(
        'consultantName.textContent = result.name || result.consultant?.display_name || reference;',
        '''consultantName.textContent = result.name || result.consultant?.display_name || reference;
        const catalogName = document.querySelector("#catalogConsultantName");
        const catalogEmail = document.querySelector("#catalogConsultantEmail");
        const catalogPhone = document.querySelector("#catalogConsultantPhone");
        if (catalogName) catalogName.textContent = result.name || result.consultant?.display_name || reference;
        if (catalogEmail) catalogEmail.textContent = result.email || "";
        if (catalogPhone) catalogPhone.textContent = result.phone || "";''',
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "index.html").write_text(page_html, encoding="utf-8")
    (OUTPUT / "products.json").write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    pages = render_pages()
    products = extract_products()
    build_html(pages, products)
    print(f"pages={len(pages)} products={len(products)} output={OUTPUT}")


if __name__ == "__main__":
    main()
