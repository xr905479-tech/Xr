# HMI-Labor 4.0 – GitHub Pages + Supabase

**Keine Streamlit-Anmeldung und keine lokale Installation erforderlich.** Die Anwendung ist eine statische Website (HTML/CSS/JavaScript), die ihre Daten direkt über die Supabase-API übermittelt. Grundlage ist der getestete HMI-Prototyp 1.2.

## Inhalt

| Datei | Zweck |
|---|---|
| `index.html` | Teilnehmerseite: Mischanlage, HMI A/B, Fragen, Ergebnisse |
| `admin.html` | Passwortgeschütztes Admin-Dashboard, CSV-Export, QR-Code |
| `config.js` | **Öffentliche** Supabase-Projektadresse + Publishable/anon-Schlüssel (keine Secrets!) |
| `supabase_migration_v4.sql` | Ergänzt die **bereits vorhandenen** Tabellen der Version 3.0 um sichere Browserzugriffe |
| `README.md` | Diese Anleitung |

## 1. Supabase: Anonyme Anmeldungen aktivieren

1. Dein Supabase-Projekt öffnen.
2. **Authentication → Providers → Anonymous Sign-Ins** (Menübezeichnung kann leicht abweichen) aktivieren.
3. Dein bisheriges Schema mit `hmi_participants` und `hmi_results` bleibt bestehen.
4. **SQL Editor → New query**: die komplette `supabase_migration_v4.sql` einfügen und **Run** klicken.
5. Die Migration schafft die Tabelle `hmi_admins`, die Besitzerzuordnung pro Teilnehmer und Row-Level-Security-Regeln (RLS). **Nicht** erneut die alte `supabase_schema.sql` ausführen.

**Sicherheit:** Anonymous Sign-Ins erzeugen Supabase-Auth-Konten ohne Mail/Passwort. Alle Ergebniszugriffe werden mit einer anonymen Benutzerkennung durch RLS eingeschränkt. Anonymous Sign-Ins sind für offene Websites missbrauchsanfällig; Supabase empfiehlt CAPTCHA/Turnstile und angemessene Ratenlimits. Nutze die Seite für den beaufsichtigten Lehrversuch, nicht als allgemeine öffentliche Umfrage. Siehe https://supabase.com/docs/guides/auth/auth-anonymous

## 2. Admin-Konto anlegen

1. In Supabase **Authentication → Users → Add user** eine E-Mail/Passwort-Anmeldung für dich erstellen. E-Mail ggf. bestätigen.
2. **SQL Editor → New query** öffnen und **nur dort** (nicht in GitHub) ausführen, wobei du deine echte Admin-E-Mail ersetzt:

```sql
insert into public.hmi_admins(user_id)
select id from auth.users where email = 'DEINE_ADMIN_EMAIL@BEISPIEL.DE'
on conflict (user_id) do nothing;
```

3. Prüfen: Die Abfrage sollte genau ein Admin-Konto freischalten. Wenn `0 rows` betroffen sind, den E-Mail-Wert und das Supabase-Auth-Konto kontrollieren.
4. Die Anmeldung läuft über Supabase Auth in `admin.html`; der Zugang zu den Daten ist **serverseitig durch Supabase RLS** geschützt. Verwende ein eigenes starkes Passwort.

## 3. Öffentliche Supabase-Konfiguration

In Supabase findest du unter **Project Settings → API Keys** den **Publishable Key** (oder den älteren `anon`/public-Schlüssel). Unter **Project Settings → Data API** bzw. im Projektüberblick findest du die Projekt-URL.

Öffne `config.js` und ersetze genau diese beiden Platzhalter:

```js
window.HMI_CONFIG = {
  supabaseUrl: "https://DEIN-PROJEKT.supabase.co",
  supabasePublishableKey: "sb_publishable_..."
};
```

**NIEMALS** `service_role`, `secret key`, Datenbankpasswort oder Admin-Passwort in `config.js`, GitHub oder einen Screenshot schreiben. Der Publishable/anon-Schlüssel darf öffentlich sein; der Datenzugriff wird durch RLS geschützt.

## 4. GitHub Pages veröffentlichen (Repository `xr905479-tech/Xr`)

