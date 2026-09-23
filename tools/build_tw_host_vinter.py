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
    1: '''<div class="translation-panel cover-translation"><strong>Høst 2026 - vinter 2027</strong></div>''',
    2: '''<div class="translation-panel page-two-translation"><h2>Velkommen til den nye Tupperware-katalogen!</h2><p>Høsten senker seg, dagene blir kjøligere og de gode stundene sammen blir enda viktigere.</p><p>Oppdag vårt nye høst- og vinterutvalg for matlaging, oppbevaring, organisering og hyggelige måltider. Her finner du både velkjente favoritter og nye løsninger som gjør hverdagen enklere.</p><p>Enten du liker hjemmelaget mat, smarte løsninger på farten eller orden hjemme, er katalogen full av ideer for sesongen.</p><p><strong>God fornøyelse!</strong></p></div>''',
    3: '''<div class="translation-panel full-text-translation"><h2>Gjør hverdagen enklere</h2><h3>Smart og uunnværlig</h3><p>Tupperware er mer enn oppbevaringsbokser. Produktene er laget for hverdagens behov, med gjennomtenkt funksjon og et moderne uttrykk.</p><h3>Klar for alt</h3><p>Effektiv og intuitiv organisering hjelper deg med oppbevaring, matlaging og forberedelser.</p><h3>Utviklet for å gjøre en forskjell</h3><p>Kvalitet, funksjon og holdbarhet har stått sentralt helt fra starten.</p><h3>Kjøp én gang, bruk lenge</h3><p>Produkter som varer bidrar til mindre matsvinn og færre engangsprodukter.</p></div>''',
    4: '''<div class="translation-panel full-text-translation join-translation"><h2>Bli med</h2><h3>Bli kjent med produktene</h3><p>Start med nyttige Tupperware-produkter og få tilgang til arrangementer, gaver og gode tilbud.</p><h3>Jobb der du vil</h3><p>Arbeid fysisk eller digitalt, og legg opp dagene slik det passer deg.</p><h3>Møt nye mennesker</h3><p>Bli del av et engasjert fellesskap og skap nye kontakter.</p><h3>Kombiner jobb og fritid</h3><p>Du bestemmer selv arbeidstid og ambisjonsnivå.</p><h3>Provisjon fra første salg</h3><p>Du tjener provisjon helt fra starten.</p><h3>Jobb digitalt</h3><p>Bygg nettverk, skap gode kunderelasjoner og selg på nettet.</p></div><div class="translation-panel contents-translation"><strong>Innhold</strong><div><span>3 Tupperware</span><span>4 Bli med</span><span>5 Tilbakevendende og nye produkter</span><span>8 Frysing</span><span>8 Flerbruk</span><span>9 Kjøleskap</span><span>12 Oppbevaring</span><span>14 Baking</span><span>16 Oppskrifter</span><span>18 Ekstra praktisk</span><span>20 Kjøkkenredskaper</span><span>23 Barn</span><span>24 Mikrobølgeovn</span><span>26 Matlaging</span><span>28 Oppskrifter</span><span>29 Servering</span><span>30 Drikke</span><span>31 Big T</span><span>32 På farten</span><span>33 Pleie og rengjøring</span><span>34 Garanti</span></div></div>''',
    5: '''<div class="translation-panel page-five-translation"><h2>TILBAKEVENDENDE<br><strong>NYE PRODUKTER</strong></h2><p>Når behovene dine utvikler seg, gjør sortimentet vårt det samme.</p><p>Oppdag produkter som gjør comeback, og nye produkter som er utviklet for å gjøre hverdagen enklere.</p><p>Inspirerende løsninger og favoritter å dele - kanskje finner du din neste favoritt på de følgende sidene.</p></div>''',
    16: '''<div class="translation-panel recipe-intro"><strong>Et magisk måltid</strong><span>Én meny, mange muligheter til å glede. Lett å tilberede og elegant å servere - perfekt for familie og venner.</span></div><div class="translation-panel recipe-bottom"><h3>Butternutgresskarsuppe med parmesan-krem</h3><p><strong>Til 4 personer:</strong> 2 sjalottløk, 15 ml olje, 600 g butternutgresskar, 300 ml varmt vann, 1 grønnsaksbuljongterning, 400 ml kald kremfløte, 30 g parmesan, salt og pepper.</p><p>Hakk løken og varm den med olje. Tilsett skrelt gresskar i terninger, buljong og vann. Kok til mørt og mos. Pisk fløten, bland inn parmesan og smak til. Server suppen med parmesan-kremen.</p></div>''',
    17: '''<div class="translation-panel recipe-top"><h3>Pai med confitert and og sopp</h3><p><strong>Til 4 personer:</strong> andelår, sjalottløk, sjampinjong, hasselnøtter, persille, butterdeig, egg, salt og pepper.</p><p>Varm andelårene, fjern bein og skinn og riv kjøttet. Hakk løk og sopp, stek blandingen og tilsett and, nøtter og persille. Legg fyllet mellom to butterdeigplater, forsegl kantene, pensle med egg og stek ved 200 °C i omtrent 35 minutter.</p></div><div class="translation-panel recipe-lower"><h3>Bakte epler med nougat og sprø brioche</h3><p><strong>Til 4 personer:</strong> 4 epler, 80 g myk nougat, 4 skiver brioche, karamellsaus og 150 ml kremfløte.</p><p>Fjern kjernehuset og fyll eplene med nougat. Stek uten lokk i 40-45 minutter ved 180 °C. Rist brioche, varm karamell og fløte, og server eplene med saus og brioche.</p></div>''',
    18: '''<div class="translation-panel hummus-translation"><h3>Hjemmelaget hummus</h3><p>Kjør 120 g kokte, skylte kikerter sammen med et halvt hvitløksfedd. Tilsett 1 ss olivenolje, 1 ts sitronsaft og 1 ss soyasaus. Kjør til jevn konsistens og oppbevar kjølig.</p><p><strong>Variant:</strong> Tilsett 80 g kokt rødbete.</p></div>''',
    28: '''<div class="recipe-cover recipe-28-top-cover"></div><div class="translation-panel recipe-28-top"><h3>Foie gras-terrine</h3><p><strong>Til 8 personer:</strong> ca. 500 g renset foie gras, salt, pepper, krydder og 3 ss portvin, Sauternes eller Armagnac.</p><p>Del foie gras i to, krydre og mariner én time i kjøleskapet. Damp eller varm i Ultrapro cocotte 500 ml som beskrevet, avkjøl og sett kjølig i 24-48 timer.</p></div><div class="translation-panel recipe-28-middle"><h3>Kyllingrillettes</h3><p>Kjør 80 g kokt kyllingbryst og koriander i SuperSonic Chopper compact. Tilsett 3-4 ss majones, salt og pepper. Kjør sammen igjen.</p><p><strong>Variant:</strong> Bruk 75 g kokt laks og en halv sjalottløk.</p></div><div class="recipe-cover recipe-28-bottom-cover"></div><div class="translation-panel recipe-28-bottom"><h3>Pralinkake</h3><p><strong>Til 8 personer:</strong> 300 g pralinesjokolade, 100 g smør, 4 egg, 50 g sukker, vaniljesukker, 200 g kastanjekrem, 60 g hasselnøttpulver og ca. 85 g mel.</p><p>Smelt sjokolade og smør. Pisk egg, sukker og vaniljesukker. Bland inn resten, hell røren i MicroCook round 2,25 l og stek tildekket i mikrobølgeovn. La hvile, vend ut og pynt med sjokolade og nøtter.</p></div><div class="recipe-cover recipe-28-footer">28 | Oppskrifter</div>''',
    34: '''<div class="translation-panel warranty-translation"><h2>Lovbestemte og kommersielle garantier</h2><p>Tupperware-produkter omfattes av garanti mot material- og produksjonsfeil som oppstår ved normal bruk i henhold til bruksanvisningen.</p><p>Garantien dekker ikke skader som skyldes uforsiktig bruk, feil bruk eller annen behandling produktet ikke er beregnet for.</p><p>Dersom produktet omfattes av garanti, gjelder garantibetingelsene for landet ditt. Tupperware-produkter er laget for å brukes igjen og igjen. Produkter du ikke lenger trenger, bør leveres til forsvarlig gjenbruk eller gjenvinning.</p></div>''',
    36: '''<div class="consultant-details" id="catalogConsultantDetails"><div class="consultant-contact"><strong>Din Tupperware-konsulent</strong><span id="catalogConsultantName">Navn lastes inn ...</span><span id="catalogConsultantEmail"></span><span id="catalogConsultantPhone"></span></div><div class="consultant-qrs"><a id="catalogStoreLink" target="tupperware_shop"><canvas id="catalogStoreQr"></canvas><span>Handle hos konsulenten</span></a><a id="catalogDigitalLink"><canvas id="catalogDigitalQr"></canvas><span>Åpne den digitale katalogen</span></a></div></div>''',
}

