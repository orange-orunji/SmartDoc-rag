import streamlit as st
import requests
import uuid

st.set_page_config(page_title="企业智能知识库", layout="wide")
st.title("📚 企业文档智能问答")

# ---------- 初始化会话状态 ----------
if "user_sessions" not in st.session_state:
    st.session_state.user_sessions = {}

# 如果没有当前会话，自动创建一个默认会话
if "current_session" not in st.session_state:
    default_id = str(uuid.uuid4())[:8]
    st.session_state.user_sessions[default_id] = []
    st.session_state.current_session = default_id

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📂 会话管理")

    # 新建会话按钮
    if st.button("➕ 新建会话", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        st.session_state.user_sessions[new_id] = []
        st.session_state.current_session = new_id
        st.rerun()  # 刷新页面，让 selectbox 显示新会话

    # 选择已有会话
    session_list = list(st.session_state.user_sessions.keys())
    if session_list:
        # 确保 current_session 在列表中，否则选第一个
        if st.session_state.current_session not in session_list:
            st.session_state.current_session = session_list[0]

        current_idx = session_list.index(st.session_state.current_session)
        selected_session = st.selectbox(
            "当前会话",
            options=session_list,
            index=current_idx,
            key="session_selector"
        )
        # 同步当前会话
        st.session_state.current_session = selected_session
    else:
        st.warning("没有任何会话，请新建一个")
        st.stop()

    current_session = st.session_state.current_session
    st.caption(f"当前会话ID: `{current_session}`")

    # 上传文件
    st.divider()
    st.header("📄 上传文档")
    uploaded_file = st.file_uploader("选择 PDF/TXT/MD 文件", type=["pdf", "txt", "md"])
    if uploaded_file is not None:
        with st.spinner("正在解析并入库..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            resp = requests.post("http://127.0.0.1:8000/api/document/upload", files=files)
            st.success(resp.json().get("data", "上传成功"))

    st.divider()
    st.caption("支持多轮对话，每个会话独立记忆")

# ---------- 主聊天区 ----------
messages = st.session_state.user_sessions[current_session]

# 显示历史消息
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入问题
if prompt := st.chat_input("输入你的问题..."):
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("thinking..."):
            resp = requests.post(
                "http://127.0.0.1:8000/api/chat/stream",
                json={"question": prompt, "session_id": current_session},
                stream=True
            )
            placeholder = st.empty()
            full_response = ""
            for chunk in resp.iter_lines(decode_unicode=True):
                if chunk:
                    text = chunk[6:] if chunk.startswith("data: ") else chunk
                    full_response += text
                    placeholder.markdown(full_response)

    messages.append({"role": "assistant", "content": full_response})