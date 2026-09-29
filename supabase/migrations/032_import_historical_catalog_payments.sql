with historical(reference_code, amount_nok, payment_status, paid_at, note, source_key) as (
  values
    ('LISBETHOVERBYE', 0, 'paid', date '2026-07-14', null, 'legacy-pdf-LISBETHOVERBYE'),
    ('VIVIANKONGSVOLD', 500, 'paid', date '2026-07-14', null, 'legacy-pdf-VIVIANKONGSVOLD'),
    ('ANITALOMNES', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-ANITALOMNES'),
    ('MARIANNGRONLIASHEIM', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-MARIANNGRONLIASHEIM'),
    ('RITALOVLAND', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-RITALOVLAND'),
    ('JORIDBRACKENHANSEN', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-JORIDBRACKENHANSEN'),
    ('EVASOLBERG', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-EVASOLBERG'),
    ('MAYBRITTGARENBJERKESETH', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-MAYBRITTGARENBJERKESETH'),
    ('LILLIANARVESEN', 199, 'paid', date '2026-07-14', null, 'legacy-pdf-LILLIANARVESEN'),
    ('ELSEROYMOGRAVEM', 199, 'paid', date '2026-07-15', null, 'legacy-pdf-ELSEROYMOGRAVEM'),
    ('ANNMARGRETHEVATNE', 199, 'paid', date '2026-07-16', null, 'legacy-pdf-ANNMARGRETHEVATNE'),
    ('MARENOVREBO', 199, 'paid', date '2026-07-16', 'Telefon 90734353.', 'legacy-pdf-MARENOVREBO'),
    ('LEIKNYKLAUDIUSSEN', 199, 'paid', date '2026-07-16', null, 'legacy-pdf-LEIKNYKLAUDIUSSEN'),
    ('ANNKRISTINLANGHANKE', 199, 'paid', date '2026-07-16', null, 'legacy-pdf-ANNKRISTINLANGHANKE'),
    ('MARIANNEHOVLANDPEDERSEN', 199, 'paid', date '2026-07-16', null, 'legacy-pdf-MARIANNEHOVLANDPEDERSEN'),
    ('TONEJUULOLSENGRINDALEN', 199, 'paid', date '2026-07-16', null, 'legacy-pdf-TONEJUULOLSENGRINDALEN'),
    ('HANNEMARIEBJERKHOLTNYHAUG', 199, 'paid', date '2026-07-17', null, 'legacy-pdf-HANNEMARIEBJERKHOLTNYHAUG'),
    ('JANEHKJOLLEBERG', 199, 'paid', date '2026-07-20', 'Mobil 99032342.', 'legacy-pdf-JANEHKJOLLEBERG'),
    ('AINANEBELMARKEGARD', 199, 'paid', date '2026-07-21', null, 'legacy-pdf-AINANEBELMARKEGARD'),
    ('ANNETTECPAULSEN', 199, 'gift', date '2026-07-22', 'Gave fra Vivian.', 'legacy-pdf-ANNETTECPAULSEN'),
    ('KARISELNESHELLA', 199, 'gift', date '2026-07-22', 'Gave fra Vivian.', 'legacy-pdf-KARISELNESHELLA'),
    ('MONAELLINGSENTOLLEFSEN', 199, 'gift', date '2026-07-22', 'Gave fra Vivian.', 'legacy-pdf-MONAELLINGSENTOLLEFSEN'),
    ('CICILIEVIK', 199, 'paid', date '2026-07-23', null, 'legacy-pdf-CICILIEVIK'),
    ('MAYHILDEGULLESTAD', 199, 'paid', date '2026-07-23', null, 'legacy-pdf-MAYHILDEGULLESTAD'),
    ('HEGEOPHEIM', 199, 'gift', date '2026-07-27', 'Gave fra Vivian.', 'legacy-pdf-HEGEOPHEIM'),
    ('KRISTINLIA', 199, 'paid', date '2026-07-28', null, 'legacy-pdf-KRISTINLIA'),
    ('LILLIANELISABETHDRILLENAUNE', 199, 'paid', date '2026-07-28', null, 'legacy-pdf-LILLIANELISABETHDRILLENAUNE'),
    ('EVAAMODTBLOM', 199, 'paid', date '2026-07-29', null, 'legacy-pdf-EVAAMODTBLOM'),
    ('ROARVIKEN', 199, 'paid', date '2026-07-29', null, 'legacy-pdf-ROARVIKEN'),
    ('MIAKATARINABREKKEN', 199, 'paid', date '2026-08-02', null, 'legacy-pdf-MIAKATARINABREKKEN'),
    ('TOVELINNERUD', 199, 'paid', date '2026-08-13', null, 'legacy-pdf-TOVELINNERUD'),
    ('SYLVIATHERESEGRODUM', 199, 'paid', date '2026-08-13', null, 'legacy-pdf-SYLVIATHERESEGRODUM'),
    ('ANITALESTEBERG', 199, 'paid', date '2026-08-13', null, 'legacy-pdf-ANITALESTEBERG'),
    ('INENESLEKARLSOEN', 199, 'paid', date '2026-08-18', null, 'legacy-pdf-INENESLEKARLSOEN'),
    ('ANJADRAGVOLD', 199, 'paid', date '2026-08-25', null, 'legacy-pdf-ANJADRAGVOLD')
)
insert into public.consultant_product_payments (
  consultant_id, product_key, amount_nok, payment_status, paid_at, note, source_key
)
select consultants.id, 'norsk-produktkatalog', historical.amount_nok,
       historical.payment_status, historical.paid_at, historical.note, historical.source_key
from historical
join public.consultants on consultants.reference_code = historical.reference_code
on conflict (source_key) do update set
  amount_nok = excluded.amount_nok,
  payment_status = excluded.payment_status,
  paid_at = excluded.paid_at,
  note = excluded.note,
  updated_at = now();

do $$
declare
  missing_count integer;
begin
  with expected(reference_code) as (
    values ('LISBETHOVERBYE'), ('VIVIANKONGSVOLD'), ('ANITALOMNES'),
      ('MARIANNGRONLIASHEIM'), ('RITALOVLAND'), ('JORIDBRACKENHANSEN'),
      ('EVASOLBERG'), ('MAYBRITTGARENBJERKESETH'), ('LILLIANARVESEN'),
      ('ELSEROYMOGRAVEM'), ('ANNMARGRETHEVATNE'), ('MARENOVREBO'),
      ('LEIKNYKLAUDIUSSEN'), ('ANNKRISTINLANGHANKE'), ('MARIANNEHOVLANDPEDERSEN'),
      ('TONEJUULOLSENGRINDALEN'), ('HANNEMARIEBJERKHOLTNYHAUG'),
      ('JANEHKJOLLEBERG'), ('AINANEBELMARKEGARD'), ('ANNETTECPAULSEN'),
      ('KARISELNESHELLA'), ('MONAELLINGSENTOLLEFSEN'), ('CICILIEVIK'),
      ('MAYHILDEGULLESTAD'), ('HEGEOPHEIM'), ('KRISTINLIA'),
      ('LILLIANELISABETHDRILLENAUNE'), ('EVAAMODTBLOM'), ('ROARVIKEN'),
      ('MIAKATARINABREKKEN'), ('TOVELINNERUD'), ('SYLVIATHERESEGRODUM'),
      ('ANITALESTEBERG'), ('INENESLEKARLSOEN'), ('ANJADRAGVOLD')
  )
  select count(*) into missing_count
  from expected
  left join public.consultants using (reference_code)
  where consultants.id is null;
  if missing_count > 0 then
    raise exception '% historiske betalinger mangler tilhørende konsulent', missing_count;
  end if;
end $$;
