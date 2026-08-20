# NorskKatalogMedLinker

Dette er en ren prosjektkopi for den norske Tupperware-katalogen med klikkbare produktlenker.

Prosjektet inneholder bare filene som trengs for:

- norsk produktkatalog på `/`
- digital katalog/PDF-lignende katalog på `/digital-katalog?ref=KONSULENTREF`
- konsulentens egne varer på `/egne-varer`
- party-demo på `/party`
- API mot samme Supabase-database som `tupperware-norsk-nettkatalog-v2`
- automatisk deploy via Render når GitHub oppdateres

## Viktige filer

- `server.py` starter webappen og API-et.
- `index.html`, `styles.css` og `app.js` er hovedkatalogen.
- `party.html` er en visbar party-demo for konsulent og kunde.
- `party_storage.py` kobler partydata til Supabase når party-tabellene finnes.
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

### Party MVP i Supabase

For å teste `/party` fra flere maskiner må party-tabellene opprettes i samme Supabase-prosjekt.

Kjør migrasjonen:

```text
supabase/migrations/019_party_mvp.sql
```

Etter migrasjonen vil `/api/party-demo-state` og `/api/party-demo-action` automatisk bruke delt lagring i Supabase. Hvis tabellene ikke finnes ennå, faller løsningen tilbake til lokal demo-state i `server.py`.

Merk:

- Dette er en enkel MVP for testing og videre utvikling.
- RLS i `019_party_mvp.sql` er foreløpig bevisst åpen for `anon` og `authenticated` slik at kundesiden og testflyten virker uten innlogging.
- Neste steg bør være å knytte party til konsulent-ID/reference code og stramme inn tilgangsstyringen.

## Render

Render skal kobles til GitHub-repoet for dette prosjektet.

Anbefalt oppsett:

- Runtime: `Python`
- Build command: `echo Ready`
- Start command: `poetry run python server.py`
- Health check path: `/api/health`
- Auto deploy: `On commit`

Da publiseres nye endringer automatisk når du pusher til GitHub.

### Deploy av `/party`

`/party` ligger i samme Render-app som resten av NorskKatalogMedLinker. Det betyr:

- ingen ny Render-tjeneste trengs
- party blir tilgjengelig under eksisterende domene på `/party`
- når GitHub oppdateres, deployes party sammen med resten av appen

## Lokal test

```powershell
python server.py
```

Åpne:

```text
http://127.0.0.1:8789/digital-katalog?ref=LISBETHOVERBYE
http://127.0.0.1:8789/party
```

Produktlenker til Tupperware skal gå via norsk side, for eksempel:

```text
https://tupperware-eu.com/no/search?q=11155861&ref=LISBETHOVERBYE
```
