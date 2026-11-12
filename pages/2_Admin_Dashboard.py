"""Admin dashboard (FR-24 to FR-39, SDS Fig 7)."""
import streamlit as st
import bcrypt
import sqlite3
import pandas as pd
from datetime import date, datetime
import config
from chatbot.kb_store import add_document, add_from_file, edit_document, retire_document, list_documents
from chatbot.database import get_connection
from chatbot.cache import get_cache

# --- Auth ---
def check_login(username, password):
    with get_connection() as conn:
        row = conn.execute("SELECT admin_id, password_hash, failed_attempts FROM ADMIN_ACCOUNT WHERE username = ?", (username,)).fetchone()
        if not row:
            return None
        
        admin_id, pw_hash, failed = row
        if failed >= config.MAX_FAILED_LOGINS:
            st.error("Account locked due to too many failed attempts.")
            return None
            
        if bcrypt.checkpw(password.encode('utf-8'), pw_hash.encode('utf-8')):
            conn.execute("UPDATE ADMIN_ACCOUNT SET failed_attempts = 0, last_login_at = CURRENT_TIMESTAMP WHERE admin_id = ?", (admin_id,))
            conn.commit()
            return admin_id
        else:
            conn.execute("UPDATE ADMIN_ACCOUNT SET failed_attempts = failed_attempts + 1 WHERE admin_id = ?", (admin_id,))
            conn.commit()
            return None

def change_password(admin_id, current_pw, new_pw):
    with get_connection() as conn:
        row = conn.execute("SELECT password_hash FROM ADMIN_ACCOUNT WHERE admin_id = ?", (admin_id,)).fetchone()
        if not bcrypt.checkpw(current_pw.encode('utf-8'), row[0].encode('utf-8')):
            return False, "Current password is incorrect."
        new_hash = bcrypt.hashpw(new_pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute("UPDATE ADMIN_ACCOUNT SET password_hash = ? WHERE admin_id = ?", (new_hash, admin_id))
        conn.commit()
        return True, "Password updated successfully!"

# Session state
if "admin_id" not in st.session_state:
    st.session_state.admin_id = None
if "form_key" not in st.session_state:
    st.session_state.form_key = 0

# Login Screen
if st.session_state.admin_id is None:
    st.title("🔐 Admin Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")
        
        if submitted:
            aid = check_login(username, password)
            if aid:
                st.session_state.admin_id = aid
                st.session_state.admin_menu = "Documents"
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    st.stop()

# --- Main Dashboard ---
st.sidebar.title("Admin Menu")
menu = st.sidebar.radio("Go to", ["Documents", "Analytics", "Security", "Log Out"], key="admin_menu")
if menu == "Log Out":
    st.session_state.admin_id = None
    st.rerun()

# 1. Documents View
elif menu == "Documents":
    st.title("📚 Knowledge Base Documents")
    
    # Add Document Form (key changes to reset the form after success)
    with st.expander("➕ Add New Document"):
        with st.form(key=f"add_doc_{st.session_state.form_key}"):
            title = st.text_input("Title")
            category = st.text_input("Category (e.g., Fees, Exams)")
            office = st.text_input("Responsible Office")
            source = st.text_input("Source Reference (optional)")
            review = st.date_input("Review Date", value=date.today())
            
            upload = st.file_uploader("Upload file (TXT, PDF, DOCX)", type=["txt", "pdf", "docx"])
            paste = st.text_area("...OR paste text here", height=150)
            
            if st.form_submit_button("Add Document"):
                if not title or not category or not office:
                    st.error("Title, Category, and Office are required.")
                else:
                    try:
                        if upload:
                            import tempfile, os
                            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.name)[1]) as tmp:
                                tmp.write(upload.getbuffer())
                                tmp_path = tmp.name
                            add_from_file(tmp_path, title=title, category=category, responsible_office=office, source_reference=source, review_date=str(review), admin_id=st.session_state.admin_id)
                            os.unlink(tmp_path)
                        elif paste:
                            add_document(title=title, category=category, responsible_office=office, source_reference=source, review_date=str(review), content=paste, admin_id=st.session_state.admin_id)
                        else:
                            st.error("Please upload a file or paste text.")
                            st.stop()
                        
                        get_cache().invalidate()
                        st.success("Document added and indexed successfully!")
                        st.session_state.form_key += 1  # Resets the form fields to empty
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}. (Note: If uploading a PDF, ensure it contains real text and not just scanned images).")

    # List Documents
    docs = list_documents()
    if not docs:
        st.info("No documents in the knowledge base yet.")
    else:
        df = pd.DataFrame(docs)
        st.dataframe(df, use_container_width=True)
        
        # Edit / Retire actions (Filtering out retired docs from the dropdown)
        st.subheader("Manage Document")
        active_docs = [d for d in docs if d["status"] == "active"]
        
        if active_docs:
            doc_id = st.selectbox("Select Document ID", [d["document_id"] for d in active_docs])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Retire Document"):
                    retire_document(doc_id, admin_id=st.session_state.admin_id)
                    get_cache().invalidate()
                    st.success("Document retired.")
                    st.rerun()
            with col2:
                st.caption("Note: Editing document content requires re-upload.")
        else:
            st.info("No active documents to manage.")