HEADING_TRANSLATIONS = {
    "RETURNS": "TILBAKEVENDENDE",
    "NEW PRODUCTS": "NYE PRODUKTER",
    "STORAGE": "OPPBEVARING",
    "PREPARATION": "FORBEREDELSE",
    "COOKING": "MATLAGING",
    "HYDRATION & CLEANING": "DRIKKE OG RENGJØRING",
    "FREEZING": "FRYSING",
    "MULTI-PURPOSE": "FLERBRUK",
    "KEEP FRESH": "HOLD MATEN FRISK",
    "OPTIMAL FRESHNESS": "OPTIMAL FRISKHET",
    "ORGANISED PANTRY": "RYDDIG MATBOD",
    "BAKING MOMENTS": "BAKEGLEDE",
    "MAGICAL DINNER": "ET MAGISK MÅLTID",
    "ULTRA PRACTICAL": "EKSTRA PRAKTISK",
    "KITCHEN TOOLS": "KJØKKENREDSKAPER",
    "MICROWAVE": "MIKROBØLGEOVN",
    "SERVING": "SERVERING",
    "HYDRATION": "DRIKKE",
    "ON-THE-GO": "PÅ FARTEN",
    "CARE & CLEANING": "PLEIE OG RENGJØRING",
    "WARRANTY": "GARANTI",
}

