from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import pdfplumber
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PDF = Path(r"C:\Users\janro\Downloads\NO - October Leaflet - 10-2026.pdf")
OUT = ROOT / "oktober-katalog"
PAGES = OUT / "pages"
POPPLER = Path(
    r"C:\Users\janro\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)

TRANSLATIONS = {
    1: [
        {
            "class": "cover-badge",
            "text": "Gyldig kun i Norge<br>1.-30. september 2026",
            "style": "left:62%;top:83%;width:31%;",
        },
        {
            "class": "cover-title",
            "text": "80 ar med historie!",
            "style": "left:10%;top:32%;width:62%;",
        },
        {
            "class": "cover-subtitle",
            "text": "Septemberkampanje",
            "style": "left:52%;top:17%;width:34%;",
        },
    ],
    2: [
        {
            "class": "note-panel",
            "text": "<strong>Jobb der du vil</strong><br>Selg fysisk eller digitalt, og styr hverdagen selv.",
            "style": "left:8%;top:10%;width:36%;",
        },
        {
            "class": "note-panel",
            "text": "<strong>Provisjon fra forste salg</strong><br>Du tjener provisjon pa salgene dine helt fra starten.",
            "style": "left:56%;top:10%;width:34%;",
        },
        {
            "class": "note-panel",
            "text": "<strong>Fleksibel hverdag</strong><br>Du bestemmer nar og hvordan du vil jobbe.",
            "style": "left:8%;top:53%;width:36%;",
        },
        {
            "class": "note-panel",
            "text": "<strong>Bygg nettverket ditt</strong><br>Del produkter, tips og ideer med kundene dine.",
            "style": "left:56%;top:53%;width:34%;",
        },
    ],
    3: [
        {
            "class": "story-panel",
            "text": "<strong>De beste stundene deles hjemme.</strong><br>I 80 ar har Tupperware-party samlet mennesker rundt matglede, tips og inspirasjon. Som vert kan du fa vertinnegaver basert pa salget pa partyet.",
            "style": "left:9%;top:12%;width:45%;",
        },
    ],
    4: [
        {
            "class": "note-panel compact",
            "text": "<strong>Oppskrift</strong><br>Vask, skrell og kutt gronnsakene. Damp dem i Micro Urban large, og server med en enkel saus og urter.",
            "style": "left:7%;top:8%;width:44%;",
        },
    ],
    5: [
        {
            "class": "note-panel compact",
            "text": "<strong>Micro Urban large</strong><br>Damp fisk, kjott og gronnsaker pa fa minutter. Kan ogsa brukes til pasta, ris og korn.",
            "style": "left:7%;top:74%;width:46%;",
        },
    ],
    6: [
        {
            "class": "note-panel compact",
            "text": "<strong>Produkter</strong><br>Klikk pa en produktblokk for a apne varen i norsk Tupperware-nettbutikk.",
            "style": "left:8%;top:5%;width:42%;",
        },
    ],
    7: [
        {
            "class": "note-panel compact",
            "text": "<strong>Kjoleskap og oppbevaring</strong><br>Praktiske bokser og serveringsprodukter for bedre oversikt i hverdagen.",
            "style": "left:7%;top:7%;width:43%;",
        },
    ],
    8: [
        {
            "class": "note-panel compact",
            "text": "<strong>Til matlaging</strong><br>Se kampanjeproduktene og klikk pa produktblokkene for pris og bestilling.",
            "style": "left:6%;top:7%;width:44%;",
        },
    ],
    9: [
        {
            "class": "note-panel compact",
            "text": "<strong>Septembertilbud</strong><br>Produktlenkene er personlige og gar via valgt konsulent.",
            "style": "left:7%;top:7%;width:43%;",
        },
    ],
    10: [
        {
            "class": "note-panel compact dark",
            "text": "<strong>80 ars jubileum</strong><br>Utvalgte produkter og kampanjer for september.",
            "style": "left:7%;top:7%;width:42%;",
        },
    ],
    11: [
        {
            "class": "note-panel compact",
            "text": "<strong>Flere favoritter</strong><br>Klikk pa produktblokkene for a finne varen i norsk nettbutikk.",
            "style": "left:7%;top:7%;width:43%;",
        },
    ],
    12: [
        {
            "class": "note-panel compact",
            "text": "<strong>Servering og oppbevaring</strong><br>Septemberprodukter med personlige lenker til nettbutikken.",
            "style": "left:7%;top:7%;width:45%;",
        },
    ],
    13: [
        {
            "class": "note-panel compact",
            "text": "<strong>Kampanjeprodukter</strong><br>Bruk lenkeflatene for a apne riktig sok i nettbutikken.",
            "style": "left:7%;top:7%;width:43%;",
        },
    ],
    14: [
        {
            "class": "note-panel compact",
            "text": "<strong>Tupperware Norge</strong><br>Del katalogen med kunder via din personlige konsulentlenke.",
            "style": "left:8%;top:74%;width:45%;",
        },
    ],
}

OCTOBER_OVERLAYS = {
    1: '<div class="translation october-cover">Lag høstmat på under 30 minutter!</div>',
    4: '''<div class="translation october-callout callout-colander"><strong>1 dørslag</strong><span>Ideelt til kjøtt: fettet renner av, eller smak kan trekke ned i tilbehøret under.</span></div><div class="translation october-callout callout-cone"><strong>1 kjegle</strong><span>Gir jevnere tilberedning av store mengder i beholderen på 3 liter.</span></div><div class="translation october-callout callout-lids"><strong>2 fleksible lokk</strong><span>Til oppbevaring i kjøleskap og fryser, og til transport.</span></div><div class="translation october-callout callout-combo"><strong>Med Combo Micro 3 blir et komplett måltid ferdig på 30 minutter.</strong><span>Tilbered tre retter samtidig, uten at de kommer i kontakt med hverandre.</span></div><div class="translation october-blog">Oppskriften på sjokolade- og kirsebærkake finner du på bloggen vår.</div>''',
    5: '<div class="translation october-heading">Høsten, den raske veien!</div>',
    7: '''<div class="translation october-recipes"><article><h2>HVITLØKSGULRØTTER</h2><h3>Ingredienser til 4 personer</h3><p>4 store gulrøtter, 3 hvitløksfedd, 1 bunt persille, 30 g smør, salt og pepper.</p><h3>Slik gjør du</h3><ol><li>Skrell gulrøttene og skjær dem i skiver med MandoChef.</li><li>Hakk hvitløk og persille i SuperSonic Chopper compact.</li><li>Legg gulrøttene i Combo Micro 3, tilsett vann og tilbered i mikrobølgeovn til de er møre.</li><li>Bland inn smør, hvitløk og persille. Smak til med salt og pepper.</li></ol></article><article><h2>KJØTTFYLT KÅL</h2><h3>Ingredienser til 4 personer</h3><p>1 grønnkål eller savoykål, 2 løk, 2 hvitløksfedd, 500 g kjøttdeig, 200 g kokt ris, persille, salt og pepper.</p><h3>Slik gjør du</h3><ol><li>Løsne kålbladene og forvell dem.</li><li>Hakk løk, hvitløk og persille. Bland med kjøttdeig og ris.</li><li>Fordel fyllet på bladene, brett sammen og legg pakkene i Combo Micro 3.</li><li>Tilbered i mikrobølgeovn til kjøttet er gjennomstekt. La retten hvile før servering.</li></ol></article><article><h2>PÆREKAKE</h2><h3>Ingredienser til 6 personer</h3><p>3 pærer, 150 g mel, 100 g sukker, 2 egg, 100 ml melk, 80 g smør og 1 ts bakepulver.</p><h3>Slik gjør du</h3><ol><li>Skrell pærene og skjær dem i skiver.</li><li>Pisk egg og sukker. Bland inn melk, smeltet smør, mel og bakepulver.</li><li>Hell røren i en egnet form og fordel pærene over.</li><li>Stek til kaken er gyllen og gjennomstekt. Avkjøl litt før servering.</li></ol></article></div>''',
    8: '<div class="translation october-heading">Høsten, skåret til perfeksjon!</div>',
    9: '<div class="translation october-heading">Sett smak på høsten</div>',
    11: '<div class="translation october-heading">Gjør deg klar for høsten på en stor måte!</div>',
    12: '<div class="translation october-heading october-heading-left">Grøss ...</div>',
    13: '<div class="translation october-heading">... og Halloween går POP!</div>',
    14: '<div class="translation october-heading october-heading-left">Høsten, ryddig og organisert!</div>',
}

OCTOBER_OVERLAYS[7] = '''<div class="translation recipe-sheet-original">
<section class="recipe-row recipe-carrots"><h2>HVITLØKSGULRØTTER</h2><div class="recipe-columns"><div class="ingredients"><h3>Ingredienser til 4 personer</h3><ul><li>500 g gulrøtter</li><li>Bladene fra 4 persillekvister</li><li>2 hvitløksfedd</li><li>20 g smør i små terninger</li><li>Krydder</li><li>2 ss vann eller grønnsaksbuljong</li></ul></div><div class="method"><ol><li>Skrell de vaskede gulrøttene og skjær dem i skiver med MandoChef, innstilling 1. Legg dem i 3-litersformen.</li><li>Hakk persillebladene i SuperSonic Chopper Compact og bland dem med gulrøttene.</li><li>Press de skrelte hvitløksfeddene uten kime over gulrøttene med Garlic Star.</li><li>Tilsett resten av ingrediensene og bland godt.</li><li>Stable formene i Combo Micro 3 og tilbered i 25 minutter ved 600 watt. La hvile i 5 minutter.</li><li>Server sammen med den kjøttfylte kålen.</li></ol></div></div><div class="individual"><strong>Tilberedt alene</strong><span>Tilbered med lokk i ca. 7 minutter ved 600 watt. Rør halvveis.</span></div></section>
<section class="recipe-row recipe-cabbage"><h2>KJØTTFYLT KÅL</h2><div class="recipe-columns"><div class="ingredients"><h3>Ingredienser til 4 personer</h3><ul><li>2 løk (ca. 300 g)</li><li>2 ts persille</li><li>1 hvitløksfedd, skrelt</li><li>¼ bunt bladpersille, bladene plukket av</li><li>100 g mellomgrov couscous</li><li>200 g pølsefarse</li><li>Salt og pepper</li><li>1 egg</li><li>1 kinakål (ca. 900 g)</li></ul></div><div class="method"><ol><li>Hakk skrelt løk, skrelt hvitløk uten kime og vasket, tørket persille porsjonsvis i SuperSonic Chopper Compact.</li><li>Bland løk, hvitløk, persille, couscous, pølsefarse, salt, pepper og egg kraftig i That's a Bowl 3 l til fyllet er jevnt.</li><li>Vask kålen og fjern roten. Del kålen slik at grønne og hvite deler skilles. Kle bunnen og sidene av 1,75-litersformen med to lag grønne blader som går opp langs sidene.</li><li>Legg i fyllet, dekk med grønne blader, brett sidebladene inn mot midten og press godt. Legg resten av kålen til side til oppskriften med kinakål.</li><li>Stable Combo Micro 3 og tilbered i 25 minutter ved 600 watt. La hvile i 5 minutter, hell av væsken og server i porsjoner med hvitløksgulrøttene.</li></ol></div></div><div class="individual"><strong>Tilberedt alene</strong><span>Tilbered med lokk i ca. 10 minutter ved 600 watt. La hvile i 3 minutter, hell om nødvendig av væsken med dørslaget, og nyt.</span></div></section>
<section class="recipe-row recipe-pear"><h2>PÆREKAKE</h2><div class="recipe-columns"><div class="ingredients"><h3>Ingredienser til 4 personer</h3><ul><li>1 ss flytende karamell</li><li>500 g modne pærer</li><li>80 g svært mykt smør</li><li>80 g sukker</li><li>2 egg</li><li>80 g mel (ca. 135 ml)</li><li>2 usprøytede appelsiner til pressing</li><li>2 ss brunt sukker</li><li>Eventuelt pekannøtter</li></ul></div><div class="method"><ol><li>Pensle 750 ml-formen med karamell med Easylogics pensel.</li><li>Skrell pærene, del dem i to og fjern kjernehusene. Legg én halvdel i midten og resten i båter rundt.</li><li>Pisk smør og sukker kremet. Tilsett eggene ett om gangen, deretter melet, og bland godt.</li><li>Fordel røren over pærene. Unngå å legge for mye røre i midten.</li><li>Stable Combo Micro 3 og tilbered i 25 minutter ved 600 watt. La kaken stå til den er avkjølt.</li><li>Riv skallet og press appelsinene med Citrus Set. Tilsett brunt sukker og bland.</li><li>Hvelv kaken på et serveringsfat. Avkjøl litt før den søtede appelsinsaften helles over.</li><li>Server med flytende karamell og eventuelt pekannøtter.</li></ol><p><strong>Variant:</strong> Bruk pærer eller annen frukt i sukkerlake.</p></div></div><div class="individual"><strong>Tilberedt alene</strong><span>Tilbered uten lokk i ca. 10 minutter ved 600 watt. La hvile, og nyt som angitt.</span></div></section>
</div>'''


def convert_pages() -> list[dict[str, int | str]]:
    OUT.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)
    for stale in PAGES.glob("page-*.*"):
        stale.unlink()
    subprocess.run(
        [str(POPPLER), "-jpeg", "-r", "144", str(SOURCE_PDF), str(PAGES / "page")],
        check=True,
    )
    pages = []
    for source in sorted(PAGES.glob("page-*.jpg")):
        number = int(source.stem.split("-")[-1])
        webp = PAGES / f"page-{number:02d}.webp"
        image = Image.open(source).convert("RGB")
        image.save(webp, "WEBP", quality=88, method=6)
        source.unlink()
        pages.append({"page": number, "file": webp.name, "width": image.width, "height": image.height})
    if pages:
        return pages
    for webp in sorted(PAGES.glob("page-*.webp")):
        number = int(webp.stem.split("-")[-1])
        image = Image.open(webp)
        pages.append({"page": number, "file": webp.name, "width": image.width, "height": image.height})
    return pages


