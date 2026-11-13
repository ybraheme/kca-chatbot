"""Student Chat Page."""
import streamlit as st
from app import handle_request
from chatbot import chat_db
import config
from chatbot.bootstrap import ensure_db
ensure_db()

# Initialize state
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "history" not in st.session_state:
    st.session_state.history = []

st.title("💬 Student Support Chat")
st.info("**Do not enter personal details.** Answers come from KCA documents; confirm important matters with the office.")

# SIDEBAR: Chat History
with st.sidebar:
    st.title("Chat History")
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_session_id = None
        st.session_state.history = []
        st.rerun()
    
    st.divider()
    sessions = chat_db.get_sessions()
    for sess in sessions:
        col1, col2 = st.columns([0.75, 0.25])
        with col1:
            label = f"**{sess['title']}**" if sess['session_id'] == st.session_state.current_session_id else sess['title']
            if st.button(label, key=sess['session_id'], use_container_width=True):
                st.session_state.current_session_id = sess['session_id']
                st.session_state.history = []
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{sess['session_id']}", help="Delete this chat"):
                chat_db.delete_session(sess['session_id'])
                if st.session_state.current_session_id == sess['session_id']:
                    st.session_state.current_session_id = None
                st.rerun()

# MAIN CHAT AREA
if st.session_state.current_session_id:
    messages = chat_db.get_messages(st.session_state.current_session_id)
    st.session_state.history = [{"q": m["content"], "a": messages[i+1]["content"]} 
                                for i, m in enumerate(messages) 
                                if m["role"] == "user" and i+1 < len(messages) and messages[i+1]["role"] == "assistant"]
    st.session_state.history = st.session_state.history[-config.HISTORY_WINDOW:]
else:
    messages = []

for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("source_title"):
            st.caption(f"📄 Source: *{msg['source_title']}* | Last reviewed: {msg['review_date']}")

if prompt := st.chat_input("Type your question..."):
    if not st.session_state.current_session_id:
        st.session_state.current_session_id = chat_db.create_session(prompt)
    
    chat_db.save_message(st.session_state.current_session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching KCA documents..."):
            response = handle_request(prompt, st.session_state.history)

        st.markdown(response["answer"])
        top_source = None
        if response["sources"]:
            top = response["sources"][0]
            top_source = {"title": top["title"], "review_date": top["review_date"]}
            st.caption(f"📄 Source: *{top['title']}* | Last reviewed: {top['review_date']}")

    chat_db.save_message(
        st.session_state.current_session_id, "assistant", response["answer"],
        source_title=top_source["title"] if top_source else None,
        review_date=top_source["review_date"] if top_source else None
    )
    st.session_state.history.append({"q": prompt, "a": response["answer"]})
    st.session_state.history = st.session_state.history[-config.HISTORY_WINDOW:]
    st.rerun()