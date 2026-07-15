"""
WhatsApp Notes — review UI.

A lightweight inbox for thoughts you fire off via WhatsApp. Messages are
captured by webhook.py (running in the cloud) and land in the shared database.
This app lets you search, pin, edit, and delete them.

Run locally:
    streamlit run app.py
"""

import os
from datetime import timezone
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st

from models import count_notes, delete_note, init_db, list_notes, update_note

LOCAL_TZ = ZoneInfo(os.environ.get("APP_TIMEZONE", "").strip() or "America/New_York")

st.set_page_config(page_title="WhatsApp Notes", page_icon="🗒️", layout="centered")

init_db()


def check_password() -> bool:
    """Open by default (fine for local use). If APP_PASSWORD is set, gate on it."""
    try:
        secret_pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        secret_pw = ""
    pw = os.environ.get("APP_PASSWORD", "") or secret_pw
    if not pw:
        return True
    if st.session_state.get("authed"):
        return True
    st.title("🔒 WhatsApp Notes")
    entered = st.text_input("Password", type="password")
    if entered and entered == pw:
        st.session_state.authed = True
        return True
    if entered:
        st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()


def fmt(dt):
    """Format a stored (UTC) timestamp in the user's local timezone, cross-platform."""
    if dt.tzinfo is None:  # SQLite returns naive datetimes; they're stored as UTC.
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(LOCAL_TZ)
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%b %d, %Y')} · {hour}:{dt.strftime('%M')} {ampm}"


# --- Header ---------------------------------------------------------------
st.title("🗒️ WhatsApp Notes")
total = count_notes()
st.caption(f"{total} note{'' if total == 1 else 's'} · message your Telegram bot to add more")

# --- Controls -------------------------------------------------------------
c1, c2 = st.columns([3, 1])
with c1:
    search = st.text_input(
        "Search", placeholder="Search notes…", label_visibility="collapsed"
    )
with c2:
    pinned_only = st.toggle("📌 Pinned")

notes = list_notes(search=search.strip(), pinned_only=pinned_only)

if not notes:
    st.info("No matches." if (search or pinned_only) else "No notes yet — send one from Telegram.")

# --- Note list ------------------------------------------------------------
for note in notes:
    edit_key = f"edit_{note.id}"
    confirm_key = f"confirm_del_{note.id}"

    with st.container(border=True):
        # ---- Edit mode ----
        if st.session_state.get(edit_key):
            new_body = st.text_area(
                "Edit", value=note.body, key=f"ta_{note.id}", label_visibility="collapsed"
            )
            b1, b2 = st.columns(2)
            if b1.button("💾 Save", key=f"save_{note.id}", use_container_width=True):
                update_note(note.id, body=new_body)
                st.session_state[edit_key] = False
                st.rerun()
            if b2.button("Cancel", key=f"cancel_{note.id}", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()
            continue

        # ---- Display mode ----
        prefix = "📌 " if note.pinned else ""
        st.markdown(f"{prefix}{note.body}")
        meta = fmt(note.created_at)
        if note.sender_name:
            meta += f" · {note.sender_name}"
        st.caption(meta)

        if st.session_state.get(confirm_key):
            st.warning("Delete this note permanently?")
            d1, d2 = st.columns(2)
            if d1.button("Yes, delete", key=f"delc_{note.id}", type="primary", use_container_width=True):
                delete_note(note.id)
                st.session_state.pop(confirm_key, None)
                st.rerun()
            if d2.button("Cancel", key=f"delx_{note.id}", use_container_width=True):
                st.session_state.pop(confirm_key, None)
                st.rerun()
        else:
            a1, a2, a3 = st.columns(3)
            pin_label = "📌 Unpin" if note.pinned else "📌 Pin"
            if a1.button(pin_label, key=f"pin_{note.id}", use_container_width=True):
                update_note(note.id, pinned=not note.pinned)
                st.rerun()
            if a2.button("✏️ Edit", key=f"editbtn_{note.id}", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()
            if a3.button("🗑️ Delete", key=f"del_{note.id}", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
