-- HMI-Labor 4.0: Ausführung im Supabase SQL Editor nach dem Schema der Version 3.0.
-- Das bisherige Schema hat RLS an und keine Policies; dieses Skript aktiviert
-- gezielte Browser-Zugriffe. Vorher Daten sichern, falls bereits echte Ergebnisse vorliegen.
begin;

alter table public.hmi_participants add column if not exists owner_id uuid references auth.users(id) on delete cascade;
create unique index if not exists hmi_participants_owner_unique on public.hmi_participants(owner_id);

create table if not exists public.hmi_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.hmi_participants enable row level security;
alter table public.hmi_results enable row level security;
alter table public.hmi_admins enable row level security;

-- Supabase Auth + Row Level Security: nur explizit berechtigte Admin-UIDs.
create or replace function public.hmi_is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.hmi_admins
    where user_id = (select auth.uid())
  ) and coalesce((select (auth.jwt()->>'is_anonymous')::boolean),true) = false;
$$;
revoke all on function public.hmi_is_admin() from public, anon;
grant execute on function public.hmi_is_admin() to authenticated;

-- Einmalige Teilnehmerzuordnung über eine atomare INSERT-Operation.
-- Es werden ausschließlich echte Supabase-Anonym-Accounts zugelassen.
create or replace function public.hmi_join()
returns table (participant_id uuid, participant_number bigint, test_order text)
language plpgsql security definer set search_path = '' as $$
declare v_user uuid; v_id uuid; v_num bigint;
begin
  v_user := (select auth.uid());
  if v_user is null or coalesce((select (auth.jwt()->>'is_anonymous')::boolean),false) is not true then
    raise exception 'Nur anonyme Versuchsteilnehmer können teilnehmen';
  end if;
  insert into public.hmi_participants(owner_id) values(v_user)
    on conflict (owner_id) do update set owner_id = excluded.owner_id
    returning id, number into v_id, v_num;
  return query select v_id, v_num, case when (v_num % 2)=1 then 'AB'::text else 'BA'::text end;
end; $$;
revoke all on function public.hmi_join() from public, anon;
grant execute on function public.hmi_join() to authenticated;

-- Ehemalige Policies, falls Migration erneut ausgeführt wird.
drop policy if exists "hmi_participant_read_own_or_admin" on public.hmi_participants;
drop policy if exists "hmi_result_read_own_or_admin" on public.hmi_results;
drop policy if exists "hmi_result_insert_own" on public.hmi_results;
drop policy if exists "hmi_admin_own" on public.hmi_admins;

create policy "hmi_participant_read_own_or_admin"
on public.hmi_participants for select to authenticated
using (owner_id = (select auth.uid()) or (select public.hmi_is_admin()));

create policy "hmi_result_read_own_or_admin"
on public.hmi_results for select to authenticated
using (
  (select public.hmi_is_admin()) or
  exists (select 1 from public.hmi_participants p
          where p.id = hmi_results.participant_id and p.owner_id = (select auth.uid()))
);

create policy "hmi_result_insert_own"
on public.hmi_results for insert to authenticated
with check (
  coalesce((select (auth.jwt()->>'is_anonymous')::boolean),false) is true
  and exists (select 1 from public.hmi_participants p
      where p.id = hmi_results.participant_id
        and p.owner_id = (select auth.uid())
        and hmi_results.test_order = case when (p.number % 2)=1 then 'AB' else 'BA' end)
  and jsonb_typeof(runs)='array'
  and jsonb_array_length(runs)=2
);

create policy "hmi_admin_own" on public.hmi_admins
for select to authenticated using (user_id=(select auth.uid()));

-- Den Zugriff auf die Tabellen ausdrücklich begrenzen. Kein Schreiben in
-- Teilnehmer- oder Admin-Tabellen über den Browser; Join via RPC.
revoke all on public.hmi_participants, public.hmi_results, public.hmi_admins from anon;
revoke all on public.hmi_participants, public.hmi_results, public.hmi_admins from authenticated;
grant select on public.hmi_participants to authenticated;
grant select, insert on public.hmi_results to authenticated;
grant select on public.hmi_admins to authenticated;

commit;

-- NACH Erstellen des Admin-Kontos in Supabase Authentication -> Users
-- die eigene Admin-E-Mail einsetzen und die folgende Zeile SEPARAT ausführen:
-- insert into public.hmi_admins(user_id)
-- select id from auth.users where email = 'DEINE_ADMIN_EMAIL@BEISPIEL.DE'
-- on conflict (user_id) do nothing;
-- Die Admin-E-Mail bitte nicht in eine öffentliche GitHub-Datei schreiben.
