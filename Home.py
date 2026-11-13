"""KCA Chatbot Portal - Main Entry Point."""
import streamlit as st
from chatbot.bootstrap import ensure_db

st.set_page_config(page_title="KCA Chatbot Portal", page_icon="🎓", layout="wide")

# Ensure DB is ready before anything else
ensure_db()

with st.sidebar:
    st.title("Navigation")
    st.page_link("Home.py", label="Home")
    st.page_link("pages/1_Student_Chat.py", label="💬 Student Chat")
    st.page_link("pages/2_Admin_Dashboard.py", label="🔐 Admin Dashboard")
    st.divider()
    st.caption("KCA University • STU 3101")

st.title("🎓 KCA Artificial Intelligence-Powered Student Support Chatbot")
st.markdown("""
Welcome to the KCA Student Support system.

Use the **sidebar** to navigate:
- **💬 Student Chat**: Ask questions about fees, exams, and registration.
- **🔐 Admin Dashboard**: Manage the knowledge base and view analytics.
""")
st.info("This is a prototype system. Answers are generated from KCA documents.")