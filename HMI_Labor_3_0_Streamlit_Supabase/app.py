"""HMI-Labor 3.0: öffentliche Teilnehmeransicht, serverseitige Supabase-Speicherung."""
from __future__ import annotations
import csv
import hmac
import io
import json
import re
import uuid
from urllib.parse import quote

import pandas as pd
import qrcode
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="HMI-Labor | Mensch–Maschine–Experiment", page_icon="⚙️", layout="wide")
st.markdown("""<style>
.block-container{max-width:1100px;padding-top:1.6rem}
[data-testid="stMetric"]{background:#f1f5f9;padding:1rem;border-radius:12px}
</style>""", unsafe_allow_html=True)

ROOT = __import__('pathlib').Path(__file__).parent
hmi = components.declare_component("hmi_lab_interface", path=str(ROOT / "hmi_component"))


def get_secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def supabase(method: str, table: str, *, params: dict | None = None, payload=None):
    url = get_secret("SUPABASE_URL").rstrip("/")
    key = get_secret("SUPABASE_SERVICE_ROLE_KEY")
    if not url.startswith("https://") or not key:
        raise RuntimeError("Supabase-Zugangsdaten fehlen. Bitte Streamlit-Secrets einrichten.")
    if table not in ("hmi_participants", "hmi_results"):
        raise ValueError("Unzulässige Tabelle")
    headers = {"apikey": key, "Authorization": "Bearer " + key,
               "Content-Type": "application/json", "Accept": "application/json",
               "Prefer": "return=representation"}
    response = requests.request(method, url + "/rest/v1/" + table, headers=headers,
                                params=params, json=payload, timeout=15)
    if not response.ok:
        raise RuntimeError(f"Datenbankfehler (HTTP {response.status_code}). Bitte Konfiguration prüfen.")
    return response.json() if response.content else []


def join():
    rows = supabase("POST", "hmi_participants", payload={})
    if len(rows) != 1:
        raise RuntimeError("Teilnehmerkennung konnte nicht erzeugt werden")
    row = rows[0]
    return row["id"], "AB" if int(row["number"]) % 2 else "BA", int(row["number"])


def validate_result(value, expected_id: str, expected_order: str):
    if not isinstance(value, dict) or value.get("kind") != "completed":
        raise ValueError("Unvollständige Übertragung")
    if value.get("participant_id") != expected_id or value.get("order") != expected_order:
        raise ValueError("Teilnehmerkennung oder Reihenfolge stimmen nicht überein")
    runs = value.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        raise ValueError("Es werden genau zwei Testdurchgänge benötigt")
    if [r.get("interface") for r in runs] != list(expected_order):
        raise ValueError("Falsche Reihenfolge der Oberflächen")
    safe = []
    for i, r in enumerate(runs):
        duration = r.get("duration")
        errors = r.get("errors")
        target = r.get("targetRpm")
        tasks = r.get("tasks")
        ratings = r.get("ratings")
        if (not isinstance(duration, (int, float)) or isinstance(duration, bool)
                or not 0 <= duration <= 1800):
            raise ValueError("Ungültige Bearbeitungszeit")
        if not isinstance(errors, int) or isinstance(errors, bool) or not 0 <= errors <= 500:
            raise ValueError("Ungültiger Fehlerwert")
        if target != (1500 if i == 0 else 1200):
            raise ValueError("Ungültiger Drehzahl-Sollwert")
        if (not isinstance(tasks, list) or len(tasks) != 4 or
                [t.get("task") for t in tasks] != [1, 2, 3, 4] or
                any(t.get("success") is not True or not isinstance(t.get("seconds"), (float, int))
                    or isinstance(t.get("seconds"), bool) or not 0 <= t["seconds"] <= 1800 for t in tasks)):
            raise ValueError("Unvollständige Aufgaben")
        if (not isinstance(ratings, list) or len(ratings) != 3
                or any(type(v) is not int or not 1 <= v <= 5 for v in ratings)):
            raise ValueError("Ungültige Bewertung")
        # Nur für das Dashboard benötigte Kennzahlen speichern; keine Freitexte oder Gerätekennungen.
        safe.append({"interface": r["interface"], "duration": round(float(duration), 2),
                     "errors": errors, "tasks": [{"task": t["task"], "seconds": round(float(t["seconds"]), 2), "success": True} for t in tasks],
                     "ratings": ratings, "targetRpm": target})
    return safe


def save_result(pid, order, runs):
    # Upsert wiederholbarer Übertragungen nach einem Netzwerkfehler, geschützt durch participant_id.
    # Aufrufe erfolgen ausschließlich über die Serverseite der laufenden Streamlit-Sitzung.
    supabase("POST", "hmi_results", params={"on_conflict": "participant_id"},
             payload={"participant_id": pid, "test_order": order, "runs": runs})


def get_data():
    # In diesem Seminar nur wenige Personen; Pagination für eine spätere Nutzung ergänzen.
    participants = supabase("GET", "hmi_participants", params={"select": "id,number,created_at", "order": "number.asc", "limit": "1000"})
    results = supabase("GET", "hmi_results", params={"select": "participant_id,test_order,runs,created_at", "limit": "1000"})
    return participants, results


def make_csv(results, participants):
    mapping = {p["id"]: p["number"] for p in participants}
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Teilnehmer", "Reihenfolge", "HMI", "Dauer_s", "Fehlbedienungen", "Aufgaben", "Bewertung_1", "Bewertung_2", "Bewertung_3"])
    for result in results:
        for run in result["runs"]:
            writer.writerow([f'T{mapping.get(result["participant_id"], "?"):02d}', result["test_order"], run["interface"],
                             run["duration"], run["errors"], len(run["tasks"]), *run["ratings"]])
    return ('\ufeff' + output.getvalue()).encode('utf-8')