def reuse_shared_norwegian_pages() -> None:
    for page_number in (2, 3):
        source = ROOT / "september-katalog" / "pages" / f"page-{page_number:02d}.webp"
        if source.exists():
            shutil.copy2(source, PAGES / source.name)


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value


def extract_products() -> list[dict[str, object]]:
    products: list[dict[str, object]] = []
    seen: set[tuple[int, str]] = set()
    code_re = re.compile(r"^(?:\d{7,8}|\d{2}[A-Z]{2}\d{3,})$")
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            width = float(page.width)
            height = float(page.height)
            words = page.extract_words(
                keep_blank_chars=False,
                use_text_flow=False,
                x_tolerance=2,
                y_tolerance=4,
            )
            for word in words:
                code = re.sub(r"[^A-Z0-9]", "", word.get("text", "").upper())
                if len(code) == 16 and code.isdigit() and all(code[i] == code[i + 1] for i in range(0, 16, 2)):
                    code = code[::2]
                if not code_re.match(code):
                    continue
                if code in {"01102026", "31102026"}:
                    continue
                key = (page_number, code)
                if key in seen:
                    continue
                seen.add(key)
                x0 = float(word["x0"])
                x1 = float(word["x1"])
                top = float(word["top"])
                bottom = float(word["bottom"])
                center_x = (x0 + x1) / 2

                # The visible article number is usually between product name,
                # dimensions and price. Make the clickable area cover that
                # whole product text block, not just the tiny number.
                block_words = [
                    item
                    for item in words
                    if top - 58 <= float(item["top"]) <= bottom + 38
                    and abs(((float(item["x0"]) + float(item["x1"])) / 2) - center_x) <= 170
                ]
                if block_words:
                    bx0 = min(float(item["x0"]) for item in block_words)
                    bx1 = max(float(item["x1"]) for item in block_words)
                    btop = min(float(item["top"]) for item in block_words)
                    bbottom = max(float(item["bottom"]) for item in block_words)
                else:
                    bx0, bx1, btop, bbottom = x0, x1, top, bottom

                left = max(3.5, bx0 / width * 100 - 1.5)
                top_pct = max(2.0, btop / height * 100 - 1.2)
                block_width = min(48.0, (bx1 - bx0) / width * 100 + 3.0)
                block_height = min(12.5, (bbottom - btop) / height * 100 + 2.4)
                if block_width < 24.0:
                    if center_x / width < 0.5:
                        left = max(3.5, center_x / width * 100 - 14.0)
                    else:
                        left = min(72.0, center_x / width * 100 - 14.0)
                    block_width = 28.0
                block_height = max(5.8, block_height)

                products.append(
                    {
                        "page": page_number,
                        "code": code,
                        "name": code,
                        "left": left,
                        "top": top_pct,
                        "width": block_width,
                        "height": block_height,
                    }
                )
    return products


