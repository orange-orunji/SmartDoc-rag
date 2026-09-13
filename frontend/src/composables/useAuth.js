import { ref } from 'vue'

// 模块级单例状态：所有组件共享同一份登录态（无需 Pinia）
const token = ref(localStorage.getItem('access_token') || '')
const username = ref(localStorage.getItem('user') || '')
const authed = ref(!!token.value)

function setAuth(t, u) {
    token.value = t
    username.value = u
    authed.value = true
    localStorage.setItem('access_token', t)
    localStorage.setItem('user', u)
}

function logout() {
    token.value = ''
    username.value = ''
    authed.value = false
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
}

/** 登录/注册；模式由 mode 指定（'login' | 'register'） */
async function loginOrRegister(mode, user, pass) {
    const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'
    const resp = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, password: pass }),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || '操作失败，请重试')
    if (mode === 'login') {
        setAuth(data.access_token, user)
        return { registered: false }
    }
    return { registered: true }
}

/** 带 token 的请求头（供后续模块使用） */
function authHeaders() {
    return token.value ? { Authorization: 'Bearer ' + token.value } : {}
}

export function useAuth() {
    return { token, username, authed, setAuth, logout, loginOrRegister, authHeaders }
}