def admin_page():
    st.title("🔐 HMI-Labor | Admin-Dashboard")
    password = get_secret("ADMIN_PASSWORD")
    if not password:
        st.error("ADMIN_PASSWORD ist noch nicht in Streamlit-Secrets konfiguriert.")
        return
    if not st.session_state.get("admin_authenticated"):
        with st.form("admin_login"):
            typed = st.text_input("Admin-Passwort", type="password")
            sent = st.form_submit_button("Anmelden")
        if sent:
            if hmac.compare_digest(typed.encode(), password.encode()):
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Passwort nicht korrekt.")
        return
    if st.button("Abmelden"):
        st.session_state.admin_authenticated = False
        st.rerun()
    if st.button("🔄 Ergebnisse aktualisieren"):
        st.rerun()
    try:
        participants, results = get_data()
    except Exception as exc:
        st.error(str(exc))
        return
    c1,c2,c3 = st.columns(3)
    c1.metric("Teilnahmen gestartet", len(participants))
    c2.metric("Abgeschlossene Vergleiche", len(results))
    c3.metric("Noch ohne Ergebnis", max(0, len(participants)-len(results)))
    rows=[]
    labels={p["id"]: f'T{int(p["number"]):02d}' for p in participants}
    for res in results:
        for r in res.get("runs", []):
            rows.append({"Person": labels.get(res["participant_id"], "?"), "Reihenfolge": res["test_order"],
                        "HMI": r["interface"], "Zeit (s)": r["duration"], "Fehler": r["errors"],
                        "Bewertung": sum(r["ratings"])/3, "Aufgaben": len(r["tasks"])})
    if rows:
        df=pd.DataFrame(rows)
        summary=df.groupby("HMI")[["Zeit (s)", "Fehler", "Bewertung", "Aufgaben"]].mean().round(2)
        st.subheader("Durchschnittswerte pro HMI")
        st.dataframe(summary, use_container_width=True)
        st.subheader("Bearbeitungszeit")
        st.bar_chart(summary["Zeit (s)"], horizontal=True)
        st.subheader("Fehlbedienungen")
        st.bar_chart(summary["Fehler"], horizontal=True)
        st.subheader("Einzelergebnisse")
        st.dataframe(df.sort_values(["Person", "HMI"]), use_container_width=True, hide_index=True)
        st.download_button("⬇️ CSV-Ergebnisse herunterladen", data=make_csv(results, participants), file_name="hmi_labor_ergebnisse.csv", mime="text/csv")
        st.caption("Didaktischer Versuch mit kleiner Stichprobe; keine kausale Zuordnung einzelner Gestaltungsmerkmale.")
    else:
        st.info("Noch keine vollständigen Durchgänge eingegangen.")
    public_url = get_secret("PUBLIC_URL")
    if public_url.startswith("https://"):
        st.divider()
        st.subheader("QR-Code zur Teilnahme")
        st.code(public_url)
        qr=qrcode.QRCode(box_size=8,border=3)
        qr.add_data(public_url)
        qr.make(fit=True)
        img=qr.make_image(fill_color="black", back_color="white").convert("RGB")
        st.image(img, width=230)
    else:
        st.caption("Für einen QR-Code PUBLIC_URL in Streamlit-Secrets ergänzen.")


def participant_page():
    st.title("⚙️ HMI-Labor")
    st.caption("Mensch–Maschine–Experiment · Produkt- und Industriedesign")
    if st.session_state.get("saved"):
        st.success("Deine Ergebnisse wurden zentral gespeichert. Vielen Dank für die Teilnahme!")
        st.info("Bitte das Experiment nicht noch einmal starten. Die Lehrperson zeigt später die Gesamtauswertung.")
        return
    if "participant_id" not in st.session_state:
        st.write("Du testest zwei Bedienoberflächen einer virtuellen Mischanlage. Deine Bearbeitungszeiten, Fehlbedienungen und drei kurze Bewertungen werden anonym erfasst.")
        st.info("Plane ungefähr 10–12 Minuten ein. Bitte die Browserseite während des Experiments nicht aktualisieren.")
        if st.button("Teilnahme beginnen", type="primary"):
            try:
                pid, order, number = join()
                st.session_state.participant_id = pid
                st.session_state.test_order = order
                st.session_state.participant_number = number
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        return
    st.write(f"**Deine Kennung:** T{st.session_state.participant_number:02d}")
    st.caption("Die beiden Oberflächen werden automatisch in der zugewiesenen Reihenfolge getestet.")
    # Das HTML steuert beide Oberflächen und sendet erst am Ende einen einzigen Wert an Python.
    result=hmi(participant_id=st.session_state.participant_id,
               order=st.session_state.test_order, key="hmi_full_experiment", default=None)
    if isinstance(result, dict) and result.get("kind") == "completed":
        try:
            safe=validate_result(result, st.session_state.participant_id, st.session_state.test_order)
            save_result(st.session_state.participant_id, st.session_state.test_order, safe)
            st.session_state.saved=True
            st.rerun()
        except Exception as exc:
            st.error(f"Ergebnis konnte noch nicht gespeichert werden: {exc}")
            st.warning("Bitte die Seite nicht aktualisieren. Du kannst die Übertragung mit dem Button erneut versuchen.")
            if st.button("Ergebnis erneut speichern"):
                st.rerun()


if st.query_params.get("admin") == "1":
    admin_page()
else:
    participant_page()
