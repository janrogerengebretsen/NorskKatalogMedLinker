alter table public.party_events
add column if not exists consultant_ref text;

update public.party_events
set consultant_ref = 'LISBETHOVERBYE'
where consultant_ref is null or btrim(consultant_ref) = '';

alter table public.party_events
alter column consultant_ref set default 'LISBETHOVERBYE';

alter table public.party_events
alter column consultant_ref set not null;

create index if not exists party_events_consultant_ref_idx
on public.party_events (consultant_ref, starts_at desc);

comment on column public.party_events.consultant_ref is
  'Reference code for the consultant who owns the party. Party MVP is currently enabled only for approved consultants.';
