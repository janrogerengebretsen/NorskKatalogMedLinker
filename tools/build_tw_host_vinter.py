from __future__ import annotations

import html
import json
import math
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
    4: '''<div class="translation-panel full-text-translation join-translation"><h2>Bli med</h2><h3>Bli kjent med produktene</h3><p>Start med nyttige Tupperware-produkter og få tilgang til arrangementer, gaver og gode tilbud.</p><h3>Jobb der du vil</h3><p>Arbeid fysisk eller digitalt, og legg opp dagene slik det passer deg.</p><h3>Møt nye mennesker</h3><p>Bli del av et engasjert fellesskap og skap nye kontakter.</p><h3>Kombiner jobb og fritid</h3><p>Du bestemmer selv arbeidstid og ambisjonsnivå.</p><h3>Provisjon fra første salg</h3><p>Du tjener provisjon helt fra starten.</p><h3>Jobb digitalt</h3><p>Bygg nettverk, skap gode kunderelasjoner og selg på nettet.</p></div><div class="translation-panel contents-translation"><strong>Innhold</strong><div><a href="#page-3">3 Tupperware</a><a href="#page-4">4 Bli med</a><a href="#page-5">5 Tilbakevendende og nye produkter</a><a href="#page-8">8 Frysing</a><a href="#page-8">8 Flerbruk</a><a href="#page-9">9 Kjøleskap</a><a href="#page-12">12 Oppbevaring</a><a href="#page-14">14 Baking</a><a href="#page-16">16 Oppskrifter</a><a href="#page-18">18 Ekstra praktisk</a><a href="#page-20">20 Kjøkkenredskaper</a><a href="#page-23">23 Barn</a><a href="#page-24">24 Mikrobølgeovn</a><a href="#page-26">26 Matlaging</a><a href="#page-28">28 Oppskrifter</a><a href="#page-29">29 Servering</a><a href="#page-30">30 Drikke</a><a href="#page-31">31 Big T</a><a href="#page-32">32 På farten</a><a href="#page-33">33 Pleie og rengjøring</a><a href="#page-34">34 Garanti</a></div></div>''',
    5: '''<div class="translation-panel page-five-translation"><h2>TILBAKEVENDENDE<br><strong>NYE PRODUKTER</strong></h2><p>Når behovene dine utvikler seg, gjør sortimentet vårt det samme.</p><p>Oppdag produkter som gjør comeback, og nye produkter som er utviklet for å gjøre hverdagen enklere.</p><p>Inspirerende løsninger og favoritter å dele - kanskje finner du din neste favoritt på de følgende sidene.</p></div>''',
    6: '''<div class="fixed-heading heading-page6-prep">FORBEREDELSE</div><div class="fixed-heading heading-page6-cook">MATLAGING</div><div class="fixed-footer">6 | Tilbakevendende og nye produkter</div>''',
    7: '''<div class="fixed-heading heading-page7">DRIKKE OG RENGJØRING</div><div class="fixed-footer">7 | Tilbakevendende og nye produkter</div>''',
    9: '''<div class="product-copy product-copy-page9"><strong>Mindre svinn, mer friskhet!</strong><p>Ventsmart-boksene regulerer fuktighet og luftsirkulasjon, slik at frukt og grønnsaker holder seg friske lenger.</p><p>En enklere hverdag med mindre matsvinn.</p></div>''',
    10: '''<div class="fixed-heading heading-page10">OPTIMAL FRISKHET</div><div class="translation-panel page10-info"><h3>Oppbevares kjølig!</h3><p>Hold maten frisk lenger med lufttette bokser, brett og skåler. De passer godt til ingredienser, rester og ferdiglagde måltider i kjøleskapet, bevarer smak, gir bedre orden og bidrar til mindre matsvinn.</p></div><div class="fixed-footer">10 | Kjøleskap</div>''',
    11: '''<div class="product-copy page11-jar-one">Oppbevar og ta med hjemmelaget mat</div><div class="product-copy page11-jar-two">Favorittsalaten din med dressing i lokket</div><div class="product-copy page11-info"><strong>Bokser som holder maten frisk når du er på farten.</strong><p>Ta med favorittrettene dine hvor du vil.</p><p>Fargerike salater, balanserte måltider og gode desserter holder seg friske og klare til å nytes gjennom dagen.</p></div>''',
    12: '''<div class="product-copy page12-info"><strong>Ultra Clear® kombinerer gjennomsiktighet og eleganse!</strong><p>Se ingrediensene med et blikk og hold kjøkkenet ryddig.</p><p>Det lufttette lokket er enkelt å åpne, og det lette designet forener funksjon, friskhet og eleganse i hverdagen.</p></div>''',
    13: '''<div class="product-copy page13-info"><strong>Organiser, stable og gjør det enkelt!</strong><p>Fleksible løsninger som holder ingrediensene lett tilgjengelige.</p></div><div class="product-copy page13-paper">Tørkepapir lett tilgjengelig.</div><div class="product-copy page13-chop">Praktisk for å holde arbeidsflaten ren.</div><div class="fixed-footer">13 | Oppbevaring</div>''',
    14: '''<div class="fixed-heading heading-page14">BAKEGLEDE</div><div class="product-copy page14-info"><strong>Slipp matgleden løs!</strong><p>Smarte løsninger som hjelper deg gjennom alle trinn når du lager kjeks, kaker og desserter.</p></div><div class="fixed-footer">14 | Bakeglede</div>''',
    15: '''<div class="product-copy page15-icing"><strong>Rask glasur</strong><p>Bland ca. 30 g melis med 1 ts sitronsaft. Juster konsistensen med litt mer melis eller sitronsaft.</p><p>Fyll dekorpennen, pynt og sett bakverket kjølig så glasuren stivner.</p></div><div class="product-copy page15-treat"><strong>Gjør bakverket ekstra fint!</strong><p>Dekorpennen passer til presis pynting med glasur, mønstre og personlige hilsener på julekaker, kaker og andre søtsaker.</p><p>Den er enkel å bruke og gjør hvert bakverk både personlig og innbydende.</p></div><div class="fixed-footer">15 | Bakeglede</div>''',
    16: '''<div class="fixed-heading heading-page16">ET MAGISK MÅLTID</div><div class="translation-panel recipe-intro"><strong>Én meny, tusen muligheter til å glede.</strong><span>Lett å tilberede og elegant å servere - et måltid laget med kjærlighet av barna, en hyggelig stund med familien eller en middag med venner.</span></div><div class="translation-panel recipe-panel recipe16-top"><h3>Butternutgresskarsuppe med pisket parmesankrem</h3><p><strong>Ingredienser til 4 personer:</strong> 2 sjalottløk (ca. 50 g), 15 ml olje, 600 g butternutgresskar, 300 ml varmt vann, 1 grønnsaksbuljongterning, 400 ml svært kald kremfløte, 30 g parmesan, salt og pepper.</p><ul><li>Hakk skrelte sjalottløk i <strong>SuperSonic Chopper compact</strong>. Varm dem med oljen i ca. 2 minutter ved 600 watt i <strong>MicroPlus pitcher 1 l</strong>.</li><li>Tilsett skrelt gresskar i terninger, kuttet med <strong>A-series chef knife</strong>, og den smuldrede buljongterningen.</li></ul></div><div class="translation-panel recipe-panel recipe16-lower"><ul><li>Tilsett vann og kok i ca. 20 minutter ved 600 watt. Rør halvveis.</li><li>Kontroller at gresskaret er mørt, og mos det med <strong>Potato masher</strong>.</li><li>Tilsett halvparten av fløten, smak til og varm i 2 minutter ved 600 watt.</li><li>Pisk resten av den kalde fløten stiv. Bland forsiktig inn revet parmesan fra <strong>Grate n Store</strong>, og smak til.</li><li>Server suppen med parmesankrem og parmesanspon. Kremen og parmesanen kan erstattes med hakkede hasselnøtter.</li></ul></div><div class="fixed-footer">16 | Oppskrifter</div>''',
    17: '''<div class="translation-panel recipe-panel recipe17-top-right"><h3>Pai med confitert and og sopp</h3><p><strong>Ingredienser til 4 personer:</strong> 2 confiterte andelår uten overflødig fett, 2 sjalottløk (ca. 50 g), 500 g sjampinjong, 40 g hasselnøtter, 4 persillekvister, salt, pepper, 2 butterdeigsplater og 1 eggeplomme blandet med 1 ss vann.</p><ul><li>Varm andelårene i <strong>MicroCook round 2,25 l</strong> i 2 minutter ved 360 watt, slik at de blir lettere å beine ut.</li></ul></div><div class="translation-panel recipe-panel recipe17-top-lower"><ul><li>Ta vare på 2 ss andefett i <strong>Refrigerator bowl 380 ml</strong>. Fjern bein, skinn og fett fra kjøttet, riv det og legg det i <strong>Modular bowl 1 l</strong>.</li><li>Hakk sjalottløk og sopp i <strong>SuperSonic Chopper extra</strong>.</li><li>Ha blandingen i <strong>MicroCook round 2,25 l</strong>, rør inn andefettet med <strong>KPT simple spoon</strong> og varm i 8 minutter ved 600 watt. Rør halvveis, la hvile i 3 minutter og hell av væsken.</li><li>Tilsett and, hasselnøtter og persille, og smak til med salt og pepper.</li><li>Legg én butterdeigsplate på et stekebrett. Pensle kantene med eggeplomme og vann med <strong>Easylogics basting brush</strong>. Fordel fyllet med 3-4 cm kant, legg på den andre platen og brett kantene sammen.</li><li>Pensle toppen og stek ca. 35 minutter ved 200 °C.</li></ul></div><div class="translation-panel recipe-panel recipe17-bottom-left"><h3>Bakt eple med nougat og sprø brioche</h3><p><strong>Ingredienser til 4 personer:</strong> 4 store bakeepler, 80 g myk nougat, 4 briodeskiver, 10 Carambars og 150 ml kremfløte.</p><ul><li>Del nougaten i 8 biter. Vask eplene og fjern kjernehuset.</li><li>Legg eplene i <strong>Ultrapro 2 l</strong> og fyll hvert eple med 2 nougatbiter.</li></ul></div><div class="translation-panel recipe-panel recipe17-bottom-lower"><ul><li>Stek uten lokk i 40-45 minutter ved 180 °C.</li><li>Rist briodeskivene i brødrister eller stekeovn før servering.</li><li>Varm Carambars og fløte i <strong>Microplus pitcher 1 l</strong> i 2 minutter ved 600 watt. La hvile i 1 minutt og bland med <strong>KPT beater stirrer</strong>. Varm eventuelt 30 sekunder til.</li><li>Drypp litt stekesjy over briochen, legg på de bakte eplene og server med Carambar-kremen.</li></ul></div><div class="fixed-footer">17 | Oppskrifter</div>''',
    18: '''<div class="translation-panel hummus-translation"><h3>Hjemmelaget hummus</h3><p>Kjør 120 g kokte, skylte kikerter sammen med et halvt hvitløksfedd. Tilsett 1 ss olivenolje, 1 ts sitronsaft og 1 ss soyasaus. Kjør til jevn konsistens og oppbevar kjølig.</p><p><strong>Variant:</strong> Tilsett 80 g kokt rødbete.</p></div><div class="product-copy page18-extra">Ingen oppgave er for stor! Hakker, finfordeler og blander store mengder.</div><div class="product-copy page18-compact">Hakk på sekunder og lag gode retter på kort tid!</div><div class="product-copy page18-mando">En mandolin for alle typer kutting.</div><div class="product-copy page18-speedy">En svært kompakt mandolin for rask og fin skjæring.</div><div class="fixed-footer">18 | Ekstra praktisk</div>''',
    19: '''<div class="product-copy page19-dicer">Tre utskiftbare blader for skiver, terninger eller staver.</div><div class="product-copy page19-spiral">Svært praktisk med kjegler for grønnsaksspagetti og tagliatelle.</div><div class="product-copy page19-pusher">Skyverens blader holder grønnsakene på plass og beskytter fingrene.</div><div class="fixed-footer">19 | Ekstra praktisk</div>''',
    20: '''<div class="product-copy page20-intro"><strong>Alltid lett tilgjengelig.</strong><p>Smarte kjøkkenredskaper som gjør hvert trinn i forberedelsene enklere.</p></div><div class="product-copy page20-star"><strong>Stjernen på kjøkkenet.</strong></div><div class="product-copy page20-spatula">Blander og skraper effektivt helt til siste rest.</div><div class="fixed-footer">20 | Kjøkkenredskaper</div>''',
    28: '''<div class="recipe-cover recipe-28-top-cover"></div><div class="translation-panel recipe-28-top"><h3>Foie gras-terrine</h3><p><strong>Til 8 personer:</strong> ca. 500 g renset foie gras, salt, pepper, krydder og 3 ss portvin, Sauternes eller Armagnac.</p><p>Del foie gras i to, krydre og mariner én time i kjøleskapet. Damp eller varm i Ultrapro cocotte 500 ml som beskrevet, avkjøl og sett kjølig i 24-48 timer.</p></div><div class="translation-panel recipe-28-middle"><h3>Kyllingrillettes</h3><p>Kjør 80 g kokt kyllingbryst og koriander i SuperSonic Chopper compact. Tilsett 3-4 ss majones, salt og pepper. Kjør sammen igjen.</p><p><strong>Variant:</strong> Bruk 75 g kokt laks og en halv sjalottløk.</p></div><div class="recipe-cover recipe-28-bottom-cover"></div><div class="translation-panel recipe-28-bottom"><h3>Pralinkake</h3><p><strong>Til 8 personer:</strong> 300 g pralinesjokolade, 100 g smør, 4 egg, 50 g sukker, vaniljesukker, 200 g kastanjekrem, 60 g hasselnøttpulver og ca. 85 g mel.</p><p>Smelt sjokolade og smør. Pisk egg, sukker og vaniljesukker. Bland inn resten, hell røren i MicroCook round 2,25 l og stek tildekket i mikrobølgeovn. La hvile, vend ut og pynt med sjokolade og nøtter.</p></div><div class="recipe-cover recipe-28-footer">28 | Oppskrifter</div>''',
    34: '''<div class="translation-panel warranty-translation"><h2>Lovbestemte og kommersielle garantier</h2><p>Tupperware-produkter omfattes av garanti mot material- og produksjonsfeil som oppstår ved normal bruk i henhold til bruksanvisningen.</p><p>Garantien dekker ikke skader som skyldes uforsiktig bruk, feil bruk eller annen behandling produktet ikke er beregnet for.</p><p>Dersom produktet omfattes av garanti, gjelder garantibetingelsene for landet ditt. Tupperware-produkter er laget for å brukes igjen og igjen. Produkter du ikke lenger trenger, bør leveres til forsvarlig gjenbruk eller gjenvinning.</p></div>''',
    22: '''<div class="fixed-heading heading-page22">KJØKKENREDSKAPER</div><div class="translation-panel page22-info"><h3>En kniv for ethvert behov.</h3><p>Universalkniv, skrellekniv, tomatkniv, brødkniv eller kokkekniv - det finnes en kniv til enhver oppgave.</p><p>Beskyttelseshylsene tar vare på bladene og gjør det enkelt å oppbevare knivene i en skuff eller hengende.</p></div><div class="product-copy page22-paring">Små, presise kutt.</div><div class="product-copy page22-utility">Perfekt til hverdagens kutteoppgaver.</div><div class="product-copy page22-serrated">Tagget blad for matvarer med glatt skall.</div><div class="product-copy page22-bread">Skjærer brød og bakverk presist.</div><div class="product-copy page22-chef">Hakk, skjær, del store biter og finhakk.</div><div class="product-copy page22-board">Skjær trygt på den sklisikre flaten, og flytt maten enkelt med det fleksible brettet.</div><div class="product-copy page22-sharpener">Sliper glatte og taggete knivblad trygt.</div><div class="fixed-footer">22 | Kjøkkenredskaper</div>''',
    23: '''<div class="fixed-heading heading-page23">BARN</div><div class="product-copy page23-dish">Delt tallerken som tåler mikrobølgeovn, med lufttett lokk som ikke lekker og avtakbart håndtak.</div><div class="product-copy page23-snack">Holder maten frisk med lufttette lokk.</div><div class="product-copy page23-cutlery">Utviklet for å hjelpe små barn med å spise selv. Fra 6 måneder.</div><div class="product-copy page23-milk">Tre rom på 85 ml til tilberedning av tåteflasker på 240 ml.</div><div class="product-copy page23-case">Passer for barn i alle aldre.</div><div class="fixed-footer">23 | Barn</div>''',
    24: '''<div class="fixed-heading heading-page24">MIKROBØLGEOVN</div><div class="product-copy page24-intro"><strong>Få mer ut av mikrobølgeovnen.</strong><p>Bak, grill, gratiner, damp gode retter eller lag hele måltider enkelt.</p><p>Med Tupperware® kan du lage maten raskt og praktisk med gode resultater. Spar tid uten å gå på kompromiss med smaken.</p></div><div class="product-copy page24-popcorn">Hjemmelaget popcorn for store og små.</div><div class="product-copy page24-urban">Damp grønnsaker, fisk, kjøtt, pasta og korn på få minutter.</div><div class="product-copy page24-grill">Bruning, grilling og gratinering i mikrobølgeovn er mulig!</div><div class="fixed-footer">24 | Mikrobølgeovn</div>''',
    25: '''<div class="product-copy page25-pitcher">Varm, smelt og hell av enkelt.</div><div class="product-copy page25-pasta">Én beholder til å koke, helle av, servere, oppbevare og varme pasta.</div><div class="product-copy page25-cook">Allsidig og rask, fra forrett til dessert.</div><div class="product-copy page25-healthy">Den ideelle løsningen for raske måltider.</div><div class="fixed-footer">25 | Mikrobølgeovn</div>''',
    26: '''<div class="product-copy page26-air">Sprøtt uten overflødig olje. Raskt, enkelt og fristende.</div><div class="fixed-heading heading-page26">IDEELL MATLAGING</div><div class="product-copy page26-round">Sunn og jevn tilberedning med gode resultater hver gang.</div><div class="product-copy page26-roast">Ideell størrelse for perfekt steking av fjærkre og store kjøttstykker.</div><div class="fixed-footer">26 | Matlaging</div>''',
    30: '''<div class="fixed-heading heading-page30">HOLD DEG HYDRERT</div><div class="product-copy page30-intro"><strong>Alltid lett tilgjengelig.</strong><p>Gjenbrukbare, praktiske og holdbare flasker som blir med overalt.</p></div><div class="fixed-footer">30 | Drikke</div>''',
    32: '''<div class="fixed-heading heading-page32">PÅ FARTEN</div><div class="product-copy page32-slim">Hjemmelaget lunsj hvor som helst.<br>To bokser i én.<br>22,8 x 14,1 x 4,3 cm h</div><div class="product-copy page32-divided">Praktisk til en balansert lunsj med tre rom.<br>25,4 x 15,7 x 5,3 cm h</div><div class="product-copy page32-cutlery">Gjenbrukbart bestikk som klikkes sammen: kniv, gaffel og skje.<br>16 x 3,9 x 2,7 cm h</div><div class="product-copy page32-lunch">Matboks med to rom, ideell til måltider og mellommåltider.<br>20 x 17,9 x 5,9 cm h</div><div class="fixed-footer">32 | På farten</div>''',
    33: '''<div class="product-copy page33-set">Inneholder én vindusklut, én universalklut og én tosidig moppklut.</div><div class="fixed-heading heading-page33">PLEIE OG RENGJØRING</div><div class="product-copy page33-glasses">Fjerner støv, smuss og fingermerker fra glass, skjermer og overflater.</div><div class="product-copy page33-dish">Absorberer 5–8 ganger sin egen vekt i vann. Ideell på kjøkkenet.</div><div class="product-copy page33-dust">Lange fibre fanger støv, og den andre siden rengjør effektivt.</div><div class="product-copy page33-window">Rengjør vinduer og speil blankt og uten striper.<br>40 x 40 cm</div><div class="product-copy page33-multi">Bruk tørr for glans eller våt for skånsom rengjøring og avfetting.<br>30 x 30 cm</div><div class="product-copy page33-mop">Tosidig mopp som brukes tørr eller våt for effektiv rengjøring.<br>50 x 60 cm</div><div class="fixed-footer">33 | Pleie og rengjøring</div>''',
    36: '''<div class="consultant-details" id="catalogConsultantDetails"><div class="consultant-contact"><strong>Din Tupperware-konsulent</strong><span id="catalogConsultantName">Navn lastes inn ...</span><span id="catalogConsultantEmail"></span><span id="catalogConsultantPhone"></span></div><div class="consultant-qrs"><a id="catalogStoreLink" target="tupperware_shop"><canvas id="catalogStoreQr"></canvas><span>Handle hos konsulenten</span></a><a id="catalogDigitalLink"><canvas id="catalogDigitalQr"></canvas><span>Åpne den digitale katalogen</span></a></div></div><div class="catalog-disclaimer"><span>*Disse varene blir tilgjengelige fra november 2026.</span><span>Produktene er tilgjengelige så langt lageret rekker.</span><span>Produktbilder og farger kan avvike.</span></div>''',
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

