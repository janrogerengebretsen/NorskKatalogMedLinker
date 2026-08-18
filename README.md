# NorskKatalogMedLinker

Dette er en ren prosjektkopi for den norske Tupperware-katalogen med klikkbare produktlenker.

Prosjektet inneholder bare filene som trengs for:

- norsk produktkatalog på `/`
- digital katalog/PDF-lignende katalog på `/digital-katalog?ref=KONSULENTREF`
- konsulentens egne varer på `/egne-varer`
- API mot samme Supabase-database som `tupperware-norsk-nettkatalog-v2`
- automatisk deploy via Render når GitHub oppdateres

## Viktige filer

- `server.py` starter webappen og API-et.
- `index.html`, `styles.css` og `app.js` er hovedkatalogen.
- `catalog-demo/index.html` og `catalog-demo/pages/` er den digitale katalogen med sidebilder og lenkeflater.
- `consultant_registry.py` leser konsulenter, kjøpte produkter og egne varer fra Supabase.
- `official_catalog.py` henter produktdata fra Tupperwares norske nettbutikk.
- `render.yaml` beskriver Render-tjenesten.
- `.env.example` viser miljøvariablene som må ligge i Render.

## Supabase

Bruk samme Supabase-prosjekt som før:

```text
SUPABASE_URL=https://coekzqrjiuwhslzwldiw.supabase.co
SUPABASE_ANON_KEY=legges inn som hemmelig verdi i Render
CATALOG_SYNC_TOKEN=legges inn som hemmelig verdi i Render
```

Ikke legg ekte nøkler i GitHub. Bruk Render > Environment.

## Render

Render skal kobles til GitHub-repoet for dette prosjektet.

Anbefalt oppsett:

- Runtime: `Python`
- Build command: `echo Ready`
- Start command: `poetry run python server.py`
- Health check path: `/api/health`
- Auto deploy: `On commit`

Da publiseres nye endringer automatisk når du pusher til GitHub.

## Lokal test

```powershell
python server.py
```

Åpne:

```text
http://127.0.0.1:8789/digital-katalog?ref=LISBETHOVERBYE
```

Produktlenker til Tupperware skal gå via norsk side, for eksempel:

```text
https://tupperware-eu.com/no/search?q=11155861&ref=LISBETHOVERBYE
```
