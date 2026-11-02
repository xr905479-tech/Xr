-- In Supabase > SQL Editor ausführen.
-- Alle Daten sind für anonyme Supabase-Benutzer gesperrt; nur der
-- serverseitig verwendete Service-Role-Key darf auf die Tabellen zugreifen.
create table if not exists public.hmi_participants (
    id uuid primary key default gen_random_uuid(),
    number bigint generated always as identity unique,
    created_at timestamptz not null default now()
);
create table if not exists public.hmi_results (
    participant_id uuid primary key references public.hmi_participants(id) on delete cascade,
    test_order text not null check (test_order in ('AB','BA')),
    runs jsonb not null,
    created_at timestamptz not null default now()
);
alter table public.hmi_participants enable row level security;
alter table public.hmi_results enable row level security;
-- Absichtlich keine Policies: direkte Browser-Abfragen sind nicht erlaubt.
-- Hinweis: Für ein neues Referat können Daten über das Supabase-Dashboard
-- nach Export manuell gelöscht werden; Identitätszähler beginnt dabei nicht bei 1.
