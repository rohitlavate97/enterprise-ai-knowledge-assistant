"""Streamlit frontend for the Enterprise AI Knowledge Assistant."""

import json
import time

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
tab_docs, tab_search, tab_qa, tab_research, tab_doc_agent = st.tabs(
    [
        "📁 Knowledge Documents",
        "🔍 Semantic Search",
        "💬 AI RAG Q&A Assistant",
        "🔬 AI Research Agent",
        "📄 AI Document Agent",
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
                    btn_type = "primary" if is_active else "secondary"
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
                status_box = st.status(
                    "🚀 Deploying Document Agent...", key="status_doc_agent"
                )

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