BODY_TRANSLATIONS = {
    9: [("Less waste, more freshness!", "Mindre svinn, mer friskhet!"),
        ("Ventsmart containers regulate humidity and air circulation to help your fruits and vegetables stay fresh longer. For a simpler daily life with less waste.", "Ventsmart-boksene regulerer fuktighet og luftsirkulasjon, slik at frukt og grønnsaker holder seg friske lenger. En enklere hverdag med mindre matsvinn.")],
    11: [("Store and transport homemade preparations", "Oppbevar og ta med hjemmelaget mat"),
         ("Your favorite salads with dressing in the lid", "Favorittsalaten din med dressing i lokket"),
         ("Jars, your allies for freshness for all your meals on the go. Take your favorite recipes with you wherever you go. Colorful salads, balanced meals or indulgent desserts remain fresh and ready to enjoy to accompany you throughout the day.", "Bokser som holder maten frisk når du er på farten. Ta med favorittrettene dine hvor du vil. Fargerike salater, balanserte måltider og gode desserter holder seg friske og klare til å nytes gjennom dagen.")],
    12: [("Ultra Clear® combines transparency and elegance! View your ingredients at a glance and keep your kitchen perfectly organized. With their easy-to-open airtight lid and their light and refined design, Ultra Clear® combines practicality, freshness and elegance on a daily basis.", "Ultra Clear® kombinerer gjennomsiktighet og eleganse! Se ingrediensene med et blikk og hold kjøkkenet ryddig. Det lufttette lokket er enkelt å åpne, og det lette designet forener funksjon, friskhet og eleganse i hverdagen.")],
    13: [("Organize, stack, simplify! Modular solutions to keep your ingredients within easy reach.", "Organiser, stable og gjør det enkelt! Fleksible løsninger som holder ingrediensene lett tilgjengelige."),
         ("Paper towels within easy reach.", "Tørkepapir lett tilgjengelig."),
         ("Practical for keeping the work surface clean.", "Praktisk for å holde arbeidsflaten ren.")],
    14: [("Unleash your culinary creativity! Solutions designed to support you in making biscuits, cakes and desserts, at every stage.", "Slipp matgleden løs! Smarte løsninger som hjelper deg gjennom alle trinn når du lager kjeks, kaker og desserter.")],
    15: [("Quick icing Mix approximately 30g of icing sugar with 1 tsp of lemon juice. Adjust the consistency with a little more icing sugar or lemon juice if necessary. Fill the Decorating Pen, make your decorations, then place in the refrigerator to set the icing.", "Rask glasur: Bland ca. 30 g melis med 1 ts sitronsaft. Juster konsistensen med litt mer melis eller sitronsaft. Fyll dekorpennen, pynt og sett bakverket kjølig så glasuren stivner."),
         ("Elevate every treat! Delicate icings, refined designs, or personalized messages: the Decorating Pen is the perfect tool for precisely decorating Christmas cookies, cakes, and other sweet treats. Easy to use, it transforms every creation into a unique dessert, as elegant as it is delicious.", "Gjør bakverket ekstra fint! Dekorpennen passer til presis pynting med glasur, mønstre og personlige hilsener på julekaker, kaker og andre søtsaker. Den er enkel å bruke og gjør hvert bakverk både personlig og innbydende.")],
    18: [("No task is too big for this champion! Chopping, mincing and mixing large quantities.", "Ingen oppgave er for stor! Hakker, finfordeler og blander store mengder."),
         ("Chop in seconds and create delicious recipes in no time!", "Hakk på sekunder og lag gode retter på kort tid!"),
         ("A mandoline worthy of a great chef for making all types of cuts.", "En mandolin for alle typer kutting."),
         ("The ultra-compact mandoline for fine and quick slicing.", "En svært kompakt mandolin for rask og fin skjæring.")],
    19: [("3 interchangeable blades for cutting into slices, cubes or sticks.", "Tre utskiftbare blader for skiver, terninger eller staver."),
         ("Ultra practical with its spaghetti and tagliatelle cone for cutting your vegetables.", "Svært praktisk med kjegler for grønnsaksspagetti og tagliatelle."),
         ("The pusher's blades hold the vegetables in place while protecting your fingers.", "Skyverens blader holder grønnsakene på plass og beskytter fingrene.")],
    20: [("Always within easy reach. Clever essentials that simplify every step in the kitchen and accompany you at every stage of your preparations.", "Alltid lett tilgjengelig. Smarte kjøkkenredskaper som gjør hvert trinn i forberedelsene enklere."),
         ("The star in the kitchen.", "Stjernen på kjøkkenet."),
         ("It mixes and scrapes efficiently down to the last bit.", "Blander og skraper effektivt helt til siste rest.")],
    22: [("The perfect partner for everyday cutting tasks.", "Perfekt til hverdagens kutteoppgaver."),
         ("Serrated blade for smooth-skinned foods.", "Tagget blad for matvarer med glatt skall."),
         ("Small, precise cuts.", "Små, presise kutt."),
         ("Slices bread and pastries with precision.", "Skjærer brød og bakverk presist."),
         ("Chop, slice, cut large pieces and mince.", "Hakk, skjær, del store biter og finhakk."),
         ("Cut safely with its non-slip surface and transfer easily thanks to its flexibility.", "Skjær trygt på den sklisikre flaten, og flytt maten enkelt med det fleksible brettet."),
         ("Safely sharpens smooth and serrated blades.", "Sliper glatte og taggete knivblad trygt.")],
    23: [("Divided plate that is microwave safe. Airtight and leakproof lid, and removable handle.", "Delt tallerken som tåler mikrobølgeovn, med lufttett lokk som ikke lekker og avtakbart håndtak."),
         ("Keep food fresh thanks to their airtight lids.", "Holder maten frisk med lufttette lokk."),
         ("Designed to help babies learn to eat independently. From 6 months old.", "Utviklet for å hjelpe små barn med å spise selv. Fra 6 måneder."),
         ("3 compartments of 85 ml to make 240 ml baby bottles.", "Tre rom på 85 ml til tilberedning av tåteflasker på 240 ml."),
         ("Perfect for children of all ages.", "Passer for barn i alle aldre.")],
    24: [("The microwave reveals its full potential. Bake, grill, gratin, create delicious steamed dishes, or prepare complete recipes with ease. Thanks to Tupperware® solutions, your microwave becomes a true everyday ally, allowing you to cook quickly, easily, and with consistently delicious results. Save time without compromising on taste and enjoy practical, varied cuisine adapted to your lifestyle.", "Få mer ut av mikrobølgeovnen. Bak, grill, gratiner, damp gode retter eller lag hele måltider enkelt. Med Tupperware® kan du lage maten raskt og praktisk med gode resultater. Spar tid uten å gå på kompromiss med smaken."),
         ("Unlimited homemade popcorn for young and old.", "Hjemmelaget popcorn for store og små."),
         ("Steam vegetables, fish, meat, pasta and grains in minutes, for healthy and tasty meals.", "Damp grønnsaker, fisk, kjøtt, pasta og korn på få minutter."),
         ("Browning, grilling and gratinating in the microwave is possible!", "Bruning, grilling og gratinering i mikrobølgeovn er mulig!")],
    25: [("Heat, melt and drain easily.", "Varm, smelt og hell av enkelt."),
         ("One single container to cook, drain, serve, store and reheat your pasta.", "Én beholder til å koke, helle av, servere, oppbevare og varme pasta."),
         ("Versatile, it cooks quickly from appetizer to dessert.", "Allsidig og rask, fra forrett til dessert."),
         ("The ideal solution for quick meals.", "Den ideelle løsningen for raske måltider.")],
    26: [("Crispy without excess oil. Quick, convenient, irresistible.", "Sprøtt uten overflødig olje. Raskt, enkelt og fristende."),
         ("Healthy, even and effortless cooking for consistently successful dishes.", "Sunn og jevn tilberedning med gode resultater hver gang."),
         ("The ideal size for roasting poultry and large cuts of meat to perfection.", "Ideell størrelse for perfekt steking av fjærkre og store kjøttstykker.")],
    30: [("Always within easy reach. Reusable, practical and durable bottles that go everywhere with you.", "Alltid lett tilgjengelig. Gjenbrukbare, praktiske og holdbare flasker som blir med overalt.")],
    32: [("A homemade lunch anywhere.", "Hjemmelaget lunsj hvor som helst."),
         ("Practical for preparing a balanced lunch thanks to its 3 compartments.", "Praktisk til en balansert lunsj med tre rom."),
         ("Reusable cutlery that clips together (knife, fork, spoon).", "Gjenbrukbart bestikk som klikkes sammen: kniv, gaffel og skje."),
         ("2-compartment lunch box, ideal for carrying meals and snacks.", "Matboks med to rom, ideell til måltider og mellommåltider.")],
    33: [("Includes: 1 window towel, 1 multipurpose towel and 1 mop towel 2 sided", "Inneholder én vindusklut, én universalklut og én tosidig moppklut."),
         ("Removes dust, dirt and fingerprints from glasses, screens and surfaces.", "Fjerner støv, smuss og fingermerker fra glass, skjermer og overflater."),
         ("Absorbs 5 to 8 times its weight in water. Ideal for cooking.", "Absorberer 5–8 ganger sin egen vekt i vann. Ideell på kjøkkenet."),
         ("Long fibers to capture dust, and one side for effective cleaning.", "Lange fibre fanger støv, og den andre siden rengjør effektivt."),
         ("Cleans and shines windows and mirrors without streaks, in one easy step.", "Rengjør vinduer og speil blankt og uten striper."),
         ("Use dry to shine, or wet to gently clean and degrease.", "Bruk tørr for glans eller våt for skånsom rengjøring og avfetting."),
         ("Double-sided mop: use dry or wet for effective cleaning", "Tosidig mopp som brukes tørr eller våt for effektiv rengjøring.")],
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
    ],
    6: [
        ("11184201", "Mixing bowl 2 l", 16.7, 9.5, 21.0, 14.5),
        ("11187510", "Ultimate mixing bowl 9.5 l", 37.7, 9.5, 21.8, 14.5),
        ("11186944", "Quick shake 500 ml", 59.5, 9.5, 22.0, 14.5),
        ("11184123", "Potato masher", 6.4, 24.0, 20.9, 14.0),
        ("11186681", "Twistable peeler", 27.3, 24.0, 22.0, 14.0),
        ("11161880", "A-series Utility Knife", 49.3, 24.0, 21.7, 14.0),
        ("11164878", "U-series Sharpener", 71.0, 24.0, 22.0, 14.0),
        ("11138015", "KPT Garlic star", 17.3, 38.0, 21.0, 15.0),
        ("11116527", "Ergologics can guru", 38.3, 38.0, 21.7, 15.0),
        ("MICROPLUS1L", "Microplus pitcher 1 l", 60.0, 38.0, 22.0, 15.0),
        ("11186857", "Ultrapro cocotte 500 ml", 6.0, 61.0, 21.0, 15.0),
        ("11186856", "Ultrapro 3,5 l", 27.0, 61.0, 22.0, 15.0),
        ("11186850", "Ultrapro 5,7 l", 49.0, 61.0, 22.0, 15.0),
        ("11186859", "Ultraplus 5 l", 71.0, 61.0, 22.0, 15.0),
        ("11186368", "Voila round 260 ml", 17.0, 76.0, 21.0, 15.0),
        ("11186369", "Voila round 500 ml", 38.0, 76.0, 22.0, 15.0),
        ("11186370", "Voila round 900 ml", 60.0, 76.0, 22.0, 15.0),
    ],
    7: [
        ("11178420", "Eco bottle 750 ml", 7.6, 10.0, 21.0, 22.0),
        ("11179922", "2 Eco+ bottle 500 ml", 28.6, 10.0, 21.9, 22.0),
        ("11170998", "Eco+ bottle slim 750 ml", 50.5, 10.0, 21.8, 22.0),
        ("11168955", "Eco bottle 750 ml", 72.3, 10.0, 21.8, 22.0),
        ("11155977", "Recycled microfibers window (2)", 36.8, 32.0, 27.0, 20.0),
    ],
}

