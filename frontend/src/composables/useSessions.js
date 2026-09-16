import { computed, ref } from 'vue'
import { useAuth } from './useAuth'
import { useMessages } from './useMessages'

const { username, apiFetch } = useAuth()
const { clearMessages, loadHistory, checkPendingInterrupt } = useMessages()

const sessions = ref([])
const sessionMeta = ref({})          // 会话名 → 最后更新时间（"YYYY-MM-DD HH:MM"，来自后端 mtime）
const titles = ref({})               // 会话 ID → 显示标题（自动生成 / 手动重命名）
const currentSessionId = ref('')
const searchText = ref('')           // 会话搜索关键词

// ── 置顶（localStorage 按用户隔离） ──
const pinnedIds = ref([])

function pinKey() {
    return `pinned_sessions_${username.value || 'u'}`
}

function loadPinned() {
    try {
        pinnedIds.value = JSON.parse(localStorage.getItem(pinKey()) || '[]')
    } catch {
        pinnedIds.value = []
    }
}

function togglePin(sessionId) {
    const set = new Set(pinnedIds.value)
    if (set.has(sessionId)) set.delete(sessionId)
    else set.add(sessionId)
    pinnedIds.value = [...set]
    localStorage.setItem(pinKey(), JSON.stringify(pinnedIds.value))
}

function isPinned(sessionId) {
    return pinnedIds.value.includes(sessionId)
}

function newSessionSuffix() {
    return crypto.randomUUID
        ? crypto.randomUUID().slice(0, 8)
        : Math.random().toString(36).slice(2, 10)
}

function nowStr() {
    const d = new Date()
    const p = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadSessions() {
    loadPinned()
    try {
        const resp = await apiFetch('/api/chat/sessions')
        if (!resp.ok) return
        const data = await resp.json()
        let list = data.sessions || []
        const meta = data.session_meta || {}
        const titleMap = data.titles || {}
        // 新会话还没有文件时也先显示在列表中（归入"今天"）
        if (currentSessionId.value && !list.includes(currentSessionId.value)) {
            list.unshift(currentSessionId.value)
            if (!meta[currentSessionId.value]) meta[currentSessionId.value] = nowStr()
        }
        sessions.value = list
        sessionMeta.value = meta
        titles.value = titleMap
    } catch (err) {
        console.warn('加载会话列表失败:', err)
    }
}

/** 会话显示标题：自动生成 / 手动重命名优先，回退 session_id */
function titleOf(sessionId) {
    return titles.value[sessionId] || sessionId
}

// ── 时间分组：今天 / 近 7 天 / 更早 ──
function timeGroup(sessionId) {
    const t = sessionMeta.value[sessionId]
    if (!t) return '更早'
    const d = new Date(t.replace(' ', 'T'))
    const now = new Date()
    const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const start7 = new Date(startToday)
    start7.setDate(start7.getDate() - 6)
    if (d >= startToday) return '今天'
    if (d >= start7) return '近 7 天'
    return '更早'
}

/** 分组列表：[{ label, items: [sessionId, ...] }]；搜索时平铺为单组 */
const sessionGroups = computed(() => {
    const q = searchText.value.trim().toLowerCase()
    let list = sessions.value
    if (q) {
        list = list.filter((s) =>
            s.toLowerCase().includes(q) || (titles.value[s] || '').toLowerCase().includes(q)
        )
    }

    // 按最后更新时间倒序
    const sorted = [...list].sort((a, b) =>
        (sessionMeta.value[b] || '').localeCompare(sessionMeta.value[a] || '')
    )
    if (q) return [{ label: '', items: sorted }]

    const pinned = sorted.filter((s) => isPinned(s))
    const rest = sorted.filter((s) => !isPinned(s))
    const buckets = { '今天': [], '近 7 天': [], '更早': [] }
    for (const s of rest) buckets[timeGroup(s)].push(s)

    const out = []
    if (pinned.length) out.push({ label: '置顶', items: pinned })
    for (const label of ['今天', '近 7 天', '更早']) {
        if (buckets[label].length) out.push({ label, items: buckets[label] })
    }
    return out
})

/** 新建会话（生成新 sessionId，清空消息区） */
function createSession() {
    currentSessionId.value = username.value + '_' + newSessionSuffix()
    clearMessages()
    return currentSessionId.value
}

/** 切换会话：加载该会话的历史消息，并恢复待审批卡片 */
async function switchSession(sessionId) {
    if (sessionId === currentSessionId.value) return
    currentSessionId.value = sessionId
    await loadHistory(sessionId)
    await checkPendingInterrupt(sessionId)
}

/** 删除会话（后端业务码模式：HTTP 200 + code 字段） */
async function deleteSession(sessionId) {
    const resp = await apiFetch('/api/chat/session/' + encodeURIComponent(sessionId), {
        method: 'DELETE',
    })
    const data = await resp.json().catch(() => ({}))
    if (data.code && data.code !== 200) {
        throw new Error(data.message || '删除失败')
    }
    if (sessionId === currentSessionId.value) {
        createSession()
    }
    await loadSessions()
}

/** 重命名会话标题（后端仅改显示标题，session_id 与记忆不受影响） */
async function renameSession(sessionId, newName) {
    const resp = await apiFetch('/api/chat/session/' + encodeURIComponent(sessionId) + '/rename', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
    })
    const data = await resp.json().catch(() => ({}))
    if (data.code && data.code !== 200) {
        throw new Error(data.message || '重命名失败')
    }
    await loadSessions()
}

export function useSessions() {
    return {
        sessions, sessionMeta, titles, titleOf, searchText, sessionGroups, currentSessionId,
        loadSessions, createSession, switchSession, deleteSession, renameSession,
        togglePin, isPinned,
    }
}
