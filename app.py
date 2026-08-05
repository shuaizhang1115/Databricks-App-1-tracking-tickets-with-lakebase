import logging

import streamlit as st

from db import (
    ALLOWED_STATUSES,
    add_message,
    create_ticket,
    get_ticket,
    get_ticket_messages,
    initialize_database,
    list_tickets,
    update_ticket_status,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Lakebase Support Tickets",
    page_icon="🎫",
    layout="wide",
)


def status_label(status: str) -> str:
    return status.replace("_", " ").title()


try:
    initialize_database()
except Exception:
    logger.exception("Lakebase initialization failed")
    st.error(
        "The application could not initialize Lakebase. "
        "Check the App database resource and deployment logs."
    )
    st.stop()


st.title("🎫 Lakebase Support Tickets")
st.caption("All tickets and messages on this page are read from and written to Lakebase.")

try:
    tickets = list_tickets()
except Exception:
    logger.exception("Ticket loading failed")
    st.error("Tickets could not be loaded from Lakebase. Check the App logs.")
    st.stop()

with st.sidebar:
    st.header("Create a ticket")
    with st.form("create_ticket_form", clear_on_submit=True):
        new_title = st.text_input("Title", max_chars=200)
        new_creator = st.text_input("Created by", max_chars=100)
        new_status = st.selectbox(
            "Initial status",
            ALLOWED_STATUSES,
            format_func=status_label,
        )
        create_submitted = st.form_submit_button("Create ticket", type="primary")

    if create_submitted:
        try:
            ticket_id = create_ticket(new_title, new_status, new_creator)
            st.success(f"Ticket #{ticket_id} created.")
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            logger.exception("Ticket creation failed")
            st.error("The ticket could not be created. Check the App logs.")
    
    #summary
    st.header("Current Status")
    status_count = {
        status: sum(1 for ticket in tickets if ticket["status"] == status)
        for status in ALLOWED_STATUSES
    }

    # First row: Total and Open
    total_col, open_col = st.columns(2)
    total_col.metric("Total", len(tickets))
    open_col.metric("Open", status_count["open"])
    
    # Second row: In Progress and Resolved
    progress_col, resolved_col = st.columns(2)
    progress_col.metric("In Progress", status_count["in_progress"])
    resolved_col.metric("Resolved", status_count["resolved"])


st.subheader("All tickets")
if not tickets:
    st.info("No tickets exist yet. Create the first ticket from the sidebar.")
    st.stop()

table_rows = [
    {
        "ID": ticket["ticket_id"],
        "Title": ticket["title"],
        "Status": status_label(ticket["status"]),
        "Created by": ticket["created_by"],
        "Created at": ticket["created_at"],
        "Messages": ticket["message_count"],
    }
    for ticket in tickets
]
st.dataframe(table_rows, use_container_width=True, hide_index=True)

ticket_ids = [int(ticket["ticket_id"]) for ticket in tickets]
ticket_titles = {int(ticket["ticket_id"]): ticket["title"] for ticket in tickets}
selected_ticket_id = st.selectbox(
    "Select a ticket",
    ticket_ids,
    format_func=lambda ticket_id: f"#{ticket_id} — {ticket_titles[ticket_id]}",
)

selected_ticket = get_ticket(selected_ticket_id)
if selected_ticket is None:
    st.warning("The selected ticket no longer exists.")
    st.stop()

detail_column, status_column = st.columns([3, 2])
with detail_column:
    st.subheader(selected_ticket["title"])
    st.write(f"**Created by:** {selected_ticket['created_by']}")
    st.write(f"**Created at:** {selected_ticket['created_at']}")

with status_column:
    with st.form("status_form"):
        current_index = ALLOWED_STATUSES.index(selected_ticket["status"])
        selected_status = st.selectbox(
            "Ticket status",
            ALLOWED_STATUSES,
            index=current_index,
            format_func=status_label,
        )
        status_submitted = st.form_submit_button("Update status")

    if status_submitted:
        try:
            update_ticket_status(selected_ticket_id, selected_status)
            st.success("Status updated.")
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            logger.exception("Status update failed")
            st.error("The status could not be updated. Check the App logs.")

st.divider()
st.subheader("Messages")

try:
    messages = get_ticket_messages(selected_ticket_id)
except Exception:
    logger.exception("Message loading failed")
    st.error("Messages could not be loaded from Lakebase. Check the App logs.")
    messages = []

if messages:
    for message in messages:
        with st.container(border=True):
            st.write(message["message_text"])
            st.caption(f"{message['author']} · {message['created_at']}")
else:
    st.info("This ticket has no messages yet.")

with st.form("add_message_form", clear_on_submit=True):
    message_text = st.text_area("Add a message", max_chars=2000)
    message_author = st.text_input("Author", max_chars=100)
    message_submitted = st.form_submit_button("Add message", type="primary")

if message_submitted:
    try:
        add_message(selected_ticket_id, message_text, message_author)
        st.success("Message added.")
        st.rerun()
    except ValueError as exc:
        st.warning(str(exc))
    except Exception:
        logger.exception("Message creation failed")
        st.error("The message could not be added. Check the App logs.")