# 2. Analytics View
elif menu == "Analytics":
    st.title("📊 Analytics")
    with get_connection() as conn:
        # General stats
        total = conn.execute("SELECT COUNT(*) FROM QUERY_LOG").fetchone()[0]
        answered = conn.execute("SELECT COUNT(*) FROM QUERY_LOG WHERE outcome = 'answered'").fetchone()[0]
        declined = conn.execute("SELECT COUNT(*) FROM QUERY_LOG WHERE outcome = 'declined'").fetchone()[0]
        errors = conn.execute("SELECT COUNT(*) FROM QUERY_LOG WHERE outcome = 'error'").fetchone()[0]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Queries", total)
        col2.metric("Answered", answered)
        col3.metric("Declined", declined)
        col4.metric("Errors", errors)
        
        # Top Topics
        st.subheader("Top 10 Topics")
        topics = conn.execute("SELECT topic_category, COUNT(*) as c FROM QUERY_LOG WHERE topic_category IS NOT NULL GROUP BY topic_category ORDER BY c DESC LIMIT 10").fetchall()
        if topics:
            st.bar_chart(pd.DataFrame(topics, columns=["Topic", "Count"]).set_index("Topic"))
        else:
            st.write("No topic data yet.")

        # Unanswered Questions
        st.subheader("Unanswered (Declined) Questions")
        unans = conn.execute("SELECT timestamp, question_anonymised FROM QUERY_LOG WHERE outcome = 'declined' ORDER BY timestamp DESC LIMIT 50").fetchall()
        if unans:
            st.dataframe(pd.DataFrame(unans, columns=["Date", "Anonymised Question"]), use_container_width=True)
        else:
            st.write("No unanswered questions.")
            
        # Export
        st.subheader("Export Data")
        all_logs = conn.execute("SELECT * FROM QUERY_LOG").fetchall()
        if all_logs:
            df_logs = pd.DataFrame([dict(r) for r in all_logs])
            st.download_button("📥 Download Query Log (CSV)", df_logs.to_csv(index=False).encode('utf-8'), "query_log.csv", "text/csv")

# 3. Security / Password Change View
elif menu == "Security":
    st.title("🔐 Change Password")
    with st.form("pw_form"):
        curr = st.text_input("Current Password", type="password")
        new1 = st.text_input("New Password", type="password")
        new2 = st.text_input("Confirm New Password", type="password")
        if st.form_submit_button("Update Password"):
            if new1 != new2:
                st.error("New passwords do not match.")
            elif len(new1) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, msg = change_password(st.session_state.admin_id, curr, new1)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)