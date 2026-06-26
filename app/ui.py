import uuid
import streamlit as st
import requests
from streamlit_cookies_manager import EncryptedCookieManager

# ---------- Cookie 管理器 ----------
cookies = EncryptedCookieManager(password="your-secret-password")
if not cookies.ready():
    st.stop()

# ---------- 页面配置（只设置一次） ----------
st.set_page_config(page_title="企业智能知识库", layout="wide")

# ---------- 从 Cookie 恢复登录状态 ----------
if "access_token" not in st.session_state:
    saved_token = cookies.get("access_token")
    saved_user = cookies.get("user")
    if saved_token:
        st.session_state.access_token = saved_token
        st.session_state.user = saved_user
    else:
        st.session_state.access_token = None
        st.session_state.user = None

# ---------- 未登录时的登录/注册界面 ----------
if st.session_state.access_token is None:
    st.title("🔐 企业知识库 - 请先登录")
    auth_mode = st.radio("选择操作", ["登录", "注册"], horizontal=True)

    with st.form("auth_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("提交")

        if submitted:
            if auth_mode == "登录":
                resp = requests.post(
                    "http://127.0.0.1:8000/api/auth/login",
                    json={"username": username, "password": password}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    token = data["access_token"]
                    st.session_state.access_token = token
                    st.session_state.user = username
                    cookies["access_token"] = token
                    cookies["user"] = username
                    cookies.save()
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("登录失败：" + resp.json().get("detail", "未知错误"))
            else:
                resp = requests.post(
                    "http://127.0.0.1:8000/api/auth/register",
                    json={"username": username, "password": password}
                )
                if resp.status_code == 200:
                    st.success("注册成功，请切换到登录并登录")
                else:
                    st.error("注册失败：" + resp.json().get("detail", "未知错误"))
    st.stop()

# ---------- 已登录：侧边栏用户信息 + 退出按钮 ----------
st.sidebar.success(f"用户: {st.session_state.user}")
if st.sidebar.button("退出登录"):
    st.session_state.access_token = None
    st.session_state.user = None
    del cookies["access_token"]
    del cookies["user"]
    cookies.save()
    st.rerun()

# ---------- 全局认证头（所有请求都要带） ----------
auth_headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

st.title("📚 企业文档智能问答")

# ===================== 工具函数 =====================
def format_message(text: str) -> str:
    text = text.replace('<br>', '\n').replace('<br/>', '\n').replace('&lt;br&gt;', '\n')
    text = text.replace('\\n', '\n')
    return text

# ===================== 会话管理 =====================
query_params = st.query_params
if "session_id" in query_params:
    session_id = query_params["session_id"]
    if "current_session" not in st.session_state:
        st.session_state.current_session = session_id
else:
    if "current_session" not in st.session_state:
        raw_id = str(uuid.uuid4())[:8]
        default_id = f"{st.session_state.user}_{raw_id}" if st.session_state.user else raw_id
        st.session_state.current_session = default_id
        st.query_params["session_id"] = default_id
    else:
        st.query_params["session_id"] = st.session_state.current_session

current_session = st.session_state.current_session

# 初始化定义一个计数器来记录对话框
if "session_selector_key" not in st.session_state:
    st.session_state.session_selector_key = 0


if "messages" not in st.session_state:
    st.session_state.messages = []

# ===================== 侧边栏 =====================
with st.sidebar:
    st.header("📂 会话管理")

    if st.button("➕ 新建会话", use_container_width=True):
        raw_id = str(uuid.uuid4())[:8]
        new_id = f"{st.session_state.user}_{raw_id}"
        st.session_state.current_session = new_id
        st.session_state.messages = []
        st.query_params["session_id"] = new_id
        st.session_state.session_selector_key += 1  # 关键：改变 key
        st.rerun()

    # ---------- 新增：我的会话列表 ----------
    # 从后端获取当前用户的所有会话
    # ---------- 我的会话列表（修正版）----------
    resp = requests.get(
        "http://127.0.0.1:8000/api/chat/sessions",
        headers=auth_headers
    )
    if resp.status_code == 200:
        user_sessions = resp.json().get("sessions", [])
    else:
        user_sessions = []

    # 构建下拉选项：确保当前会话始终在选项中
    if current_session and current_session not in user_sessions:
        # 当前会话是新创建的，还没有历史，把它加在最前面
        display_sessions = [current_session] + user_sessions
    else:
        display_sessions = user_sessions

    if "delete_confirm" not in st.session_state:
        st.session_state.delete_confirm = False

    if display_sessions:
        st.subheader("💬 我的会话")
        selectbox_options = display_sessions + ["──────────", "🗑️ 删除当前会话"]
        try:
            default_index = display_sessions.index(current_session)
        except ValueError:
            default_index = 0

        selected = st.selectbox(
            "选择一个会话",
            options=selectbox_options,
            index=default_index,
            key=f"session_selector_{st.session_state.session_selector_key}",
            label_visibility="collapsed"
        )

        # 选择了分隔线 → 重置回当前会话
        if selected == "──────────":
            st.session_state.session_selector_key += 1
            st.rerun()

        # 选择了删除 → 弹出确认提示（同时重置 selectbox 防止循环触发）
        if selected == "🗑️ 删除当前会话":
            st.session_state.session_selector_key += 1
            st.session_state.delete_confirm = True
            st.rerun()

        # 正常切换会话
        if selected and selected != current_session and not selected.startswith("─") and selected != "🗑️ 删除当前会话":
            st.session_state.current_session = selected
            st.session_state.messages = []
            st.query_params["session_id"] = selected
            st.rerun()

        # 删除确认弹窗（先确认再执行）
        if st.session_state.delete_confirm:
            st.warning(f"⚠️ 确定要删除此会话吗？")
            st.caption(f"`{current_session}`")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认删除", key="confirm_del", use_container_width=True):
                    requests.delete(
                        f"http://127.0.0.1:8000/api/chat/session/{current_session}",
                        headers=auth_headers
                    )
                    st.session_state.delete_confirm = False
                    raw_id = str(uuid.uuid4())[:8]
                    new_id = f"{st.session_state.user}_{raw_id}"
                    st.session_state.current_session = new_id
                    st.session_state.messages = []
                    st.query_params["session_id"] = new_id
                    st.session_state.session_selector_key += 1
                    st.rerun()
            with c2:
                if st.button("❌ 取消", key="cancel_del", use_container_width=True):
                    st.session_state.delete_confirm = False
                    st.rerun()

        st.caption(":red[下拉到底 → 🗑️ 删除当前会话]")
    else:
        # 如果连当前会话都没有，显示提示
        st.caption("暂无会话，请新建一个")
    st.divider()

    st.caption(f"当前会话ID: `{st.session_state.current_session}`")
    # ... 后面是上传文档等保持不变 ...

# ===================== 加载历史记录 =====================
if not st.session_state.messages:
    with st.spinner("加载历史记录..."):
        resp = requests.get(
            f"http://127.0.0.1:8000/api/chat/history/{current_session}",
            headers=auth_headers
        )
        if resp.status_code == 200:
            st.session_state.messages = resp.json().get("messages", [])

# ===================== 显示历史消息 =====================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        formatted = format_message(msg["content"])
        st.markdown(formatted)

# ===================== 提问与流式回答 =====================
if prompt := st.chat_input("输入你的问题..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("thinking..."):
            resp = requests.post(
                "http://127.0.0.1:8000/api/chat/stream",
                json={"question": prompt, "session_id": current_session},
                headers=auth_headers,
                stream=True
            )
            placeholder = st.empty()
            full_response = ""

            for chunk in resp.iter_lines(decode_unicode=True):
                if chunk:
                    # 跳过 SSE 结束标记
                    if chunk == "data: [DONE]":
                        continue
                    text = chunk[6:] if chunk.startswith("data: ") else chunk
                    full_response += text
                    placeholder.text(full_response)

            formatted = format_message(full_response)
            placeholder.markdown(formatted)

    st.session_state.messages.append({"role": "assistant", "content": full_response})