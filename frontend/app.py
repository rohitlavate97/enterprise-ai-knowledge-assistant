"""Streamlit frontend for the Enterprise AI Knowledge Assistant."""

import json
import time
from typing import Literal

import httpx
import streamlit as st

# Configure page layout and style
st.set_page_config(
    page_title="Enterprise AI Knowledge Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply visual overrides and glassmorphism styling
st.markdown(
    """
    <style>
    /* Global styles */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(18, 20, 34) 0%, rgb(8, 9, 14) 90%);
        color: #e2e8f0;
    }
    
    /* Title layout */
    .app-header {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        margin-bottom: 2rem;
    }
    .app-header h1 {
        color: #ffffff !important;
        font-family: 'Outfit', 'Inter', sans-serif;
        margin: 0;
        font-weight: 800;
        font-size: 2.5rem;
    }
    .app-header p {
        color: #93c5fd !important;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }

    /* Glassmorphic card layouts */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    /* Metrics headers */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #60a5fa;
        margin-top: 0.5rem;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Badge colors */
    .badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 75%;
        font-weight: 700;
        line-height: 1;
        text-align: center;
        white-space: nowrap;
        vertical-align: baseline;
        border-radius: 9999px;
        color: #fff;
    }
    .badge-success { background-color: #10b981; }
    .badge-warning { background-color: #f59e0b; }
    .badge-danger { background-color: #ef4444; }

    /* Custom sidebar header */
    .sidebar-header {
        font-weight: 700;
        color: #818cf8;
        font-size: 1.2rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# API Configurations
API_URL = "http://localhost:8000/api/v1"

# Initialize Session State
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "headers" not in st.session_state:
    st.session_state.headers = {}


def check_backend_status() -> bool:
    """Check if the backend FastAPI server is reachable."""
    try:
        res = httpx.get("http://localhost:8000/")
        return res.status_code == 200
    except Exception:
        return False


backend_online = check_backend_status()

# Custom Header banner
st.markdown(
    """
    <div class="app-header">
        <h1>Enterprise AI Knowledge Assistant</h1>
        <p>Tenant-Partitioned Document Ingestion, Semantic Retrieval, and AI Reasoning Engine</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar layout
with st.sidebar:
    st.markdown(
        '<div class="sidebar-header">⚙️ System Configuration</div>',
        unsafe_allow_html=True,
    )

    # Server status indicator
    if backend_online:
        st.success("🟢 Backend API: Online")
    else:
        st.error("🔴 Backend API: Offline (Run FastAPI on port 8000)")

    if st.session_state.token and st.session_state.user:
        st.markdown(
            '<div class="sidebar-header">👤 User Information</div>',
            unsafe_allow_html=True,
        )
        user = st.session_state.user
        st.write(f"**Name:** {user['full_name']}")
        st.write(f"**Email:** {user['email']}")
        role_label = user["role"].upper()
        st.markdown(
            f"**Role:** <span class='badge badge-success'>{role_label}</span>",
            unsafe_allow_html=True,
        )

        # Display scopes
        dept_name = (
            "None (Global)"
            if not user.get("department_id")
            else "HR Department"
            if "hr" in user["email"]
            else "Engineering"
        )
        st.write(f"**Department Scope:** {dept_name}")

        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.headers = {}
            st.rerun()


# Login Interface (displayed if not authenticated)
if not st.session_state.token:
    st.info("Please log in to access the secure knowledge base management portal.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Login Credentials")
        email_input = st.text_input("Corporate Email Address")
        password_input = st.text_input("Password", type="password")

        if st.button("Login", type="primary", use_container_width=True):
            if not backend_online:
                st.error(
                    "Cannot connect to backend API server. Please check port 8000."
                )
            elif not email_input or not password_input:
                st.error("Email and password fields are required.")
            else:
                try:
                    # Request OAuth2 JWT Token from API
                    res = httpx.post(
                        f"{API_URL}/auth/login",
                        data={"username": email_input, "password": password_input},
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.headers = {
                            "Authorization": f"Bearer {st.session_state.token}"
                        }

                        # Retrieve profile info
                        profile_res = httpx.get(
                            f"{API_URL}/auth/me",
                            headers=st.session_state.headers,
                        )
                        st.session_state.user = profile_res.json()
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password. Please try again.")
                except Exception as err:
                    st.error(f"Login request failed: {str(err)}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Quick-Fill Presets")
        st.write("Click a preset below to instantly populate credentials:")

        if st.button("HR Staff (User Role)", use_container_width=True):
            st.warning("Click Login to authenticate as hr@enterprise.com")
            email_input = "hr@enterprise.com"
            password_input = "password123"

        if st.button("Engineering Staff (User Role)", use_container_width=True):
            st.warning("Click Login to authenticate as eng@enterprise.com")
            email_input = "eng@enterprise.com"
            password_input = "password123"

        if st.button("Administrator (Admin Role)", use_container_width=True):
            st.warning("Click Login to authenticate as admin@enterprise.com")
            email_input = "admin@enterprise.com"
            password_input = "password123"
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# Main Application Interface (Only reachable when authenticated)
(
    tab_docs,
    tab_search,
    tab_qa,
    tab_research,
    tab_doc_agent,
    tab_coordinator,
    tab_workflows,
    tab_approvals,
) = st.tabs(
    [
        "📁 Knowledge Documents",
        "🔍 Semantic Search",
        "💬 AI RAG Q&A Assistant",
        "🔬 AI Research Agent",
        "📄 AI Document Agent",
        "🤖 Central Coordinator",
        "⚙️ Workflow Engine",
        "✅ Approvals Gate",
    ]
)


# Fetch current departments & teams for dynamic dropdown selection
departments = []
teams = []
try:
    dept_res = httpx.get(f"{API_URL}/departments/", headers=st.session_state.headers)
    if dept_res.status_code == 200:
        departments = dept_res.json()
    team_res = httpx.get(f"{API_URL}/teams/", headers=st.session_state.headers)
    if team_res.status_code == 200:
        teams = team_res.json()
except Exception:
    pass

# TAB 1: Knowledge Documents Management
with tab_docs:
    st.subheader("Knowledge Base Document Manager")

    col_list, col_upload = st.columns([3, 2])

    # 1. List Documents
    with col_list:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Managed Documents")
        try:
            doc_res = httpx.get(
                f"{API_URL}/documents/", headers=st.session_state.headers
            )
            if doc_res.status_code == 200:
                docs = doc_res.json()
                if not docs:
                    st.info("No documents uploaded yet.")
                else:
                    for doc in docs:
                        status_str = doc["status"]
                        if status_str == "completed":
                            badge_cls = "badge-success"
                        elif status_str in {"processing", "pending"}:
                            badge_cls = "badge-warning"
                        else:
                            badge_cls = "badge-danger"

                        # Resolve Department Name
                        dept_id = doc.get("department_id")
                        dept_tag = "Global / Public"
                        if dept_id:
                            matching_dept = next(
                                (d for d in departments if d["id"] == dept_id), None
                            )
                            dept_tag = (
                                matching_dept["name"]
                                if matching_dept
                                else "Department Scoped"
                            )

                        st.markdown(
                            f"""
                            <div style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong>{doc["title"]}</strong><br/>
                                    <small style="color: #94a3b8;">Size: {doc["file_size"]} bytes | Dept: {dept_tag}</small>
                                </div>
                                <div style="display: flex; gap: 15px; align-items: center;">
                                    <span class="badge {badge_cls}">{status_str.upper()}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.button("🗑️ Delete", key=f"del_{doc['id']}"):
                            del_res = httpx.delete(
                                f"{API_URL}/documents/{doc['id']}",
                                headers=st.session_state.headers,
                            )
                            if del_res.status_code == 200:
                                st.success(
                                    f"Deleted document {doc['title']} successfully!"
                                )
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Failed to delete document.")
            else:
                st.error("Failed to fetch documents from API backend.")
        except Exception as err:
            st.error(f"Error fetching documents: {str(err)}")
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Upload Document Form
    with col_upload:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Upload Document")
        uploaded_file = st.file_uploader(
            "Select text, markdown, or PDF file",
            type=["txt", "md", "pdf"],
            help="Document will be parsed, chunked, and indexed automatically in Qdrant.",
        )

        # Scope Selection
        st.write("##### Access Partition Settings")

        user_role = st.session_state.user["role"]

        if user_role == "admin":
            # Admin can upload to any department or team
            dept_opts = {"None (Public)": None}
            for d in departments:
                dept_opts[d["name"]] = d["id"]
            selected_dept_name = st.selectbox(
                "Department Scope Assignment", list(dept_opts.keys())
            )
            selected_dept_id = dept_opts[selected_dept_name]

            team_opts = {"None (All Teams)": None}
            for t in teams:
                # Show only teams of selected department if selected
                if not selected_dept_id or t.get("department_id") == selected_dept_id:
                    team_opts[t["name"]] = t["id"]
            selected_team_name = st.selectbox(
                "Team Scope Assignment", list(team_opts.keys())
            )
            selected_team_id = team_opts[selected_team_name]
        else:
            # Standard users are locked to their own department/team
            st.info("Locked to your current department/team permissions profile.")
            selected_dept_id = st.session_state.user.get("department_id")
            selected_team_id = st.session_state.user.get("team_id")

        if st.button("Start Ingestion", type="primary", use_container_width=True):
            if not uploaded_file:
                st.error("Please upload a file first.")
            else:
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type,
                        )
                    }
                    data = {}
                    if selected_dept_id:
                        data["department_id"] = str(selected_dept_id)
                    if selected_team_id:
                        data["team_id"] = str(selected_team_id)

                    st.info("Uploading file and scheduling background ingestion...")

                    res_upload = httpx.post(
                        f"{API_URL}/documents/upload",
                        files=files,
                        data=data,
                        headers=st.session_state.headers,
                    )

                    if res_upload.status_code == 201:
                        new_doc = res_upload.json()
                        st.success("Document uploaded successfully!")

                        # Real-time Ingestion Polling Loop
                        poll_bar = st.progress(
                            0, text="AI Ingesting: Parsing PDF pages..."
                        )
                        doc_id = new_doc["id"]

                        for i in range(1, 101):
                            time.sleep(0.08)
                            status_check = httpx.get(
                                f"{API_URL}/documents/{doc_id}",
                                headers=st.session_state.headers,
                            )
                            if status_check.status_code == 200:
                                current_status = status_check.json()["status"]
                                if current_status == "completed":
                                    poll_bar.progress(
                                        100,
                                        text="Ingestion Complete: Vector points indexed in Qdrant!",
                                    )
                                    break
                                elif current_status == "processing":
                                    poll_bar.progress(
                                        min(i * 4, 90),
                                        text="AI processing: Stateful Recursive Chunking & Embedding...",
                                    )
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("Ingestion upload failed. Please try again.")
                except Exception as err:
                    st.error(f"Inference Ingestion request failed: {str(err)}")
        st.markdown("</div>", unsafe_allow_html=True)


# TAB 2: Semantic Similarity Search Inspector
with tab_search:
    st.subheader("Semantic Similarity Explorer")
    st.write("Inspect matching vector database points across document chunks.")

    search_query = st.text_input("Enter search keywords/sentence:")

    col_lim, col_th = st.columns(2)
    with col_lim:
        search_limit = st.slider(
            "Result Count Limit", min_value=1, max_value=20, value=5
        )
    with col_th:
        search_threshold = st.slider(
            "Similarity Threshold Score",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
        )

    if st.button("Search Vector DB", type="primary"):
        if not search_query:
            st.error("Please enter a query.")
        else:
            try:
                # Resolve Admin overrides
                params: dict[str, str | int | float | bool | None] = {
                    "query": search_query,
                    "limit": search_limit,
                    "threshold": search_threshold,
                }

                # Standard users are locked to their own department/team (enforced in the backend REST controller)
                if st.session_state.user["role"] == "admin":
                    # Admin can override scopes if needed
                    pass

                res_search = httpx.get(
                    f"{API_URL}/documents/search",
                    params=params,
                    headers=st.session_state.headers,
                )

                if res_search.status_code == 200:
                    results = res_search.json()
                    if not results:
                        st.warning(
                            "No chunks matched the query or similarity threshold limits."
                        )
                    else:
                        st.success(f"Retrieved {len(results)} matching chunks!")
                        for idx, chunk in enumerate(results):
                            st.markdown(
                                f"""
                                <div class="glass-card" style="border-left: 4px solid #3b82f6;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <strong>Chunk Match #{idx + 1}</strong>
                                        <span class="badge badge-success">Score: {chunk["score"]:.4f}</span>
                                    </div>
                                    <div style="background-color: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 0.95rem; line-height: 1.5;">
                                        {chunk["text"]}
                                    </div>
                                    <div style="margin-top: 10px; font-size: 0.85rem; color: #94a3b8;">
                                        Document ID: {chunk["document_id"]}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                else:
                    st.error("Failed to perform search. Check API logs.")
            except Exception as err:
                st.error(f"Search request failed: {str(err)}")


# TAB 3: Interactive RAG Q&A Assistant Playground
with tab_qa:
    st.subheader("Interactive Knowledge Assistant Playground")
    st.write(
        "Engage in multi-turn conversation with the RAG assistant and manage chat sessions."
    )

    # Initialize chat session states
    if "active_chat_session_id" not in st.session_state:
        st.session_state.active_chat_session_id = None

    # Retrieve parameters for RAG retrieval
    col_qlim, col_qth = st.columns(2)
    with col_qlim:
        qa_limit = st.slider(
            "Context chunks limit", min_value=1, max_value=20, value=5, key="qa_lim"
        )
    with col_qth:
        qa_threshold = st.slider(
            "Similarity confidence threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05,
            key="qa_th",
        )

    st.markdown("---")

    col_sessions, col_chat = st.columns([1, 3])

    # 1. Chat Sessions Sidebar
    with col_sessions:
        st.markdown("### 💬 Chat Sessions")
        if st.button("➕ New Chat Session", use_container_width=True, type="primary"):
            try:
                # Create session on API
                new_sess_res = httpx.post(
                    f"{API_URL}/chat/sessions",
                    json={"title": "New Conversation"},
                    headers=st.session_state.headers,
                )
                if new_sess_res.status_code == 201:
                    new_sess = new_sess_res.json()
                    st.session_state.active_chat_session_id = new_sess["id"]
                    st.success("Created new session!")
                    st.rerun()
                else:
                    st.error("Failed to create new chat session.")
            except Exception as err:
                st.error(f"Error creating session: {str(err)}")

        # Fetch recent sessions
        sessions = []
        try:
            sess_res = httpx.get(
                f"{API_URL}/chat/sessions",
                headers=st.session_state.headers,
            )
            if sess_res.status_code == 200:
                sessions = sess_res.json()
        except Exception:
            pass

        if not sessions:
            st.info("No active chat sessions. Click above to start one.")
        else:
            st.markdown(
                "<div style='max-height: 400px; overflow-y: auto;'>",
                unsafe_allow_html=True,
            )
            for s in sessions:
                s_id = s["id"]
                s_title = s["title"]

                # Active session highlighting using simple columns
                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    # Highlight if active
                    btn_label = f"💬 {s_title}"
                    is_active = s_id == st.session_state.active_chat_session_id
                    btn_type: Literal["primary", "secondary"] = (
                        "primary" if is_active else "secondary"
                    )
                    if st.button(
                        btn_label,
                        key=f"sel_{s_id}",
                        use_container_width=True,
                        type=btn_type,
                    ):
                        st.session_state.active_chat_session_id = s_id
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_sess_{s_id}", use_container_width=True):
                        try:
                            del_sess_res = httpx.delete(
                                f"{API_URL}/chat/sessions/{s_id}",
                                headers=st.session_state.headers,
                            )
                            if del_sess_res.status_code == 204:
                                if st.session_state.active_chat_session_id == s_id:
                                    st.session_state.active_chat_session_id = None
                                st.success("Session deleted.")
                                st.rerun()
                        except Exception as err:
                            st.error(f"Delete failed: {str(err)}")
            st.markdown("</div>", unsafe_allow_html=True)

        # 🧠 Long-Term Memory Section
        st.markdown("---")
        with st.expander("🧠 Long-term User Memory"):
            st.write(
                "This memory is automatically compiled and persists across sessions."
            )
            try:
                mem_res = httpx.get(
                    f"{API_URL}/chat/memory", headers=st.session_state.headers
                )
                if mem_res.status_code == 200:
                    mem_data = mem_res.json()["memory_data"]
                    if not mem_data or (
                        not mem_data.get("preferences")
                        and not mem_data.get("extracted_facts")
                    ):
                        st.info("No long-term memory records found yet.")
                    else:
                        if mem_data.get("preferences"):
                            st.write("**Preferences:**")
                            st.json(mem_data["preferences"])
                        if mem_data.get("extracted_facts"):
                            st.write("**Extracted Facts:**")
                            for fact in mem_data["extracted_facts"]:
                                st.write(f"- {fact}")

                        if st.button(
                            "Reset Long-term Memory",
                            use_container_width=True,
                            type="secondary",
                        ):
                            clear_res = httpx.put(
                                f"{API_URL}/chat/memory",
                                json={},
                                headers=st.session_state.headers,
                            )
                            if clear_res.status_code == 200:
                                st.success("Memory cleared!")
                                st.rerun()
            except Exception as err:
                st.error(f"Failed to load memory: {str(err)}")

    # 2. Chat Feed Area
    with col_chat:
        active_id = st.session_state.active_chat_session_id
        if not active_id:
            st.markdown(
                """
                <div class="glass-card" style="text-align: center; padding: 3rem;">
                    <h2>🤖 Welcome to the RAG Chat Assistant</h2>
                    <p style="color: #94a3b8;">Select or create a chat session from the left menu to start discussing your knowledge base documents.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Fetch session detail containing message history
            session_data = None
            try:
                detail_res = httpx.get(
                    f"{API_URL}/chat/sessions/{active_id}",
                    headers=st.session_state.headers,
                )
                if detail_res.status_code == 200:
                    session_data = detail_res.json()
            except Exception as err:
                st.error(f"Could not load conversation history: {str(err)}")

            if session_data:
                # Session Title & Rename input
                sess_title = session_data["title"]
                col_title, col_ren = st.columns([3, 1])
                with col_title:
                    st.write(f"### Chat Topic: **{sess_title}**")
                with col_ren:
                    new_title_input = st.text_input(
                        "Rename Topic",
                        value=sess_title,
                        key="rename_title_input",
                        label_visibility="collapsed",
                    )
                    if new_title_input != sess_title:
                        try:
                            httpx.put(
                                f"{API_URL}/chat/sessions/{active_id}",
                                json={"title": new_title_input},
                                headers=st.session_state.headers,
                            )
                            st.rerun()
                        except Exception:
                            pass

                st.markdown(
                    "<div style='border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 1.5rem;'></div>",
                    unsafe_allow_html=True,
                )

                # Render Message history
                for m in session_data["messages"]:
                    role = m["role"]
                    content = m["content"]

                    with st.chat_message(role):
                        st.markdown(content)

                        # Render citations/sources if assistant message has them
                        citations = m.get("citations")
                        if role == "assistant" and citations:
                            conf = m.get("confidence_score", 0.0) * 100
                            with st.expander(
                                f"📚 Source Citations (Confidence: {conf:.1f}%)"
                            ):
                                for idx, s in enumerate(citations):
                                    st.markdown(
                                        f"""
                                        <div style="background-color: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; border-left: 3px solid #3b82f6; margin-bottom: 8px;">
                                            <span style="font-size: 0.8rem; color: #94a3b8;">Source #{idx + 1} | Score: {s["score"]:.4f}</span>
                                            <p style="font-family: monospace; font-size: 0.85rem; margin: 4px 0 0 0;">{s["text"]}</p>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                # User chat input
                user_query = st.chat_input("Message RAG assistant...")
                if user_query:
                    # 1. Render User Message
                    with st.chat_message("user"):
                        st.markdown(user_query)

                    # 2. Render Assistant Placeholder
                    with st.chat_message("assistant"):
                        answer_placeholder = st.empty()
                        citations_placeholder = st.empty()

                        # 3. Stream Response Chunks from API
                        full_answer = ""
                        citations = []
                        confidence = 0.0

                        try:
                            # Start Streaming Request
                            with httpx.stream(
                                "POST",
                                f"{API_URL}/chat/sessions/{active_id}/stream",
                                json={
                                    "message": user_query,
                                    "limit": qa_limit,
                                    "threshold": qa_threshold,
                                },
                                headers=st.session_state.headers,
                                timeout=60.0,
                            ) as response:
                                if response.status_code != 200:
                                    answer_placeholder.error(
                                        "Error: Could not connect to RAG streaming API."
                                    )
                                else:
                                    for line in response.iter_lines():
                                        if line.startswith("data: "):
                                            event = json.loads(line[6:])
                                            event_type = event.get("type")

                                            if event_type == "metadata":
                                                citations = event.get("citations", [])
                                                confidence = event.get(
                                                    "confidence_score", 0.0
                                                )
                                            elif event_type == "token":
                                                full_answer += event.get("content", "")
                                                answer_placeholder.markdown(
                                                    full_answer + "▌"
                                                )
                                            elif event_type == "done":
                                                break

                            # Final render without cursor
                            answer_placeholder.markdown(full_answer)

                            # Render Citations
                            if citations:
                                conf_pct = confidence * 100
                                with citations_placeholder.expander(
                                    f"📚 Source Citations (Confidence: {conf_pct:.1f}%)"
                                ):
                                    for idx, s in enumerate(citations):
                                        st.markdown(
                                            f"""
                                            <div style="background-color: rgba(255,255,255,0.03); padding: 8px; border-radius: 6px; border-left: 3px solid #3b82f6; margin-bottom: 8px;">
                                                <span style="font-size: 0.8rem; color: #94a3b8;">Source #{idx + 1} | Score: {s["score"]:.4f}</span>
                                                <p style="font-family: monospace; font-size: 0.85rem; margin: 4px 0 0 0;">{s["text"]}</p>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                            # Rerun to synchronize with session history database state
                            st.rerun()

                        except Exception as err:
                            answer_placeholder.error(f"Streaming failed: {str(err)}")

# TAB 4: Specialist Research Agent Workspace
with tab_research:
    st.subheader("🔬 Specialist Research Agent Workspace")
    st.write(
        "Deploy the specialized tool-calling Research Agent to investigate vector "
        "document chunks and synthesize facts."
    )

    research_topic = st.text_input(
        "Describe your research goal (e.g. 'Compare HR increment rules'):",
        key="research_topic_input",
    )

    if st.button("Launch Autonomous Investigation", type="primary"):
        if not research_topic:
            st.error("Please enter a research goal first.")
        else:
            try:
                # We show status steps to mock step-by-step thinking for a premium user experience
                status_box = st.status("🚀 Launching Research Agent...")

                with status_box:
                    st.write("🔍 Activating tools and analyzing constraints...")
                    time.sleep(0.5)
                    st.write(
                        "📖 Invoking `search_knowledge_base` to retrieve relevant document points..."
                    )
                    time.sleep(0.6)
                    st.write(
                        "🌐 Invoking `search_web` to collect industry standards and references..."
                    )
                    time.sleep(0.5)
                    st.write(
                        "💡 Running synthesis and compiling markdown detailed findings..."
                    )

                    # Make post request to agent endpoint
                    res_agent = httpx.post(
                        f"{API_URL}/agents/research",
                        json={"query": research_topic},
                        headers=st.session_state.headers,
                        timeout=60.0,
                    )

                if res_agent.status_code == 200:
                    status_box.update(
                        label="✅ Investigation Completed Successfully!",
                        state="complete",
                    )
                    data = res_agent.json()

                    st.write("### Research Results Summary")
                    st.markdown(
                        f"""
                        <div class="glass-card" style="border-left: 4px solid #818cf8;">
                            <div style="font-size: 1.1rem; line-height: 1.6; color: #f1f5f9; font-weight: 500;">
                                {data["summary"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        conf = data["confidence_score"] * 100
                        st.metric("Self-Assessed Confidence rating", f"{conf:.1f}%")
                    with col_m2:
                        st.write("**Citations Count:**")
                        cited_cnt = len(data.get("sources_cited", []))
                        st.info(f"{cited_cnt} Source points referenced.")

                    st.write("### Detailed Findings")
                    st.markdown(data["detailed_findings"])

                    if data.get("sources_cited"):
                        st.write("### Cited Source ID References")
                        for src in data["sources_cited"]:
                            st.code(src, language="text")
                else:
                    status_box.update(label="❌ Investigation Failed", state="error")
                    st.error(
                        f"Agent failed to execute. Status code: {res_agent.status_code}"
                    )
            except Exception as err:
                status_box.update(label="❌ Connection Error", state="error")
                st.error(f"Request failed: {str(err)}")


# TAB 5: Specialist Document Agent Workspace
with tab_doc_agent:
    st.subheader("📄 Specialist Document Agent Workspace")
    st.write(
        "Deploy the specialized tool-calling Document Agent to query metadata, "
        "inspect ingestion status, and manage the lifecycle of corporate documents."
    )

    st.write("### Preset Suggestion Queries")

    preset_query = None
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📋 List Documents", key="btn_list_docs"):
            preset_query = "List all my documents"
    with col2:
        if st.button("🔍 Check Ingestion Status", key="btn_status_docs"):
            preset_query = "What is the status of 'HR Guidelines.txt'?"
    with col3:
        if st.button("ℹ️ Get Document Info", key="btn_info_docs"):
            preset_query = "Show details for 'HR Guidelines.txt'"
    with col4:
        if st.button("❌ Request Deletion", key="btn_del_docs"):
            preset_query = "Delete document 'ENG Spec.txt'"

    if preset_query:
        st.session_state.doc_agent_query = preset_query
        st.rerun()

    doc_query = st.text_input(
        "Describe your query or command (e.g. 'List my documents'):",
        value=st.session_state.get("doc_agent_query", ""),
        key="doc_agent_query_input",
    )
    st.session_state.doc_agent_query = doc_query

    if st.button("Deploy Document Agent", type="primary", key="btn_deploy_doc_agent"):
        if not doc_query:
            st.error("Please enter a query or select a preset first.")
        else:
            try:
                # We show status steps to mock step-by-step thinking for a premium user experience
                status_box = st.status("🚀 Deploying Document Agent...")

                with status_box:
                    st.write("🔒 Resolving user role and department permissions...")
                    time.sleep(0.5)
                    st.write("📂 Invoking tools to inspect repository databases...")
                    time.sleep(0.6)
                    st.write("⚙️ Formatting structured response...")
                    time.sleep(0.4)

                    # Make post request to agent endpoint
                    res_agent = httpx.post(
                        f"{API_URL}/agents/document",
                        json={"query": doc_query},
                        headers=st.session_state.headers,
                        timeout=60.0,
                    )

                if res_agent.status_code == 200:
                    status_box.update(
                        label="✅ Document Agent Operation Completed!",
                        state="complete",
                    )
                    data = res_agent.json()

                    st.write("### Operation Summary")
                    st.markdown(
                        f"""
                        <div class="glass-card" style="border-left: 4px solid #10b981;">
                            <div style="font-size: 1.1rem; line-height: 1.6; color: #f1f5f9; font-weight: 500;">
                                {data["response_summary"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        status_color = (
                            "#10b981"
                            if data["operation_status"] == "success"
                            else "#f59e0b"
                        )
                        st.markdown(
                            f"""
                            <div style="padding: 10px; border-radius: 8px; background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);">
                                <strong>Operation Status:</strong> 
                                <span style="color: {status_color}; font-weight: bold; text-transform: uppercase;">
                                    {data["operation_status"]}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col_m2:
                        referenced_cnt = len(data.get("documents_referenced", []))
                        st.metric("Referenced Documents", f"{referenced_cnt}")

                    st.write("### Detailed Information")
                    st.markdown(data["document_details"])

                    if data.get("documents_referenced"):
                        st.write("### Referenced Document IDs")
                        for ref in data["documents_referenced"]:
                            st.code(ref, language="text")
                else:
                    status_box.update(label="❌ Operation Failed", state="error")
                    st.error(
                        f"Agent failed to execute. Status code: {res_agent.status_code}"
                    )
            except Exception as err:
                status_box.update(label="❌ Connection Error", state="error")
                st.error(f"Request failed: {str(err)}")


# TAB 6: Multi-Agent Coordinator Workspace
with tab_coordinator:
    st.subheader("🤖 Central Multi-Agent Coordinator Workspace")
    st.write(
        "Deploy the central Coordinator Agent powered by LangGraph. "
        "The Coordinator dynamically analyzes your request, routes it to the "
        "most suitable specialist agent (Research or Document Agent), and "
        "synthesizes a final, unified response."
    )

    st.write("### Preset Routing Queries")

    preset_coord_query = None
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        if st.button("🔬 Research: wellness benefits", key="btn_coord_res"):
            preset_coord_query = (
                "Compare wellness program benefits against standard guidelines"
            )
    with col_c2:
        if st.button("📄 Document: list files", key="btn_coord_doc"):
            preset_coord_query = "List all my uploaded files"
    with col_c3:
        if st.button("💬 Chat: general hello", key="btn_coord_dir"):
            preset_coord_query = "Hello Coordinator! Tell me what you can do."

    if preset_coord_query:
        st.session_state.coord_agent_query = preset_coord_query
        st.rerun()

    coord_query = st.text_input(
        "Enter your query or command for the coordinator:",
        value=st.session_state.get("coord_agent_query", ""),
        key="coord_agent_query_input",
    )
    st.session_state.coord_agent_query = coord_query

    if st.button(
        "Deploy Central Coordinator",
        type="primary",
        key="btn_deploy_coordinator",
    ):
        if not coord_query:
            st.error("Please enter a query or select a preset first.")
        else:
            try:
                # We show status steps to show dynamic routing feedback
                status_box = st.status("🤖 Deploying Coordinator Agent...")

                with status_box:
                    st.write("🧠 Contacting Central Coordinator...")
                    time.sleep(0.4)
                    st.write(
                        "🔀 Running LLM routing logic to determine target specialist..."
                    )
                    time.sleep(0.5)
                    st.write(
                        "📡 Delegating to specialist node and compiling findings..."
                    )
                    time.sleep(0.6)

                    # Make post request to agent endpoint
                    res_agent = httpx.post(
                        f"{API_URL}/agents/coordinator",
                        json={"query": coord_query},
                        headers=st.session_state.headers,
                        timeout=60.0,
                    )

                if res_agent.status_code == 200:
                    status_box.update(
                        label="✅ Coordinator Routing and Execution Successful!",
                        state="complete",
                    )
                    data = res_agent.json()

                    st.write("### Routing Result")
                    agent_badge = (
                        "🔬 Research Agent"
                        if data["selected_agent"] == "research"
                        else (
                            "📄 Document Agent"
                            if data["selected_agent"] == "document"
                            else "💬 Direct (Coordinator)"
                        )
                    )

                    st.markdown(
                        f"""
                        <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 20px;">
                            <div style="padding: 10px 20px; border-radius: 8px; background-color: rgba(129, 140, 248, 0.15); border: 1px solid rgba(129, 140, 248, 0.3);">
                                <strong>Selected Node:</strong> <span style="color: #818cf8; font-weight: bold;">{agent_badge}</span>
                            </div>
                            <div style="font-style: italic; color: #94a3b8; font-size: 0.95rem;">
                                &ldquo;{data["routing_reason"]}&rdquo;
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.write("### Unified Answer Summary")
                    st.markdown(
                        f"""
                        <div class="glass-card" style="border-left: 4px solid #818cf8;">
                            <div style="font-size: 1.1rem; line-height: 1.6; color: #f1f5f9; font-weight: 500;">
                                {data["summary"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.write("### Detailed Findings")
                    st.markdown(data["detailed_findings"])

                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        conf = data["confidence_score"] * 100
                        st.metric("Overall Confidence", f"{conf:.1f}%")
                    with col_m2:
                        referenced_cnt = len(data.get("documents_referenced", []))
                        st.metric("Cited Documents", f"{referenced_cnt}")

                    if data.get("documents_referenced"):
                        st.write("### Referenced Document IDs / Source points")
                        for ref in data["documents_referenced"]:
                            st.code(ref, language="text")
                else:
                    status_box.update(label="❌ Orchestration Failed", state="error")
                    st.error(
                        f"Coordinator failed to execute. Status code: {res_agent.status_code}"
                    )
            except Exception as err:
                status_box.update(label="❌ Connection Error", state="error")
                st.error(f"Request failed: {str(err)}")


# TAB 7: Workflow Engine
with tab_workflows:
    st.subheader("⚙️ Workflow Engine Management")
    st.write(
        "Design, trigger, and inspect multi-step task execution graphs with custom retries, routing, and scheduling."
    )

    col_wf_list, col_wf_create = st.columns([3, 2])

    # 1. List and Monitor Workflows
    with col_wf_list:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Active Workflows")

        # Keep track of if we need to poll auto-refresh
        should_poll = False

        try:
            wfs_res = httpx.get(
                f"{API_URL}/workflows/", headers=st.session_state.headers
            )
            if wfs_res.status_code == 200:
                workflows = wfs_res.json()
                if not workflows:
                    st.info(
                        "No workflows created yet. Use the creation panel to design one."
                    )
                else:
                    for wf in workflows:
                        wf_id = wf["id"]
                        wf_status = wf["status"]

                        if wf_status == "completed":
                            status_badge = (
                                '<span class="badge badge-success">COMPLETED</span>'
                            )
                        elif wf_status in ["running", "pending"]:
                            status_badge = (
                                '<span class="badge badge-warning">RUNNING</span>'
                            )
                            should_poll = True
                        elif wf_status == "failed":
                            status_badge = (
                                '<span class="badge badge-danger">FAILED</span>'
                            )
                        else:
                            status_badge = f'<span class="badge badge-secondary">{wf_status.upper()}</span>'

                        # Render workflow card header
                        st.markdown(
                            f"""
                            <div style="padding: 12px; margin-top: 10px; background-color: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong>{wf["name"]}</strong>
                                    {status_badge}
                                </div>
                                <p style="font-size: 0.9rem; color: #94a3b8; margin: 0 0 10px 0;">{wf["description"] or "No description provided."}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Buttons for operations
                        col_run, col_del, col_space = st.columns([1, 1, 3])
                        with col_run:
                            if st.button("🚀 Run", key=f"run_wf_{wf_id}"):
                                try:
                                    run_res = httpx.post(
                                        f"{API_URL}/workflows/{wf_id}/run",
                                        headers=st.session_state.headers,
                                    )
                                    if run_res.status_code == 200:
                                        st.success(
                                            "Workflow execution triggered in background!"
                                        )
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("Failed to run workflow.")
                                except Exception as err:
                                    st.error(f"Error: {str(err)}")
                        with col_del:
                            if st.button("🗑️ Delete", key=f"del_wf_{wf_id}"):
                                try:
                                    del_res = httpx.delete(
                                        f"{API_URL}/workflows/{wf_id}",
                                        headers=st.session_state.headers,
                                    )
                                    if del_res.status_code == 204:
                                        st.success("Workflow deleted.")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete workflow.")
                                except Exception as err:
                                    st.error(f"Error: {str(err)}")

                        # Display tasks in expandable details
                        with st.expander(f"📋 View Tasks ({len(wf['tasks'])} steps)"):
                            tasks = sorted(wf["tasks"], key=lambda t: t["step_number"])
                            for t in tasks:
                                t_status = t["status"]
                                if t_status == "completed":
                                    t_badge = '<span class="badge badge-success">COMPLETED</span>'
                                elif t_status in ["running", "pending", "retrying"]:
                                    t_badge = '<span class="badge badge-warning">RUNNING</span>'
                                elif t_status == "failed":
                                    t_badge = (
                                        '<span class="badge badge-danger">FAILED</span>'
                                    )
                                else:
                                    t_badge = f'<span class="badge badge-secondary">{t_status.upper()}</span>'

                                st.markdown(
                                    f"""
                                    <div style="padding: 10px; margin-bottom: 8px; background-color: rgba(0,0,0,0.15); border-radius: 6px; font-size: 0.9rem;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                                            <strong>Step {t["step_number"]}: {t["name"]}</strong>
                                            {t_badge}
                                        </div>
                                        <div style="font-size: 0.8rem; color: #94a3b8;">
                                            Type: <code>{t["task_type"]}</code> | Retries: {t["retry_count"]}/{t["max_retries"]}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                                # Show outputs if completed or failed
                                if t.get("output_data"):
                                    st.write("**Output Data:**")
                                    st.json(t["output_data"])
                                if t.get("input_data"):
                                    st.write("**Input Parameters:**")
                                    st.json(t["input_data"])
                                if t.get("conditional_routes"):
                                    st.write("**Conditional Routing Matrix:**")
                                    st.json(t["conditional_routes"])
            else:
                st.error("Failed to fetch workflows from API.")
        except Exception as err:
            st.error(f"Error fetching workflows: {str(err)}")

        st.markdown("</div>", unsafe_allow_html=True)

        # Trigger near-real-time auto-refresh if there is a running workflow
        if should_poll:
            st.info(
                "🔄 Running executing task loops in background... Auto-refreshing in 2 seconds."
            )
            time.sleep(2.0)
            st.rerun()

    # 2. Create Workflow Panel
    with col_wf_create:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write("### Design New Workflow")

        wf_name = st.text_input(
            "Workflow Name", placeholder="e.g. Wellness Compliance Evaluation"
        )
        wf_desc = st.text_area(
            "Description",
            placeholder="e.g. Conducts research on wellness policies and inspects uploaded metadata.",
        )

        st.markdown("---")
        st.write("#### Configure Steps")
        num_steps = st.slider(
            "Number of steps in execution graph", min_value=1, max_value=4, value=2
        )

        wf_tasks = []
        for i in range(1, num_steps + 1):
            with st.container():
                st.markdown(f"##### 📍 Step {i} Configuration")
                t_name = st.text_input(
                    f"Step {i} Name", value=f"Action Step {i}", key=f"t_name_{i}"
                )
                t_type = st.selectbox(
                    f"Step {i} Task Type",
                    ["research", "document", "direct", "system"],
                    key=f"t_type_{i}",
                )
                t_query = st.text_area(
                    f"Step {i} Input Query / Prompt",
                    value="Research wellness guidelines.",
                    key=f"t_query_{i}",
                )
                t_retries = st.slider(
                    f"Step {i} Max Retries",
                    min_value=0,
                    max_value=5,
                    value=2,
                    key=f"t_retries_{i}",
                )
                t_delay = st.slider(
                    f"Step {i} Retry Delay (seconds)",
                    min_value=0,
                    max_value=30,
                    value=3,
                    key=f"t_delay_{i}",
                )

                # Dependencies setup
                dep_options = ["None"] + [f"Step {x}" for x in range(1, i)]
                selected_dep = st.selectbox(
                    f"Step {i} Depends On", dep_options, key=f"t_dep_{i}"
                )
                depends_on_step = None
                if selected_dep != "None":
                    # Map Step X to step number X
                    depends_on_step = int(selected_dep.replace("Step ", ""))

                # Conditional routes setup
                st.write("*(Optional) Conditional Branching Routes:*")
                route_opts = ["End Workflow"] + [
                    f"Step {x}" for x in range(1, num_steps + 1) if x != i
                ]
                route_success = st.selectbox(
                    "On Success route to:", route_opts, key=f"t_route_s_{i}"
                )
                route_failure = st.selectbox(
                    "On Failure route to:", route_opts, key=f"t_route_f_{i}"
                )

                cond_routes = {}
                if route_success != "End Workflow":
                    cond_routes["success"] = int(route_success.replace("Step ", ""))
                if route_failure != "End Workflow":
                    cond_routes["failure"] = int(route_failure.replace("Step ", ""))

                # Build task payload
                task_input = {"query": t_query}
                if t_type == "system":
                    task_input = {"message": t_query}

                task_payload = {
                    "name": t_name,
                    "task_type": t_type,
                    "input_data": task_input,
                    "step_number": i,
                    "max_retries": t_retries,
                    "retry_delay": t_delay,
                    "depends_on_task_id": depends_on_step,  # Handled as step number integer for repo mappings
                    "conditional_routes": cond_routes if cond_routes else None,
                }
                wf_tasks.append(task_payload)
                st.markdown(
                    "<hr style='border-top: 1px dashed rgba(255,255,255,0.05);'/>",
                    unsafe_allow_html=True,
                )

        if st.button("Create Workflow", type="primary", use_container_width=True):
            if not wf_name:
                st.error("Workflow name is required.")
            else:
                try:
                    payload = {
                        "name": wf_name,
                        "description": wf_desc if wf_desc else None,
                        "tasks": wf_tasks,
                    }
                    create_res = httpx.post(
                        f"{API_URL}/workflows/",
                        json=payload,
                        headers=st.session_state.headers,
                    )
                    if create_res.status_code == 201:
                        st.success("Workflow successfully created and saved!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Failed to create workflow: {create_res.text}")
                except Exception as err:
                    st.error(f"Creation request failed: {str(err)}")

        st.markdown("</div>", unsafe_allow_html=True)


# TAB 8: Approvals Gate
with tab_approvals:
    st.subheader("✅ Human-in-the-Loop Approvals Gate")
    st.write(
        "Monitor and authorize gated write operations. Sensitive actions requested by specialist agents require human sign-off."
    )

    try:
        # Fetch requests
        app_res = httpx.get(f"{API_URL}/approvals/", headers=st.session_state.headers)
        if app_res.status_code == 200:
            requests = app_res.json()
            if not requests:
                st.info("No approval requests found.")
            else:
                user_role = st.session_state.user["role"]

                for req in requests:
                    req_id = req["id"]
                    req_status = req["status"]
                    action_type = req["action_type"]
                    payload = req["payload"]

                    # Determine status badge
                    if req_status == "approved":
                        badge_html = '<span class="badge badge-success">APPROVED</span>'
                    elif req_status == "rejected":
                        badge_html = '<span class="badge badge-danger">REJECTED</span>'
                    else:
                        badge_html = (
                            '<span class="badge badge-warning">PENDING REVIEW</span>'
                        )

                    # Show request card
                    st.markdown(
                        f"""
                        <div class="glass-card" style="margin-top: 15px; border-left: 4px solid {"#10b981" if req_status == "approved" else "#ef4444" if req_status == "rejected" else "#f59e0b"};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <strong>Request: {action_type.upper()}</strong>
                                {badge_html}
                            </div>
                            <div style="font-size: 0.9rem; color: #94a3b8; margin-bottom: 10px;">
                                <strong>Request ID:</strong> <code>{req_id}</code><br/>
                                <strong>Submitted By:</strong> <code>{req["requested_by_id"]}</code> | <strong>Date:</strong> {req["created_at"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Show payload parameters
                    with st.expander("🔍 View Action Payload"):
                        st.json(payload)

                    # Render review details if already processed
                    if req_status != "pending":
                        st.write("---")
                        st.markdown(
                            f"""
                            **Review Details:**
                            - **Reviewer ID:** `{req["reviewed_by_id"]}`
                            - **Reviewed At:** {req["reviewed_at"]}
                            """
                        )
                        if req.get("comment"):
                            st.write(f"**Reviewer Comment:** {req['comment']}")
                        if req.get("rejection_reason"):
                            st.error(f"**Rejection Reason:** {req['rejection_reason']}")

                    # Render review controls for Admins if pending
                    if req_status == "pending" and user_role == "admin":
                        st.write("---")
                        st.write("##### 🛡️ Admin Decision Portal")

                        comment_input = st.text_input(
                            "Reviewer Comments (Optional)",
                            key=f"comment_{req_id}",
                            placeholder="Provide verification notes or comments...",
                        )

                        col_app, col_rej, col_space = st.columns([1, 1, 3])

                        with col_app:
                            if st.button(
                                "✅ Approve",
                                key=f"btn_approve_{req_id}",
                                type="primary",
                            ):
                                try:
                                    review_payload = {
                                        "status": "approved",
                                        "comment": comment_input
                                        if comment_input
                                        else None,
                                    }
                                    rev_res = httpx.post(
                                        f"{API_URL}/approvals/{req_id}/review",
                                        json=review_payload,
                                        headers=st.session_state.headers,
                                    )
                                    if rev_res.status_code == 200:
                                        st.success(
                                            "Action approved and executed successfully!"
                                        )
                                        time.sleep(0.8)
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Failed to approve request: {rev_res.text}"
                                        )
                                except Exception as err:
                                    st.error(f"Request failed: {str(err)}")

                        with col_rej:
                            # Rejection reason is required
                            reject_reason_input = st.text_input(
                                "Rejection Reason (Required for rejection)",
                                key=f"rej_reason_{req_id}",
                                placeholder="Explain why this request is rejected...",
                            )
                            if st.button("❌ Reject", key=f"btn_reject_{req_id}"):
                                if not reject_reason_input:
                                    st.error("Rejection reason is required to reject.")
                                else:
                                    try:
                                        review_payload = {
                                            "status": "rejected",
                                            "rejection_reason": reject_reason_input,
                                            "comment": comment_input
                                            if comment_input
                                            else None,
                                        }
                                        rev_res = httpx.post(
                                            f"{API_URL}/approvals/{req_id}/review",
                                            json=review_payload,
                                            headers=st.session_state.headers,
                                        )
                                        if rev_res.status_code == 200:
                                            st.success(
                                                "Action rejected and request updated."
                                            )
                                            time.sleep(0.8)
                                            st.rerun()
                                        else:
                                            st.error(
                                                f"Failed to reject request: {rev_res.text}"
                                            )
                                    except Exception as err:
                                        st.error(f"Request failed: {str(err)}")
                    st.markdown(
                        "<hr style='border-top: 1px dashed rgba(255,255,255,0.08);'/>",
                        unsafe_allow_html=True,
                    )
        else:
            st.error(
                f"Failed to load approval requests. Status code: {app_res.status_code}"
            )
    except Exception as err:
        st.error(f"Connection failed: {str(err)}")