CELL_OVERRIDES = {
    10: {
        "11169011": (51.5, 5.7, 42.0, 23.2),
        "11184136": (6.2, 34.7, 28.8, 20.0),
        "11184135": (35.5, 34.7, 28.8, 20.0),
        "11184137": (65.0, 34.7, 28.7, 20.0),
        "11184119": (6.2, 54.9, 28.8, 19.8),
        "11184120": (35.5, 54.9, 28.8, 19.8),
        "11184204": (65.0, 54.9, 28.7, 19.8),
        "11184105": (6.2, 75.0, 28.8, 18.5),
    }
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
            for product in page_products:
                override = CELL_OVERRIDES.get(page_number, {}).get(str(product["code"]))
                if override:
                    product.update(zip(("left", "top", "width", "height"), override))
            products.extend(page_products)
    for page, entries in MANUAL_PRODUCTS.items():
        for code, name, left, top, width, height in entries:
            product = {"page": page, "code": code, "name": name, "left": left, "top": top, "width": width, "height": height}
            if code == "MICROPLUS1L":
                product["direct_url"] = "https://tupperware-eu.com/no/products/set-pichet-et-spatule"
            products.append(product)
    return products


def extract_heading_overlays() -> dict[int, str]:
    overlays: dict[int, list[str]] = {}
    skip_pages = {1, 2, 3, 4, 5, 6, 7, 10, 16, 17, 18, 22, 28, 34, 36}
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


def extract_body_overlays() -> dict[int, str]:
    overlays: dict[int, list[str]] = {}
    with pdfplumber.open(SOURCE_PDF) as pdf:
        for page_number, translations in BODY_TRANSLATIONS.items():
            page = pdf.pages[page_number - 1]
            for english, norwegian in translations:
                pattern = re.escape(english).replace(r"\ ", r"\s+")
                matches = page.search(pattern, regex=True, case=False)
                if not matches:
                    anchor_words = re.findall(r"[A-Za-z0-9]+", english)[:2]
                    anchor_pattern = r"\W+".join(re.escape(word) for word in anchor_words)
                    matches = page.search(anchor_pattern, regex=True, case=False)
                    if not matches:
                        print(f"warning: translation source not found on page {page_number}: {english[:55]}")
                        continue
                    match = matches[0]
                    x0 = float(match["x0"])
                    top = float(match["top"])
                    width_percent = min(30.0, 96.0 - x0 / float(page.width) * 100)
                    estimated_lines = max(1, math.ceil(len(english) / max(20, width_percent * 1.05)))
                    overlays.setdefault(page_number, []).append(
                        f'<div class="body-translation" style="left:{max(0, x0-2)/float(page.width)*100:.3f}%;'
                        f'top:{max(0, top-1.5)/float(page.height)*100:.3f}%;'
                        f'width:{width_percent:.3f}%;height:{estimated_lines*2.4+.8:.3f}%">{html.escape(norwegian)}</div>'
                    )
                    continue
                match = matches[0]
                x0, x1 = float(match["x0"]), float(match["x1"])
                top, bottom = float(match["top"]), float(match["bottom"])
                pad_x, pad_y = 2.0, 1.5
                overlays.setdefault(page_number, []).append(
                    f'<div class="body-translation" style="left:{max(0, x0-pad_x)/float(page.width)*100:.3f}%;'
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
    href = html.escape(str(product.get("direct_url") or f"https://tupperware-eu.com/no/search?q={code}"), quote=True)
    return f'''<a class="product-row" href="{href}" target="tupperware_shop"
      data-search="{search}" data-page="{page}" data-code="{code}">
      <span>{name}</span><strong>{code} · Side {page}</strong>
      <small class="stock-status" data-stock-code="{code}">Sjekker lagerstatus ...</small></a>'''


def hotspot(product: dict[str, object]) -> str:
    code = html.escape(str(product["code"]))
    href = html.escape(str(product.get("direct_url") or f"https://tupperware-eu.com/no/search?q={code}"), quote=True)
    return (
        f'<a class="hotspot" href="{href}" '
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
    # These pages use manually positioned headings. PDF text order can attach
    # a spread heading to the next page or duplicate it near the footer.
    for manual_heading_page in (14, 19, 23, 24, 26, 30, 32, 33):
        heading_overlays.pop(manual_heading_page, None)
    body_overlays: dict[int, str] = {}
    sections = []
    for page in pages:
        page_number = int(page["page"])
        if page_number == 35:
            continue
        page_products = by_page.get(page_number, [])
        sections.append(
            f'''<section class="page" id="page-{page_number}" data-page="{page_number}">
              <div class="page-head"><span>Side {page_number}</span><span>{len(page_products)} lenker</span></div>
              <div class="sheet" style="--page-ratio:{ratio:.8f};">
                <img loading="lazy" decoding="async" src="/tw-host-vinter-2026-27/pages/{page["file"]}"
                  width="{page["width"]}" height="{page["height"]}" alt="Tupperware høst/vinter side {page_number}">
                {''.join(hotspot(product) for product in page_products)}
                {heading_overlays.get(page_number, '')}
                {body_overlays.get(page_number, '')}
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
    .contents-translation a { color:inherit; text-decoration:none; pointer-events:auto; }
    .contents-translation a:hover,.contents-translation a:focus-visible { text-decoration:underline; }
    .page-five-translation { left:4%; top:1%; width:92%; height:32%; background:#fff; border-left-color:#008c82; }
    #page-5 .sheet::after { content:"OPPBEVARING"; position:absolute; z-index:4; left:0; top:36.1%; width:100%; height:4.4%; display:flex; align-items:center; justify-content:center; background:#efeee2; color:#202522; font-weight:800; font-size:clamp(13px,2.2vw,30px); pointer-events:none; }
    .fixed-heading { position:absolute; z-index:4; left:0; width:100%; display:flex; align-items:center; justify-content:center; background:#efeee2; color:#202522; font-weight:800; font-size:clamp(13px,2.2vw,30px); pointer-events:none; }
    .fixed-footer { position:absolute; z-index:4; left:20%; bottom:.4%; width:60%; height:4.2%; display:flex; align-items:center; justify-content:center; background:#fff; color:#202522; font-weight:700; font-size:clamp(8px,1vw,14px); pointer-events:none; }
    .heading-page6-prep,.heading-page7 { top:2.7%; height:4.4%; }
    .heading-page6-cook { top:54.4%; height:4.4%; }
    .heading-page10 { top:29.6%; height:4.4%; }
    .heading-page16 { top:2.7%; height:4.4%; }
    .heading-page14 { top:2.7%; height:6.2%; }
    .heading-page22 { top:26.5%; height:4.5%; }
    .heading-page23 { top:4.2%; height:4.4%; }
    .heading-page24 { top:3.4%; height:4.4%; }
    .heading-page26 { top:32.8%; height:4.4%; }
    .heading-page30 { top:36.3%; height:4.2%; }
    .heading-page32 { top:4.1%; height:4.3%; }
    .heading-page33 { top:32.6%; height:4.3%; }
    .page10-info { left:35.5%; top:75%; width:58.2%; height:18.5%; background:#efeee2; border:0; box-shadow:none; font-size:clamp(8px,1vw,14px); }
    .page22-info { left:65.1%; top:52.5%; width:29.5%; height:21.5%; background:#efeee2; border:0; box-shadow:none; font-size:clamp(8px,.96vw,14px); }
    .recipe-intro { left:4.2%; top:48.1%; width:91%; height:10.2%; background:#efeee2; border:0; box-shadow:none; }
    .recipe-panel { background:#fff; border-left:4px solid #d96822; box-shadow:none; font-size:clamp(9px,1.15vw,16px); line-height:1.18; padding:1.25%; }
    .recipe-panel ul { margin:.25em 0 0 1.1em; padding:0; }
    .recipe-panel li { margin:0 0 .28em; }
    .recipe16-top { left:31.2%; top:59%; width:64%; height:20.4%; }
    .recipe16-lower { left:4.2%; top:78.8%; width:91%; height:16.4%; }
    .recipe17-top-right { left:31.2%; top:6.3%; width:64%; height:20%; background:#efeee2; }
    .recipe17-top-lower { left:4.3%; top:25.8%; width:91%; height:30%; background:#efeee2; }
    .recipe17-bottom-left { left:4.3%; top:57%; width:64%; height:18.8%; }
    .recipe17-bottom-lower { left:4.3%; top:75.4%; width:91%; height:18.5%; }
    .hummus-translation { left:5%; top:4%; width:45%; height:26%; }
    .recipe-28-top { left:31%; top:5%; width:64%; height:30%; }
    .recipe-28-middle { left:31%; top:38%; width:64%; height:18%; }
    .recipe-28-bottom { left:5%; top:58%; width:63%; height:34%; }
    .recipe-cover { position:absolute; z-index:2; background:#fff; pointer-events:none; }
    .recipe-28-top-cover { left:3%; top:24%; width:92%; height:13%; }
    .recipe-28-bottom-cover { left:3%; top:80%; width:92%; height:13%; }
    .recipe-28-footer { left:3%; top:93%; width:92%; height:5%; display:flex; align-items:center; justify-content:center; font-weight:700; }
    .warranty-translation { left:7%; top:13.1%; width:86%; height:39.8%; background:#fff; border-left-color:#008c82; box-shadow:none; }
    .heading-translation { position:absolute; z-index:4; display:flex; align-items:center; padding:0 .35em; background:#f1efe4; color:#202522; font-weight:800; line-height:1; text-transform:uppercase; font-size:clamp(8px,1.15vw,17px); pointer-events:none; white-space:nowrap; }
    .body-translation { position:absolute; z-index:4; display:flex; align-items:center; padding:.18em .3em; background:#fff; color:#202522; font-size:clamp(6px,.76vw,11px); line-height:1.14; font-weight:500; overflow:hidden; pointer-events:none; }
    .product-copy { position:absolute; z-index:4; padding:1%; background:#fff; color:#202522; font-size:clamp(7px,.92vw,13px); line-height:1.22; overflow:hidden; pointer-events:none; }
    .product-copy strong { display:block; margin-bottom:.6em; font-size:1.12em; }
    .product-copy p { margin:0 0 .55em; }
    .product-copy-page9 { left:66.1%; top:11%; width:29.4%; height:17.5%; background:#efeee2; }
    .page11-jar-one { left:36%; top:45.1%; width:28.3%; height:5.3%; padding:.35%; }
    .page11-jar-two { left:66%; top:45.1%; width:28.3%; height:5.3%; padding:.35%; }
    .page11-info { left:51.2%; top:55.1%; width:48.8%; height:38.8%; padding:4%; background:#efeee2; font-size:clamp(8px,1.1vw,15px); }
    .page12-info { left:4.6%; top:53.2%; width:29.5%; height:40.8%; padding:1.6%; background:#efeee2; font-size:clamp(8px,1vw,14px); }
    .page13-info { left:33.8%; top:25.6%; width:29.4%; height:20.9%; padding:1.2%; background:#efeee2; }
    .page13-paper { left:4.5%; top:64.5%; width:29.2%; height:3.2%; padding:.2% .5%; }
    .page13-chop { left:4.5%; top:88.6%; width:45%; height:3.2%; padding:.2% .5%; }
    .page14-info { left:67.3%; top:54.6%; width:29.4%; height:18.7%; padding:1.8%; background:#efeee2; }
    .page15-icing { left:35.2%; top:48%; width:29.6%; height:21%; padding:1.4%; }
    .page15-treat { left:4.2%; top:69.9%; width:45.2%; height:24.1%; padding:1.8%; background:#efeee2; }
    .page18-extra { left:54%; top:36.2%; width:40.8%; height:4.8%; padding:.2% .5%; }
    .page18-compact { left:54%; top:49.7%; width:40.8%; height:3.4%; padding:.2% .5%; }
    .page18-mando { left:7%; top:72.7%; width:42.8%; height:4.8%; padding:.2% .5%; }
    .page18-speedy { left:7%; top:84.1%; width:42.8%; height:3.9%; padding:.2% .5%; }
    .page19-dicer { left:66%; top:18.7%; width:28.6%; height:4.8%; padding:.3% .6%; background:#efeee2; }
    .page19-spiral { left:7.4%; top:43.8%; width:27.4%; height:5.8%; padding:.3% .6%; background:#efeee2; }
    .page19-pusher { left:7.4%; top:57.4%; width:27.4%; height:7.1%; padding:.3% .6%; background:#efeee2; }
    .page20-intro { left:44.3%; top:7.8%; width:55.7%; height:16%; padding:3%; background:#efeee2; font-size:clamp(8px,1vw,14px); }
    .page20-star { left:5.4%; top:32.7%; width:28.8%; height:4.2%; padding:.2% 1%; }
    .page20-spatula { left:5.4%; top:64.2%; width:28.8%; height:6.4%; padding:.2% 1%; }
    .page22-paring { left:5.2%; top:46.7%; width:28.8%; height:1.8%; padding:.1% .4%; background:#efeee2; }
    .page22-utility { left:35.4%; top:45.1%; width:28.8%; height:2.7%; padding:.1% .4%; background:#efeee2; }
    .page22-serrated { left:65.6%; top:45.1%; width:28.9%; height:2.7%; padding:.1% .4%; background:#efeee2; }
    .page22-bread { left:5.2%; top:66.7%; width:28.8%; height:2.9%; padding:.1% .4%; background:#efeee2; }
    .page22-chef { left:35.4%; top:66.7%; width:28.8%; height:2.9%; padding:.1% .4%; background:#efeee2; }
    .page22-board { left:6%; top:81.7%; width:31%; height:6.2%; padding:.1% .4%; }
    .page22-sharpener { left:66.7%; top:85.1%; width:27.4%; height:3.2%; padding:.1% .4%; }
    .page23-dish { left:53.2%; top:40%; width:40.6%; height:4.8%; padding:.1% .4%; background:#efeee2; }
    .page23-snack { left:8.9%; top:64.7%; width:36.8%; height:3.1%; padding:.1% .4%; background:#efeee2; }
    .page23-cutlery { left:53.4%; top:64.7%; width:40%; height:4.2%; padding:.1% .4%; background:#efeee2; }
    .page23-milk { left:9.2%; top:85.3%; width:37%; height:3.8%; padding:.1% .4%; background:#efeee2; }
    .page23-case { left:53.7%; top:85.4%; width:38%; height:2.1%; padding:.1% .4%; background:#efeee2; }
    .page24-intro { left:51.3%; top:10.3%; width:48.7%; height:28.5%; padding:4.5% 2%; background:#efeee2; font-size:clamp(8px,1vw,14px); }
    .page24-popcorn { left:6.1%; top:56.7%; width:41.8%; height:3.1%; padding:.1% .4%; }
    .page24-urban { left:53.5%; top:56.7%; width:40.3%; height:4.2%; padding:.1% .4%; }
    .page24-grill { left:6.4%; top:85.8%; width:40.6%; height:3.6%; padding:.1% .4%; }
    .page25-pitcher { left:5.8%; top:43.5%; width:27%; height:2.4%; padding:.1% .4%; background:#efeee2; }
    .page25-pasta { left:5.6%; top:62.8%; width:27.3%; height:6.2%; padding:.1% .4%; }
    .page25-cook { left:36.2%; top:64.7%; width:27%; height:4.3%; padding:.1% .4%; }
    .page25-healthy { left:67%; top:64.7%; width:27.2%; height:4.3%; padding:.1% .4%; }
    .page26-air { left:30.8%; top:13.7%; width:30.5%; height:3.8%; padding:.1% .4%; background:#efeee2; }
    .page26-round { left:7%; top:85.3%; width:41%; height:4.5%; padding:.1% .4%; background:#efeee2; }
    .page26-roast { left:56.8%; top:85.3%; width:38%; height:4.5%; padding:.1% .4%; background:#efeee2; }
    .page30-intro { left:5.1%; top:62.8%; width:59.5%; height:8.5%; padding:2.5% 3%; background:#efeee2; font-size:clamp(8px,1vw,14px); }
    .page32-slim { left:53.5%; top:23.1%; width:40%; height:4.5%; padding:.1% .4%; background:#efeee2; }
    .page32-divided { left:53.5%; top:43.6%; width:40%; height:5.2%; padding:.1% .4%; background:#efeee2; }
    .page32-cutlery { left:7%; top:65.2%; width:40%; height:5%; padding:.1% .4%; }
    .page32-lunch { left:7%; top:86%; width:40%; height:5.2%; padding:.1% .4%; }
    .page33-set { left:52.5%; top:25.3%; width:42.8%; height:4.8%; padding:.1% .4%; background:#efeee2; }
    .page33-glasses { left:5%; top:56.5%; width:28.6%; height:5.6%; padding:.1% .4%; background:#efeee2; }
    .page33-dish { left:35.6%; top:56.6%; width:28.5%; height:4.6%; padding:.1% .4%; background:#efeee2; }
    .page33-dust { left:66.7%; top:57.4%; width:28.5%; height:5.4%; padding:.1% .4%; background:#efeee2; }
    .page33-window { left:5%; top:84.1%; width:28.7%; height:7.2%; padding:.1% .4%; background:#efeee2; }
    .page33-multi { left:35.7%; top:85.4%; width:28.5%; height:5.8%; padding:.1% .4%; background:#efeee2; }
    .page33-mop { left:66.7%; top:85.2%; width:28.5%; height:6.2%; padding:.1% .4%; background:#efeee2; }
    .consultant-details { position:absolute; z-index:3; left:14%; top:46.5%; width:73%; height:34%; display:grid; grid-template-columns:1fr 1.35fr; align-items:center; gap:3%; padding:3%; background:#f3f4e8; color:#262626; text-align:center; font-size:clamp(10px,1.45vw,20px); border-radius:7%; }
    .consultant-contact { display:flex; flex-direction:column; gap:.55em; min-width:0; }
    .consultant-details strong { font-size:1.16em; text-transform:uppercase; }
    .consultant-details span { overflow-wrap:anywhere; }
    .consultant-qrs { display:grid; grid-template-columns:1fr 1fr; gap:5%; align-items:start; }
    .consultant-qrs a { display:grid; gap:.55em; color:#262626; text-decoration:none; font-weight:700; font-size:.72em; }
    .consultant-qrs canvas { display:block; width:100% !important; height:auto !important; aspect-ratio:1; background:#fff; padding:5%; }
    .catalog-disclaimer { position:absolute; z-index:4; left:7.5%; top:81%; width:65%; min-height:8.5%; display:flex; flex-direction:column; justify-content:center; gap:.2em; padding:1.2% 1.6%; background:#26342d; color:#fff; font-size:clamp(7px,.86vw,12px); line-height:1.22; pointer-events:none; }
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
