with consultant_seed (reference_code, display_name, email, catalog_slug) as (
  values
    ('LISBETHOVERBYE', 'Lisbeth Øverbye', 'lisbeth@elektron.no', 'lisbeth-overbye'),
    ('VIVIANKONGSVOLD', 'Vivian Kongsvold', 'viviankongsvold@gmail.com', 'vivian-kongsvold'),
    ('ANITALOMNES', 'Anita Lomnes', 'tw-anita@epost.no', 'anita-lomnes'),
    ('MARIANNGRONLIASHEIM', 'Mariann Grønli Åsheim', 'mariannaash@hotmail.com', 'mariann-gronli-asheim'),
    ('RITALOVLAND', 'Rita Løvland', 'ritlo015@gmail.com', 'rita-lovland'),
    ('JORIDBRACKENHANSEN', 'Jorid Hansen', 'jorid1901@gmail.com', 'jorid-hansen'),
    ('EVASOLBERG', 'Eva Irene Solberg', 'evas@live.no', 'eva-irene-solberg'),
    ('MAYBRITTGARENBJERKESETH', 'Maj Britt Bjerkseth', 'maybjerks@gmail.com', 'maj-britt-bjerkseth'),
    ('LILLIANARVESEN', 'Lilliann Arvesen', 'larvesen@live.no', 'lilliann-arvesen'),
    ('ELSEROYMOGRAVEM', 'Else Røymo Gravem', 'elsergravem@hotmail.com', 'else-roymo-gravem'),
    ('ANNMARGRETHEVATNE', 'Ann Margrethe Dahl Vatne', 'Annvatne@gmail.com', 'ann-margrethe-dahl-vatne'),
    ('MARENOVREBO', 'Maren Øvrebø', 'maren.ovrebo@ovrebo.no', 'maren-ovrebo'),
    ('LEIKNYKLAUDIUSSEN', 'Leikny Klaudiussen', 'leik63@hotmail.com', 'leikny-klaudiussen'),
    ('ANNKRISTINLANGHANKE', 'Ann Kristin Langhanke', 'langhanke1@msn.com', 'ann-kristin-langhanke'),
    ('MARIANNEHOVLANDPEDERSEN', 'Marianne Hovland Pedersen', 'marped2@yahoo.com', 'marianne-hovland-pedersen'),
    ('TONEJUULOLSENGRINDALEN', 'Tone Grindalen', 'togrindalen@yahoo.no', 'tone-grindalen'),
    ('HANNEMARIEBJERKHOLTNYHAUG', 'Hanne Marie Nyhaug', 'hamabjeny@gmail.com', 'hanne-marie-nyhaug'),
    ('JANEHKJOLLEBERG', 'Jane Carin Kjølleberg', 'janekjolleberg@gmail.com', 'jane-carin-kjolleberg'),
    ('AINANEBELMARKEGARD', 'Aina Nebel Markegård', 'ainanebel@hotmail.com', 'aina-nebel-markegard'),
    ('ANNETTECPAULSEN', 'Anette C Paulsen', 'AYAPAUL@OUTLOOK.com', 'anette-c-paulsen'),
    ('KARISELNESHELLA', 'Kari Selnes Hella', 'kshella@sf-nett.no', 'kari-selnes-hella'),
    ('MONAELLINGSENTOLLEFSEN', 'Mona Ellingsen Tollefsen', 'MONAET1980@gmail.com', 'mona-ellingsen-tollefsen'),
    ('CICILIEVIK', 'Cicilie Vik', 'ciciliev@online.no', 'cicilie-vik'),
    ('MAYHILDEGULLESTAD', 'May Hilde Gullestad', 'milde96@hotmail.no', 'may-hilde-gullestad'),
    ('HEGEOPHEIM', 'Hege Opheim', 'hege.opheim@icloud.com', 'hege-opheim'),
    ('KRISTINLIA', 'Kristin Lia', 'Kristin.Lia@hotmail.com', 'kristin-lia'),
    ('LILLIANELISABETHDRILLENAUNE', 'Lillian Elisabeth Drilen Aune', 'l_drilen@hotmail.com', 'lillian-elisabeth-drilen-aune'),
    ('EVAAMODTBLOM', 'Eva Åmodt Blom', 'eva.a.blom@nordre-land.kommune.no', 'eva-amodt-blom'),
    ('ROARVIKEN', 'Roar Viken', 'roar.viken@gmail.com', 'roar-viken')
), saved_consultants as (
  insert into public.consultants as existing (
    reference_code,
    display_name,
    email,
    catalog_slug,
    status,
    public_listing,
    consented_at,
    verified_at
  )
  select
    reference_code,
    display_name,
    email,
    catalog_slug,
    'active'::public.consultant_status,
    true,
    now(),
    now()
  from consultant_seed
  on conflict (reference_code) do update set
    display_name = excluded.display_name,
    email = coalesce(existing.email, excluded.email),
    catalog_slug = excluded.catalog_slug,
    status = 'active',
    public_listing = true,
    consented_at = coalesce(existing.consented_at, now()),
    verified_at = coalesce(existing.verified_at, now())
  returning id
)
insert into public.subscriptions (consultant_id, plan, status)
select id, 'free', 'active'
from saved_consultants
where not exists (
  select 1
  from public.subscriptions
  where subscriptions.consultant_id = saved_consultants.id
    and subscriptions.ends_at is null
);