MANUAL_PRODUCTS = {
    5: [
        ("11184105", "Modular bowl 630 ml", 7, 39, 22, 17),
        ("11184136", "Modular bowl 1 l", 29, 39, 22, 17),
        ("11184135", "Modular bowl 1,5 l", 51, 39, 21, 17),
        ("11184137", "Modular bowl 2 l", 72, 39, 21, 17),
        ("11186044", "Set Freezer mates 450 ml (4)", 7, 56, 22, 18),
        ("11184913", "Ventsmart low 1,8 l", 29, 56, 22, 18),
        ("11183903", "Refrigerator bowl 380 ml (4)", 51, 56, 21, 18),
        ("11184200", "Slim line pitcher 2 l", 72, 56, 21, 18),
        ("11184167", "One touch fresh 540 ml", 15, 74, 26, 17),
        ("11184177", "One touch fresh 1,1 l", 41, 74, 25, 17),
        ("11184104", "One touch fresh 1,8 l", 66, 74, 25, 17),
    ]
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


def _non_overlapping_cells(anchors: list[dict[str, object]], page_width: float, page_height: float) -> None:
    """Turn article-number anchors into disjoint product cards that include their images."""
    rows: list[list[dict[str, object]]] = []
    for anchor in sorted(anchors, key=lambda item: (float(item["anchor_y"]), float(item["anchor_x"]))):
        if not rows or abs(float(anchor["anchor_y"]) - sum(float(x["anchor_y"]) for x in rows[-1]) / len(rows[-1])) > 25:
            rows.append([anchor])
        else:
            rows[-1].append(anchor)

    row_bottoms = [max(float(item["anchor_bottom"]) for item in row) + 4 for row in rows]
    for row_index, row in enumerate(rows):
        row.sort(key=lambda item: float(item["anchor_x"]))
        bottom = min(page_height - 2, row_bottoms[row_index])
        if row_index == 0:
            gap = row_bottoms[1] - row_bottoms[0] if len(rows) > 1 else 105
            top = max(2, bottom - min(118, max(58, gap * .92)))
        else:
            top = row_bottoms[row_index - 1] + 2
        centers = [float(item["anchor_x"]) for item in row]
        boundaries = [2.0]
        boundaries.extend((centers[index] + centers[index + 1]) / 2 for index in range(len(centers) - 1))
        boundaries.append(page_width - 2.0)
        for index, item in enumerate(row):
            left = boundaries[index] + .8
            right = boundaries[index + 1] - .8
            item.update(
                left=left / page_width * 100,
                top=top / page_height * 100,
                width=max(1, right - left) / page_width * 100,
                height=max(1, bottom - top) / page_height * 100,
            )


def extract_products() -> list[dict[str, object]]:
    products: list[dict[str, object]] = []
    seen: set[tuple[int, str]] = set()
    code_pattern = re.compile(r"^(?:\d{7,8}|[A-Z]{1,4}\d{3,}[A-Z0-9]*)$")
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            width, height = float(page.width), float(page.height)
            words = page.extract_words(x_tolerance=2, y_tolerance=4, use_text_flow=False)
            page_products: list[dict[str, object]] = []
            for word in words:
                code = re.sub(r"[^A-Z0-9]", "", str(word.get("text", "")).upper())
                if not code_pattern.fullmatch(code) or (page_number, code) in seen:
                    continue
                seen.add((page_number, code))
                x0, x1 = float(word["x0"]), float(word["x1"])
                bottom = float(word["bottom"])
                page_products.append(
                    {
                        "page": page_number,
                        "code": code,
                        "name": product_name(words, word),
                        "anchor_x": (x0 + x1) / 2,
                        "anchor_y": bottom,
                        "anchor_bottom": bottom,
                    }
                )
            _non_overlapping_cells(page_products, width, height)
            products.extend(page_products)
    for page, entries in MANUAL_PRODUCTS.items():
        for code, name, left, top, width, height in entries:
            products.append({"page": page, "code": code, "name": name, "left": left, "top": top, "width": width, "height": height})
    return products


def extract_heading_overlays() -> dict[int, str]:
    overlays: dict[int, list[str]] = {}
    skip_pages = {1, 2, 3, 4, 5, 16, 17, 18, 28, 34, 36}
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            if page_number in skip_pages:
                continue
            for english, norwegian in HEADING_TRANSLATIONS.items():
                for match in page.search(english, regex=False, case=False):
                    x0, x1 = float(match["x0"]), float(match["x1"])
                    top, bottom = float(match["top"]), float(match["bottom"])
                    pad_x, pad_y = 4.0, 2.0
                    overlays.setdefault(page_number, []).append(
                        f'<div class="heading-translation" style="left:{max(0, x0-pad_x)/float(page.width)*100:.3f}%;'
                        f'top:{max(0, top-pad_y)/float(page.height)*100:.3f}%;'
                        f'width:{(min(float(page.width), x1+pad_x)-max(0, x0-pad_x))/float(page.width)*100:.3f}%;'
                        f'height:{(bottom-top+2*pad_y)/float(page.height)*100:.3f}%">{html.escape(norwegian)}</div>'
                    )
    return {page: "".join(items) for page, items in overlays.items()}


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
    heading_overlays = extract_heading_overlays()
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
                {heading_overlays.get(page_number, '')}
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
        "</head>",
        '  <script src="https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js"></script>\n</head>',
    )
    page_html = page_html.replace(
        '<button id="toggle" type="button">Vis lenkeflater</button>',
        '<button id="toggle" type="button">Vis lenkeflater</button><div class="print-tools"><input id="printPages" type="text" inputmode="numeric" placeholder="Sider, f.eks. 1-5,36" aria-label="Sider som skal skrives ut"><button id="printCatalog" type="button">Skriv ut</button></div>',
    )
    page_html = page_html.replace(
        "</style>",
        '''
    .translation-panel { position:absolute; z-index:3; padding:2.1%; background:#f9f8ef; color:#262626; border-left:6px solid #d96822; box-shadow:0 8px 22px rgba(0,0,0,.14); font-size:clamp(9px,1.12vw,16px); line-height:1.3; pointer-events:none; overflow:hidden; }
    .translation-panel h2,.translation-panel h3,.translation-panel p { margin:0 0 .65em; }
    .translation-panel h2 { font-size:1.65em; }
    .translation-panel h3 { font-size:1.05em; }
    .cover-translation { left:27%; top:87%; width:46%; height:7%; display:flex; align-items:center; justify-content:center; padding:1%; text-align:center; background:#fff; color:#27221e; border:2px solid #d45a3c; box-shadow:none; }
    .cover-translation strong,.cover-translation span { display:block; }
    .cover-translation strong { font-size:1.7em; }
    .page-two-translation { left:40%; top:5%; width:54%; height:86%; font-size:clamp(9px,1.28vw,17px); }
    .full-text-translation { left:7%; top:6%; width:86%; height:84%; }
    .join-translation { height:61%; }
    .contents-translation { left:5%; top:70%; width:90%; height:29%; background:#653925; color:#fff; border-left-color:#f5d995; }
    .contents-translation strong { display:block; font-size:1.35em; margin-bottom:.45em; }
    .contents-translation div { display:grid; grid-template-columns:1fr 1fr; gap:.18em 1.5em; font-size:.82em; }
    .page-five-translation { left:4%; top:1%; width:92%; height:32%; background:#fff; border-left-color:#008c82; }
    #page-5 .sheet::after { content:"OPPBEVARING"; position:absolute; z-index:4; left:0; top:33%; width:100%; padding:.45em 0; background:#efeee2; color:#202522; text-align:center; font-weight:800; font-size:clamp(13px,2.2vw,30px); pointer-events:none; }
    .recipe-intro { left:4%; top:48%; width:92%; }
    .recipe-bottom { left:32%; top:62%; width:63%; height:31%; }
    .recipe-top { left:31%; top:7%; width:64%; height:46%; }
    .recipe-lower { left:7%; top:61%; width:62%; height:29%; }
    .hummus-translation { left:5%; top:4%; width:45%; height:26%; }
    .recipe-28-top { left:31%; top:5%; width:64%; height:30%; }
    .recipe-28-middle { left:31%; top:38%; width:64%; height:18%; }
    .recipe-28-bottom { left:5%; top:58%; width:63%; height:34%; }
    .recipe-cover { position:absolute; z-index:2; background:#fff; pointer-events:none; }
    .recipe-28-top-cover { left:3%; top:24%; width:92%; height:13%; }
    .recipe-28-bottom-cover { left:3%; top:80%; width:92%; height:13%; }
    .recipe-28-footer { left:3%; top:93%; width:92%; height:5%; display:flex; align-items:center; justify-content:center; font-weight:700; }
    .warranty-translation { left:7%; top:11%; width:86%; height:42%; background:#fff; border-left-color:#008c82; }
    .heading-translation { position:absolute; z-index:4; display:flex; align-items:center; padding:0 .35em; background:#f1efe4; color:#202522; font-weight:800; line-height:1; text-transform:uppercase; font-size:clamp(8px,1.15vw,17px); pointer-events:none; white-space:nowrap; }
    .consultant-details { position:absolute; z-index:3; left:14%; top:46.5%; width:73%; height:34%; display:grid; grid-template-columns:1fr 1.35fr; align-items:center; gap:3%; padding:3%; background:#f3f4e8; color:#262626; text-align:center; font-size:clamp(10px,1.45vw,20px); border-radius:7%; }
    .consultant-contact { display:flex; flex-direction:column; gap:.55em; min-width:0; }
    .consultant-details strong { font-size:1.16em; text-transform:uppercase; }
    .consultant-details span { overflow-wrap:anywhere; }
    .consultant-qrs { display:grid; grid-template-columns:1fr 1fr; gap:5%; align-items:start; }
    .consultant-qrs a { display:grid; gap:.55em; color:#262626; text-decoration:none; font-weight:700; font-size:.72em; }
    .consultant-qrs canvas { display:block; width:100% !important; height:auto !important; aspect-ratio:1; background:#fff; padding:5%; }
    .print-tools { display:flex; gap:8px; align-items:center; }
    .print-tools input { width:190px; }
    .bar { grid-template-columns:minmax(210px,1fr) auto auto auto; }
    @media print {
      @page { size:A5 portrait; margin:0; }
      body { background:#fff; }
      header, aside, .page-head { display:none !important; }
      main, .pages { display:block; width:100%; max-width:none; margin:0; padding:0; }
      .page { display:block; width:148mm; height:210mm; margin:0; border:0; border-radius:0; box-shadow:none; overflow:hidden; break-after:page; page-break-after:always; }
      .page.print-excluded { display:none !important; }
      .sheet { width:148mm; height:210mm; }
      .hotspot { display:none !important; }
    }
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
    page_html = page_html.replace(
        'consultantReady = true;',
        '''const storeUrl = `https://tupperware-eu.com/no/?ref=${encodeURIComponent(reference)}`;
        const digitalUrl = `${window.location.origin}/tw-host-vinter-2026-27/?ref=${encodeURIComponent(reference)}`;
        const storeLink = document.querySelector("#catalogStoreLink");
        const digitalLink = document.querySelector("#catalogDigitalLink");
        if (storeLink) storeLink.href = storeUrl;
        if (digitalLink) digitalLink.href = digitalUrl;
        if (window.QRCode) {
          const qrOptions = { width: 220, margin: 1, color: { dark: "#172124", light: "#ffffff" } };
          window.QRCode.toCanvas(document.querySelector("#catalogStoreQr"), storeUrl, qrOptions);
          window.QRCode.toCanvas(document.querySelector("#catalogDigitalQr"), digitalUrl, qrOptions);
        }
        consultantReady = true;''',
        1,
    )
    page_html = page_html.replace(
        'prepareConsultant();',
        '''function selectedPrintPages(value) {
      const selected = new Set();
      String(value || "").split(",").map(part => part.trim()).filter(Boolean).forEach((part) => {
        const match = part.match(/^(\\d+)\\s*-\\s*(\\d+)$/);
        if (match) {
          const start = Math.max(1, Math.min(36, Number(match[1])));
          const end = Math.max(1, Math.min(36, Number(match[2])));
          for (let page = Math.min(start, end); page <= Math.max(start, end); page += 1) selected.add(page);
        } else if (/^\\d+$/.test(part)) {
          const page = Number(part);
          if (page >= 1 && page <= 36) selected.add(page);
        }
      });
      return selected;
    }
    document.querySelector("#printCatalog")?.addEventListener("click", () => {
      const selected = selectedPrintPages(document.querySelector("#printPages")?.value);
      document.querySelectorAll(".page").forEach((page) => {
        page.classList.toggle("print-excluded", selected.size > 0 && !selected.has(Number(page.dataset.page)));
      });
      window.print();
      setTimeout(() => document.querySelectorAll(".page").forEach(page => page.classList.remove("print-excluded")), 500);
    });
    prepareConsultant();''',
        1,
    )
    page_html = page_html.replace(
        'function updateStockStatus(code, product) {',
        '''function updateStockStatus(code, product) {
      const directUrl = product && (product.url || product.sourceUrl || product.canonicalUrl);
      if (directUrl) {
        const reference = cleanReference(new URLSearchParams(window.location.search).get("ref"));
        document.querySelectorAll(`a[data-code="${code}"]`).forEach((link) => {
          link.href = norwegianShopUrl(directUrl, reference);
        });
      }''',
    )
    page_html = page_html.replace(
        'async function prepareConsultant() {',
        '''function renderCatalogQrs(reference) {
      if (!reference) return;
      const storeUrl = `https://tupperware-eu.com/no/?ref=${encodeURIComponent(reference)}`;
      const digitalUrl = `${window.location.origin}/tw-host-vinter-2026-27/?ref=${encodeURIComponent(reference)}`;
      const storeLink = document.querySelector("#catalogStoreLink");
      const digitalLink = document.querySelector("#catalogDigitalLink");
      if (storeLink) storeLink.href = storeUrl;
      if (digitalLink) digitalLink.href = digitalUrl;
      if (window.QRCode) {
        const qrOptions = { width: 220, margin: 1, color: { dark: "#172124", light: "#ffffff" } };
        window.QRCode.toCanvas(document.querySelector("#catalogStoreQr"), storeUrl, qrOptions);
        window.QRCode.toCanvas(document.querySelector("#catalogDigitalQr"), digitalUrl, qrOptions);
      }
    }
    async function prepareConsultant() {''',
        1,
    )
    page_html = page_html.replace(
        'if (!reference) { consultantLine.classList.add("invalid"); consultantName.textContent = "ingen konsulent valgt"; return; }',
        'if (!reference) { consultantLine.classList.add("invalid"); consultantName.textContent = "ingen konsulent valgt"; return; }\n      renderCatalogQrs(reference);',
        1,
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    page_html = "\n".join(line.rstrip() for line in page_html.splitlines()) + "\n"
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