def product_row(product: dict[str, object]) -> str:
    code = html.escape(str(product["code"]))
    page = int(product["page"])
    return f'''
        <a class="product-row" href="https://tupperware-eu.com/no/search?q={code}" target="tupperware_shop"
           data-search="{code.lower()} {code.lower()}" data-page="{page}" data-code="{code}">
          <span>{code}</span>
          <strong>Side {page}</strong>
          <small class="stock-status" data-stock-code="{code}">Sjekker lagerstatus ...</small>
        </a>'''


def hotspot(product: dict[str, object]) -> str:
    code = html.escape(str(product["code"]))
    return (
        f'<a class="hotspot" href="https://tupperware-eu.com/no/search?q={code}" '
        f'target="tupperware_shop" style="left:{product["left"]:.4f}%;'
        f'top:{product["top"]:.4f}%;width:{product["width"]:.4f}%;'
        f'height:{product["height"]:.4f}%;" aria-label="{code}" title="{code}" data-code="{code}"></a>'
    )


def overlay_html(page_number: int) -> str:
    return OCTOBER_OVERLAYS.get(page_number, "")


def build_html(pages: list[dict[str, int | str]], products: list[dict[str, object]]) -> None:
    by_page: dict[int, list[dict[str, object]]] = {}
    for product in products:
        by_page.setdefault(int(product["page"]), []).append(product)

    first = pages[0]
    ratio = float(first["width"]) / float(first["height"])
    page_sections = []
    for page in pages:
        page_no = int(page["page"])
        page_products = by_page.get(page_no, [])
        page_sections.append(
            f'''
            <section class="page" id="page-{page_no}" data-page="{page_no}">
              <div class="page-head">
                <span>Side {page_no}</span>
                <span>{len(page_products)} lenker</span>
              </div>
              <div class="sheet" style="--page-ratio:{ratio:.8f};">
                <img loading="lazy" decoding="async" src="/oktober-katalog/pages/{page["file"]}" width="{page["width"]}" height="{page["height"]}" alt="Oktoberkatalog side {page_no}">
                {''.join(hotspot(product) for product in page_products)}
                {overlay_html(page_no)}
              </div>
            </section>'''
        )

    page_sections.append(
        f'''<section class="page" id="page-15" data-page="15">
          <div class="page-head"><span>Side 15</span><span>Konsulentinformasjon</span></div>
          <div class="sheet contact-sheet" style="--page-ratio:{ratio:.8f};">
            <div class="contact-accent">Tupperware</div>
            <div class="contact-intro"><span>OKTOBER 2026</span><h2>Bestill fra din Tupperware-konsulent</h2><p>Klikk på produktene i den digitale katalogen, legg flere varer i handlekurven og send hele bestillingen samlet. Pris og lagerstatus i Tupperwares nettbutikk gjelder alltid.</p></div>
            <div class="contact-card"><h3>Din konsulent</h3><strong id="catalogConsultantName">Navn lastes inn ...</strong><span id="catalogConsultantEmail"></span><span id="catalogConsultantPhone"></span></div>
            <div class="contact-qr-grid"><a id="catalogStoreLink" target="tupperware_shop"><canvas id="catalogStoreQr"></canvas><strong>Handle hos konsulenten</strong><span id="catalogStoreUrl"></span></a><a id="catalogDigitalLink"><canvas id="catalogDigitalQr"></canvas><strong>Åpne oktoberkatalogen</strong><span id="catalogDigitalUrl"></span></a></div>
            <div class="contact-note">Tupperware sender bestillingen hjem til kunden. Normal leveringstid er vanligvis 7-10 dager.</div>
          </div>
        </section>'''
    )

    rows = "\n".join(product_row(product) for product in products)
    body = f'''<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tupperware oktoberkatalog 2026</title>
  <script src="https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #f2f5f4; color: #172124; }}
    header {{ position: sticky; top: 0; z-index: 10; background: #fff; border-bottom: 1px solid #dbe2e0; }}
    .consultant-line {{ min-height: 32px; display:flex; align-items:center; justify-content:center; gap:8px; padding:6px 18px; background:#0b6b66; color:#fff; font-size:13px; }}
    .consultant-line small {{ color: rgba(255,255,255,.75); }}
    .consultant-line.invalid {{ background:#9b332d; }}
    .bar {{ display:grid; grid-template-columns:minmax(210px,1fr) auto auto; gap:10px; align-items:center; max-width:1380px; margin:0 auto; padding:12px 18px; }}
    .brand {{ display:flex; align-items:center; gap:10px; min-width:0; }}
    .brand-mark {{ width:36px; height:36px; display:grid; place-items:center; flex:0 0 auto; background:#d45a3c; color:#fff; font-size:21px; font-weight:800; }}
    h1 {{ margin:0; font-size:18px; letter-spacing:0; }}
    input {{ width:min(420px,100%); border:1px solid #cbd6d3; border-radius:8px; min-height:40px; padding:8px 10px; font:inherit; }}
    button {{ border:1px solid #0b6b66; background:#0b6b66; color:#fff; border-radius:8px; min-height:40px; padding:8px 12px; font:inherit; font-weight:700; cursor:pointer; }}
    main {{ display:grid; grid-template-columns:300px minmax(0,1fr); gap:18px; max-width:1380px; margin:0 auto; padding:18px; }}
    aside {{ position:sticky; top:76px; align-self:start; max-height:calc(100vh - 92px); overflow:auto; background:#fff; border:1px solid #dbe2e0; border-radius:8px; }}
    .product-row {{ display:grid; gap:4px; padding:10px 12px; border-bottom:1px solid #eef2f1; color:#172124; text-decoration:none; }}
    .product-row:hover {{ background:#edf8f6; }}
    .product-row strong {{ color:#0b6b66; font-size:13px; }}
    .stock-status {{ color:#506166; font-size:12px; font-weight:700; }}
    .stock-status.available {{ color:#08795f; }}
    .stock-status.unavailable {{ color:#9b332d; }}
    .stock-status.unknown {{ color:#6b5b2a; }}
    .pages {{ display:grid; gap:18px; }}
    .page {{ background:#fff; border:1px solid #dbe2e0; border-radius:8px; overflow:hidden; box-shadow:0 8px 24px rgba(18,48,47,.08); }}
    .page-head {{ display:flex; justify-content:space-between; border-bottom:1px solid #e7ecea; padding:8px 12px; font-size:13px; font-weight:700; color:#506166; }}
    .sheet {{ position:relative; width:100%; aspect-ratio:var(--page-ratio); background:#fff; }}
    .sheet img {{ display:block; width:100%; height:100%; object-fit:contain; }}
    .hotspot {{ position:absolute; display:block; border-radius:4px; outline-offset:2px; }}
    .hotspot:focus {{ outline:3px solid #d45a3c; background:rgba(212,90,60,.14); }}
    body.show-links .hotspot {{ background:rgba(11,107,102,.18); box-shadow:inset 0 0 0 2px rgba(11,107,102,.75); }}
    .translation {{ position:absolute; z-index:2; font-weight:800; line-height:1.15; color:#172124; text-wrap:balance; pointer-events:none; }}
    .october-cover {{ left:5%; top:17%; width:68%; min-height:10%; display:flex; align-items:center; padding:1.2% 1.6%; background:#efbda5; color:#7f210b; font-size:clamp(18px,3.2vw,46px); }}
    .october-heading {{ left:4%; top:2.3%; width:92%; min-height:7%; display:flex; align-items:center; justify-content:center; padding:.7% 1.4%; background:#fff; color:#84250d; font-size:clamp(16px,2.8vw,40px); text-align:center; }}
    .october-heading-left {{ justify-content:flex-start; }}
    #page-8 .october-heading {{ left:3%; width:94%; background:#d7b28d; }}
    #page-12 .october-heading {{ left:0; top:0; width:48%; min-height:9%; padding-left:5%; background:#ef7f22; color:#182f59; }}
    #page-13 .october-heading {{ left:28%; width:69%; background:#fff; }}
    #page-14 .october-heading {{ left:0; top:0; width:76%; min-height:9%; padding-left:5%; background:#d7a77f; }}
    .october-callout {{ display:grid; gap:.25em; padding:.7% 1%; background:rgba(247,200,178,.96); color:#46170c; font-size:clamp(8px,.95vw,14px); font-weight:500; }}
    .october-callout strong {{ font-size:1.08em; }}
    .callout-colander {{ left:3%; top:15.8%; width:31%; min-height:10%; }}
    .callout-cone {{ left:3%; top:68%; width:32%; min-height:11%; }}
    .callout-lids {{ left:67%; top:68%; width:30%; min-height:11%; }}
    .callout-combo {{ left:5%; top:81%; width:90%; min-height:17%; display:flex; flex-direction:column; justify-content:center; text-align:center; font-size:clamp(9px,1.15vw,16px); }}
    .october-blog {{ left:66%; top:3%; width:31%; min-height:10%; display:flex; align-items:center; padding:1%; background:#f7c8b2; color:#46170c; font-size:clamp(8px,.9vw,13px); text-align:center; }}
    .recipe-sheet-original {{ left:2%; top:2.3%; width:96%; height:96%; display:grid; grid-template-rows:24.8% 34.3% 38.7%; gap:1.1%; padding:0; background:#d7bba4; color:#29221e; font-size:clamp(11.5px,1.25vw,20px); font-weight:400; line-height:1.08; overflow:hidden; }}
    .recipe-row {{ position:relative; min-height:0; padding:1.35% 2.25% 1.15%; background:#f8f5f1; overflow:hidden; }}
    .recipe-row h2,.recipe-row h3,.recipe-row p {{ margin:0; }}
    .recipe-row h2 {{ margin-bottom:.3em; color:#6e311f; font-size:1.72em; line-height:1; font-weight:800; }}
    .recipe-row h3 {{ margin-bottom:.3em; font-size:1em; font-weight:800; }}
    .recipe-columns {{ display:grid; grid-template-columns:32.5% 64.5%; gap:3%; height:calc(100% - 3.9em); }}
    .ingredients,.method {{ min-width:0; }}
    .recipe-row ul,.recipe-row ol {{ margin:0; padding-left:1.45em; }}
    .recipe-row li {{ margin:0 0 .18em; }}
    .method p {{ margin-top:.3em; }}
    .individual {{ position:absolute; left:2.25%; right:2.25%; bottom:1%; display:grid; grid-template-columns:17% 1fr; gap:2%; align-items:center; padding-top:.38em; border-top:1px solid #b68b70; font-size:.94em; }}
    .individual strong {{ color:#6e311f; text-transform:uppercase; }}
    .cover-badge {{ padding:1.1% 1.6%; background:rgba(255,255,255,.92); color:#0b6b66; font-size:clamp(10px,1.4vw,19px); text-transform:uppercase; letter-spacing:.04em; }}
    .cover-title {{ color:#fff; font-size:clamp(22px,4.3vw,54px); text-shadow:0 2px 8px rgba(0,0,0,.28); }}
    .cover-subtitle {{ color:#fff; font-size:clamp(15px,2.2vw,30px); text-shadow:0 2px 8px rgba(0,0,0,.28); }}
    .note-panel, .story-panel {{ padding:1.2% 1.5%; background:rgba(255,255,255,.92); border-left:5px solid #0b6b66; font-size:clamp(10px,1.45vw,18px); font-weight:500; box-shadow:0 8px 20px rgba(0,0,0,.12); }}
    .note-panel.compact {{ font-size:clamp(9px,1.08vw,15px); line-height:1.22; }}
    .note-panel.dark {{ background:rgba(23,33,36,.9); color:#fff; }}
    .note-panel strong, .story-panel strong {{ color:#0b6b66; font-weight:900; }}
    .print-tools {{ display:grid; grid-template-columns:minmax(0,180px) max-content; gap:8px; min-width:0; }}
    .print-tools input {{ width:100%; min-width:0; }}
    .print-tools button {{ white-space:nowrap; }}
    .bar {{ grid-template-columns:minmax(210px,1fr) minmax(180px,360px) auto auto; }}
    .contact-sheet {{ overflow:hidden; background:linear-gradient(150deg,#f4b89e 0 40%,#f8e9df 40% 100%); padding:7%; color:#20312d; }}
    .contact-accent {{ position:absolute; right:-8%; top:7%; color:rgba(132,37,13,.1); font-weight:900; font-size:clamp(50px,10vw,140px); transform:rotate(-8deg); }}
    .contact-intro {{ position:relative; z-index:1; max-width:80%; }}
    .contact-intro > span {{ color:#84250d; font-weight:900; letter-spacing:0; }}
    .contact-intro h2 {{ margin:.3em 0; font-size:clamp(24px,4vw,54px); line-height:1; }}
    .contact-intro p {{ max-width:86%; font-size:clamp(11px,1.35vw,18px); line-height:1.4; }}
    .contact-card {{ position:relative; z-index:1; display:flex; flex-direction:column; gap:.35em; width:62%; margin-top:4%; padding:3%; background:#fff; border-left:8px solid #0b6b66; box-shadow:0 10px 24px rgba(70,36,24,.14); font-size:clamp(11px,1.5vw,20px); }}
    .contact-card h3 {{ margin:0; color:#84250d; text-transform:uppercase; font-size:.8em; }}
    .contact-card span {{ overflow-wrap:anywhere; }}
    .contact-qr-grid {{ position:relative; z-index:1; display:grid; grid-template-columns:1fr 1fr; gap:4%; margin-top:5%; }}
    .contact-qr-grid a {{ display:grid; grid-template-columns:36% 1fr; grid-template-rows:auto 1fr; align-items:center; gap:.35em 5%; padding:3%; background:#fff; color:#20312d; text-decoration:none; box-shadow:0 10px 24px rgba(70,36,24,.12); }}
    .contact-qr-grid canvas {{ grid-row:1 / 3; width:100% !important; height:auto !important; aspect-ratio:1; }}
    .contact-qr-grid span {{ font-size:clamp(7px,.75vw,11px); overflow-wrap:anywhere; }}
    .contact-note {{ position:relative; z-index:1; margin-top:5%; padding:2.5%; background:#84250d; color:#fff; text-align:center; font-weight:700; font-size:clamp(10px,1.25vw,17px); }}
    @media (max-width:860px) {{ .bar {{ grid-template-columns:minmax(0,1fr); }} .bar > * {{ width:100%; min-width:0; }} .print-tools {{ grid-template-columns:minmax(0,1fr) max-content; }} main {{ grid-template-columns:1fr; }} aside {{ position:static; max-height:210px; }} .consultant-line {{ flex-wrap:wrap; text-align:center; }} }}
    @media (max-width:430px) {{ .print-tools {{ grid-template-columns:1fr; }} .print-tools button {{ width:100%; }} }}
    @media print {{
      @page {{ size:A4 portrait; margin:0; }}
      body {{ background:#fff; }}
      header, aside, .page-head {{ display:none !important; }}
      main, .pages {{ display:block; width:100%; max-width:none; margin:0; padding:0; }}
      .page {{ display:block; width:210mm; height:297mm; margin:0; border:0; border-radius:0; box-shadow:none; overflow:hidden; break-after:page; page-break-after:always; }}
      .page.print-excluded {{ display:none !important; }}
      .sheet {{ width:210mm; height:297mm; }}
      .hotspot {{ display:none !important; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="consultant-line" id="consultantLine">
      <span>Du handler med <strong id="consultantName">Kontrollerer konsulent ...</strong></span>
      <small id="consultantCode"></small>
    </div>
    <div class="bar">
      <div class="brand"><span class="brand-mark">T</span><h1>Tupperware oktoberkatalog 2026</h1></div>
      <input id="search" type="search" placeholder="Søk artikkelnummer eller kode">
      <button id="toggle" type="button">Vis lenkeflater</button>
      <div class="print-tools"><input id="printPages" type="text" inputmode="numeric" placeholder="Sider, f.eks. 1-5,15" aria-label="Sider som skal skrives ut eller lagres som PDF"><button id="printCatalog" type="button" title="Skriv ut eller velg Lagre som PDF i utskriftsvinduet">PDF / skriv ut</button></div>
    </div>
  </header>
  <main>
    <aside>{rows}</aside>
    <div class="pages">{''.join(page_sections)}</div>
  </main>
  <script>
    const search = document.querySelector("#search");
    const rows = [...document.querySelectorAll(".product-row")];
    const shopLinks = [...document.querySelectorAll('a[target="tupperware_shop"]')];
    const toggle = document.querySelector("#toggle");
    const consultantLine = document.querySelector("#consultantLine");
    const consultantName = document.querySelector("#consultantName");
    const consultantCode = document.querySelector("#consultantCode");
    const printPages = document.querySelector("#printPages");
    const printCatalog = document.querySelector("#printCatalog");
    let shopWindow = null;
    let consultantReady = false;
    function cleanReference(value) {{ return String(value || "").trim().replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 80); }}
    function openShopProduct(url) {{
      shopWindow = window.open(url, "tupperware-official-store");
      if (!shopWindow) {{ window.location.assign(url); return; }}
      try {{ shopWindow.focus(); }} catch {{}}
    }}
    function norwegianShopUrl(value, reference) {{
      const target = new URL(value);
      if (target.hostname === "tupperware-eu.com" || target.hostname.endsWith(".tupperware-eu.com")) {{
        if (target.pathname === "" || target.pathname === "/") target.pathname = "/no/";
        else if (target.pathname !== "/no" && !target.pathname.startsWith("/no/")) target.pathname = `/no${{target.pathname.startsWith("/") ? target.pathname : `/${{target.pathname}}`}}`;
        target.searchParams.set("ref", reference);
      }}
      return target.toString();
    }}
    async function prepareConsultant() {{
      const params = new URLSearchParams(window.location.search);
      const reference = cleanReference(params.get("ref"));
      if (!reference) {{ consultantLine.classList.add("invalid"); consultantName.textContent = "ingen konsulent valgt"; return; }}
      const fallbackStoreUrl = `https://tupperware-eu.com/no/?ref=${{encodeURIComponent(reference)}}`;
      const fallbackDigitalUrl = `${{window.location.origin}}/oktober-katalog?ref=${{encodeURIComponent(reference)}}`;
      document.querySelector("#catalogConsultantName").textContent = reference;
      document.querySelector("#catalogStoreLink").href = fallbackStoreUrl;
      document.querySelector("#catalogDigitalLink").href = fallbackDigitalUrl;
      document.querySelector("#catalogStoreUrl").textContent = fallbackStoreUrl;
      document.querySelector("#catalogDigitalUrl").textContent = fallbackDigitalUrl;
      if (window.QRCode) {{
        QRCode.toCanvas(document.querySelector("#catalogStoreQr"), fallbackStoreUrl, {{ width:260, margin:1 }});
        QRCode.toCanvas(document.querySelector("#catalogDigitalQr"), fallbackDigitalUrl, {{ width:260, margin:1 }});
      }}
      try {{
        const response = await fetch(`/api/consultant?ref=${{encodeURIComponent(reference)}}&track=1`);
        const result = await response.json();
        if (!response.ok || !result.found) throw new Error("Ugyldig konsulent");
        consultantName.textContent = result.name || result.consultant?.display_name || reference;
        consultantCode.textContent = reference;
        shopLinks.forEach((link) => {{ link.href = norwegianShopUrl(link.href, reference); }});
        const profile = result.consultant || result;
        const displayName = result.name || profile.display_name || reference;
        const storeUrl = `https://tupperware-eu.com/no/?ref=${{encodeURIComponent(reference)}}`;
        const digitalUrl = `${{window.location.origin}}/oktober-katalog?ref=${{encodeURIComponent(reference)}}`;
        document.querySelector("#catalogConsultantName").textContent = displayName;
        document.querySelector("#catalogConsultantEmail").textContent = profile.email || "";
        document.querySelector("#catalogConsultantPhone").textContent = profile.phone || "";
        document.querySelector("#catalogStoreLink").href = storeUrl;
        document.querySelector("#catalogDigitalLink").href = digitalUrl;
        document.querySelector("#catalogStoreUrl").textContent = storeUrl;
        document.querySelector("#catalogDigitalUrl").textContent = digitalUrl;
        if (window.QRCode) {{
          QRCode.toCanvas(document.querySelector("#catalogStoreQr"), storeUrl, {{ width:260, margin:1 }});
          QRCode.toCanvas(document.querySelector("#catalogDigitalQr"), digitalUrl, {{ width:260, margin:1 }});
        }}
        consultantReady = true;
      }} catch {{
        consultantLine.classList.add("invalid"); consultantName.textContent = "konsulenten kunne ikke bekreftes"; consultantCode.textContent = reference;
      }}
    }}
    function statusLabel(product) {{
      if (!product) return ["unknown", "Ikke funnet i produktbasen"];
      if (product.catalogStatus === "not-in-current-assortment") return ["unknown", "Ikke i dagens sortiment"];
      if (product.available) return ["available", "På lager"];
      return ["unavailable", "Midlertidig utsolgt"];
    }}
    async function loadStockStatuses() {{
      const codes = [...new Set(rows.map(row => row.dataset.code).filter(Boolean))];
      await Promise.all(codes.map(async (code) => {{
        let product = null;
        try {{
          const response = await fetch(`/api/products?q=${{encodeURIComponent(code)}}&limit=8`);
          const payload = await response.json();
          if (response.ok && Array.isArray(payload.products)) {{
            product = payload.products.find(item => String(item.articleNumber || "").toUpperCase() === code)
              || payload.products[0]
              || null;
          }}
        }} catch {{}}
        const [statusClass, text] = statusLabel(product);
        document.querySelectorAll(`[data-stock-code="${{code}}"]`).forEach((item) => {{
          item.textContent = text;
          item.classList.remove("available", "unavailable", "unknown");
          item.classList.add(statusClass);
        }});
        document.querySelectorAll(`.hotspot[data-code="${{code}}"]`).forEach((item) => {{
          item.title = `${{code}} - ${{text}}`;
          item.setAttribute("aria-label", `${{code}} - ${{text}}`);
        }});
      }}));
    }}
    shopLinks.forEach((link) => {{
      link.addEventListener("click", (event) => {{
        event.preventDefault();
        if (!consultantReady) {{ window.alert("Produktet kan ikke åpnes før en gyldig konsulent er valgt."); return; }}
        openShopProduct(link.href);
      }});
    }});
    search.addEventListener("input", () => {{
      const query = search.value.trim().toLowerCase();
      rows.forEach((row) => {{ row.style.display = !query || row.dataset.search.includes(query) ? "" : "none"; }});
    }});
    rows.forEach((row) => {{
      row.addEventListener("mouseenter", () => {{
        const page = document.querySelector(`[data-page="${{row.dataset.page}}"]`);
        if (page) page.scrollIntoView({{ block: "center", behavior: "smooth" }});
      }});
    }});
    toggle.addEventListener("click", () => {{
      document.body.classList.toggle("show-links");
      toggle.textContent = document.body.classList.contains("show-links") ? "Skjul lenkeflater" : "Vis lenkeflater";
    }});
    function selectedPrintPages(value) {{
      if (!value.trim()) return new Set(Array.from({{length:15}}, (_, index) => index + 1));
      const selected = new Set();
      value.split(",").forEach((part) => {{
        const match = part.trim().match(/^(\\d+)(?:\\s*-\\s*(\\d+))?$/);
        if (!match) return;
        let start = Math.max(1, Math.min(15, Number(match[1])));
        let end = Math.max(1, Math.min(15, Number(match[2] || match[1])));
        if (start > end) [start, end] = [end, start];
        for (let page = start; page <= end; page += 1) selected.add(page);
      }});
      return selected;
    }}
    printCatalog.addEventListener("click", () => {{
      const selected = selectedPrintPages(printPages.value);
      if (!selected.size) {{ window.alert("Skriv inn gyldige sider, for eksempel 1-5,15."); return; }}
      document.querySelectorAll(".page").forEach((page) => page.classList.toggle("print-excluded", !selected.has(Number(page.dataset.page))));
      window.print();
      window.setTimeout(() => document.querySelectorAll(".page").forEach((page) => page.classList.remove("print-excluded")), 500);
    }});
    prepareConsultant();
    loadStockStatuses();
  </script>
</body>
</html>
'''
    (OUT / "index.html").write_text(body, encoding="utf-8")
    (OUT / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    pages = convert_pages()
    reuse_shared_norwegian_pages()
    products = extract_products()
    build_html(pages, products)
    print(f"pages={len(pages)}")
    print(f"products={len(products)}")
    print(OUT / "index.html")


if __name__ == "__main__":
    main()