1. Öffne dein Repository `Xr` auf GitHub.
2. Lade die **fünf Einzeldateien** (nicht die ZIP!) `index.html`, `admin.html`, `config.js`, `supabase_migration_v4.sql`, `README.md` in das **Hauptverzeichnis des Repositories** hoch. Die alte Streamlit-Unterordnerstruktur darf im Repo bleiben; sie wird nicht gebraucht.
3. GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**, Branch `main`, Folder `/(root)` → **Save**.
4. Nach der Bereitstellung ist die Teilnehmerseite voraussichtlich erreichbar unter:
   `https://xr905479-tech.github.io/Xr/`
5. Admin-Seite:
   `https://xr905479-tech.github.io/Xr/admin.html`
6. Beide URLs sind **Beispiele auf Basis des bestehenden Repository-Namens**, noch nicht als aktiv verifiziert. Maßgeblich ist die auf GitHub unter **Settings → Pages** angezeigte Website-Adresse.

Die Website erfordert Internetzugang auf den Smartphones. Kein gemeinsames WLAN nötig.

## 5. Funktionsprüfung

1. Teilnehmerseite auf einem Smartphone öffnen. Bei aktivem Anonymous Sign-In erscheint automatisch eine Kennung `T...` und die zugewiesene Reihenfolge.
2. Erstes HMI: vier Aufgaben → drei Bewertungen → zweites HMI: vier Aufgaben → drei Bewertungen.
3. Nach dem zweiten Fragebogen erscheint **„Ergebnisse erfolgreich an Supabase übertragen“**.
4. Mit einem **anderen Browserprofil/Inkognito-Gerät** die Admin-Seite öffnen und mit der freigeschalteten E-Mail/Passwort anmelden.
5. Unter „Abgeschlossene Vergleiche“ sollte ein neuer Datensatz stehen; CSV herunterladen und auf Plausibilität prüfen.
6. Danach den Test möglichst mit 2–3 Personen wiederholen (A→B / B→A prüfen).

## 6. Was wissenschaftlich und technisch zu beachten ist

- Es handelt sich um ein **Lehr-Experiment**, nicht um eine Produktionssteuerung.
- Der Browser misst die Zeiten und meldet die Ergebnisse an die Datenbank. Bei einer öffentlich zugänglichen JavaScript-Anwendung kann ein technisch versierter Nutzer Messwerte verändern. Die Daten sind für den beaufsichtigten Unterricht geeignet, aber nicht manipulationssicher.
- Die Gruppenzuordnung folgt dem fortlaufenden Teilnehmerzähler (abwechselnd AB/BA). Vorabtests und abgebrochene Teilnahmen beeinflussen die Zählung. **Vor dem Referat** die Testdaten im Supabase-Dashboard kontrolliert entfernen und Teilnehmerzuordnungen prüfen; Identitätszähler bleiben dabei bestehen.
- Teilnehmer müssen **nicht** ihren Namen oder ihre E-Mail eingeben. Supabase speichert technische Auth-Kontoinformationen. Teilnehmende über die Datenspeicherung informieren.
- Ein öffentliches Repository enthält den Quellcode der Anwendung. Der Datenzugang bleibt dank RLS geschützt; Supabase-Policies vor dem Live-Einsatz unbedingt testen.
- Bei erneutem Öffnen derselben Browser-Sitzung wird die Teilnahme als abgeschlossen erkannt.
- Falls du in `admin.html` „nicht als Admin freigeschaltet“ siehst: prüfen, ob E-Mail/Passwort-Konto existiert und `hmi_admins` die richtige Benutzer-ID enthält.

## Fehlerhilfe

| Meldung | Typische Ursache |
|---|---|
| „Cloud-Verbindung nicht eingerichtet“ | Platzhalter in `config.js` nicht ersetzt oder JS-Bibliothek nicht geladen |
| „Anonymous sign-ins are disabled“ | Supabase Auth Anonymous Sign-Ins aktivieren |
| „permission denied“ / „row-level security“ | SQL-Migration fehlt oder RLS-Policy nicht korrekt angelegt |
| Admin sieht keine Daten | Admin-UID nicht in `hmi_admins` freigeschaltet |
| Upload klappt nicht | Internetverbindung / Supabase-API prüfen und „Übertragung erneut versuchen“ |

## Links zur Dokumentation

- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- Supabase Anonymous Sign-ins: https://supabase.com/docs/guides/auth/auth-anonymous
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
