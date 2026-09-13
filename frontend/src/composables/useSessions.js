import { ref } from 'vue'
import { useAuth } from './useAuth'
import { useMessages } from './useMessages'

const { username, authHeaders } = useAuth()
const { clearMessages, loadHistory, checkPendingInterrupt } = useMessages()

const sessions = ref([])
const currentSessionId = ref('')

function newSessionSuffix() {
    return crypto.randomUUID
        ? crypto.randomUUID().slice(0, 8)
        : Math.random().toString(36).slice(2, 10)
}

async function loadSessions() {
    try {
        const resp = await fetch('/api/chat/sessions', { headers: authHeaders() })
        if (!resp.ok) return
        const data = await resp.json()
        let list = data.sessions || []
        // 新会话还没有文件时也先显示在列表中
        if (currentSessionId.value && !list.includes(currentSessionId.value)) {
            list.unshift(currentSessionId.value)
        }
        sessions.value = list
    } catch (err) {
        console.warn('加载会话列表失败:', err)
    }
}

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
    const resp = await fetch('/api/chat/session/' + encodeURIComponent(sessionId), {
        method: 'DELETE',
        headers: authHeaders(),
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

/** 重命名会话（后端业务码模式；重命名后旧 thread 记忆断裂为已知设计取舍） */
async function renameSession(sessionId, newName) {
    const resp = await fetch('/api/chat/session/' + encodeURIComponent(sessionId) + '/rename', {
        method: 'PUT',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName }),
    })
    const data = await resp.json().catch(() => ({}))
    if (data.code && data.code !== 200) {
        throw new Error(data.message || '重命名失败')
    }
    if (sessionId === currentSessionId.value) {
        currentSessionId.value = newName.trim()
    }
    await loadSessions()
}

export function useSessions() {
    return { sessions, currentSessionId, loadSessions, createSession, switchSession, deleteSession, renameSession }
}
