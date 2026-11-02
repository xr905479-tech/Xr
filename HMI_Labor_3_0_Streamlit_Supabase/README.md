# HMI-Labor 3.0 – Streamlit Community Cloud + Supabase

Eine öffentliche, smartphonefähige HMI-Simulation (Legacy A gegen Guided B) mit zentraler Datenbank und passwortgeschütztem Admin-Dashboard. Weiterverwendet wurde die Maschinensteuerung aus dem funktionierenden lokalen Prototyp 2.1. Keine Python-Installation auf Teilnehmergeräten und kein lokaler Server erforderlich.

## Einrichtung – alles im Browser

### 1. Supabase-Datenbank

1. Auf https://supabase.com/ ein kostenfreies Projekt anlegen.
2. **SQL Editor** öffnen, Inhalt von `supabase_schema.sql` einfügen und ausführen.
3. Unter **Project Settings → API** (Bezeichnungen können abweichen) die **Project URL** und einen *serverseitigen Secret/Service-Role-Schlüssel* kopieren. Schlüssel **niemals** in GitHub, in JavaScript oder im Browser veröffentlichen. Bei neueren Supabase-Projekten können die Schlüssel anders benannt sein; der verwendete Schlüssel muss serverseitig vollen Tabellenzugriff besitzen.

### 2. GitHub

1. Auf https://github.com/ ein neues Repository anlegen.
2. Diese Dateien hochladen: `app.py`, `requirements.txt`, `supabase_schema.sql`, `hmi_component/index.html`, `.gitignore` sowie optional die README und die Beispiel-Secrets.
3. **Niemals eine echte `secrets.toml` hochladen.** Das Repository darf öffentlich sein, solange keine Schlüssel enthalten sind.

### 3. Streamlit Community Cloud

1. https://share.streamlit.io/ aufrufen, mit GitHub verbinden.
2. **Create app** → Repository auswählen → Main file `app.py` → deployen.
3. **App settings → Secrets** öffnen, die vier Werte aus `.streamlit/secrets.toml.example` mit echten Zugangsdaten ergänzen.
4. `PUBLIC_URL` auf die echte `https://…streamlit.app`-Adresse setzen, App bei Bedarf neu starten.
5. Teilnehmerlink: `PUBLIC_URL` (ohne Parameter); Admin: `PUBLIC_URL/?admin=1`.

### 4. Test vor dem Referat

1. Auf Smartphone A den Teilnehmerlink öffnen und Versuch A/B vollständig durchführen.
2. Auf Smartphone B getrennt öffnen: B/A wird über fortlaufende Teilnehmernummern verteilt.
3. Im Admin-Dashboard beide Ergebnisse kontrollieren.
4. CSV herunterladen und Inhalt kontrollieren.
5. Direkt vor dem Referat die App öffnen, damit sie bei einem eventuellen Schlafmodus aufwacht.

## Sicherheits- und Methodik-Hinweise

- `SUPABASE_SERVICE_ROLE_KEY` ist ein **privates Server-Geheimnis**. Der Schlüssel wird nur durch Streamlit-Python verarbeitet, niemals durch HTML/JavaScript.
- Die Tabellen haben **Row Level Security** ohne öffentliche Policies. Die Streamlit-Serverinstanz greift mit dem geheimen Schlüssel zu.
- Adminzugriff benötigt `ADMIN_PASSWORD`; lege ein langes, einzigartiges Passwort fest. Diese einfache Absicherung ist für ein kleines anonymes Seminar gedacht, nicht für sensible/personenbezogene Daten.
- Gespeichert werden zufällige Teilnehmer-IDs, Zeit, Fehler, Aufgabenabschluss und Bewertungen. Es werden keine Namen benötigt. Einwilligung/Information und Aufbewahrungsdauer vor dem Versuch klären.
- Eine neue Teilnahme wird durch den Streamlit-Server erzeugt. Fortlaufende Nummern verteilen die Reihenfolgen abwechselnd AB/BA. Bei abgebrochenen Teilnahmen kann die Anzahl *abgeschlossener* AB/BA-Durchgänge ungleich sein.
- Das Experiment speichert einen Datensatz **erst nach beiden vollständigen Durchgängen**. Bei Verbindungsverlust/Reload geht die laufende Browser-Sitzung möglicherweise verloren.
- Das ist ein Demonstrationsversuch, kein validiertes Messinstrument. Alle vier Aufgaben müssen vollständig gelöst werden; ein Zeitlimit/Abbruchmodus ist noch nicht implementiert.
- Kostenlose Hostingdienste können schlafen oder Kontingentgrenzen verändern. Vor der Vorführung einen Probelauf durchführen.
- Für eine erneute Seminargruppe Daten nach Sicherung über Supabase löschen (Resultate zuerst, danach Teilnehmer); der Nummernzähler wird dabei nicht automatisch zurückgesetzt.
