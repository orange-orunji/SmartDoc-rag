import { ref, reactive } from 'vue'
import { useAuth } from './useAuth'

const { authHeaders } = useAuth()

// 消息列表：历史消息 { role, content }；流中的"活消息"额外带 tips/streaming/approval
const messages = ref([])
const isStreaming = ref(false)
const awaitingApproval = ref(false)   // 待审批：锁定输入区

/** 中断帧 → 审批卡片数据模型 */
function toApproval(interrupt) {
    return {
        payload: interrupt.payload || {},
        interruptId: interrupt.interrupt_id,
        // pending | sending-confirm | sending-cancel | confirmed | cancelled | error
        status: 'pending',
        error: '',
    }
}

function clearMessages() {
    messages.value = []
    awaitingApproval.value = false
}

/** 加载指定会话的历史消息（文件历史，展示用） */
async function loadHistory(sessionId) {
    messages.value = []
    awaitingApproval.value = false
    if (!sessionId) return
    try {
        const resp = await fetch('/api/chat/history/' + encodeURIComponent(sessionId), {
            headers: authHeaders(),
        })
        if (!resp.ok) return
        const data = await resp.json()
        // 数据归一化：后端历史接口 role 为 'human'/'assistant'，统一成 'user'/'assistant'
        messages.value = (data.messages || []).map((m) => ({
            ...m,
            role: m.role === 'human' ? 'user' : m.role,
        }))
    } catch (err) {
        console.warn('加载历史失败:', err)
    }
}

/** 消费 SSE 响应流：文本增量写进 live.content，工具提示进 live.tips，中断帧返回给调用方 */
async function consumeStream(resp, live) {
    let interrupt = null
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const handleFrame = (raw) => {
        if (!raw || raw === '[DONE]') return
        let data
        try { data = JSON.parse(raw); } catch { data = raw; }

        // 中断帧（JSON object）：审批中断通知
        if (typeof data === 'object' && data !== null) {
            if (data.type === 'interrupt') interrupt = data
            return
        }
        // 工具调用提示：独立提示条，不并入回答文本
        if (data.startsWith('[调用工具')) {
            live.tips.push(data)
            return
        }
        // 回答文本：逐帧追加（打字机）
        live.content += data
    }

    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed || !trimmed.startsWith('data: ')) continue
            handleFrame(trimmed.slice(6))
        }
    }
    if (buffer.trim().startsWith('data: ')) {
        handleFrame(buffer.trim().slice(6))
    }
    return { interrupt }
}

/** 发送消息：SSE 流式对话；若流尾出现中断帧 → 附上审批卡片并锁定输入 */
async function sendMessage(question, sessionId) {
    if (isStreaming.value || awaitingApproval.value) return

    messages.value.push({ role: 'user', content: question })
    const live = reactive({ role: 'assistant', content: '', tips: [], streaming: true })
    messages.value.push(live)
    isStreaming.value = true

    try {
        const resp = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, session_id: sessionId }),
        })
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}))
            throw new Error(err.detail || '请求失败')
        }
        const { interrupt } = await consumeStream(resp, live)
        if (interrupt) {
            live.approval = toApproval(interrupt)
            awaitingApproval.value = true
        }
    } catch (err) {
        live.content += (live.content ? '\n\n' : '') + '【错误】' + err.message
    } finally {
        live.streaming = false
        isStreaming.value = false
    }
}

/** 提交审批决定：恢复流继续写入同一条消息（支持"再次中断"链式更新卡片） */
async function sendResume(msg, decision, sessionId) {
    if (isStreaming.value || !msg.approval || msg.approval.status !== 'pending') return

    // 重建的占位消息：清掉占位文案，恢复流从干净气泡开始
    if (msg.placeholder) {
        msg.content = ''
        msg.placeholder = false
    }
    msg.approval.status = decision ? 'sending-confirm' : 'sending-cancel'
    isStreaming.value = true
    let again = false

    try {
        const resp = await fetch('/api/chat/resume', {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, decision }),
        })
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}))
            throw new Error(err.detail || '请求失败')
        }
        const { interrupt } = await consumeStream(resp, msg)
        if (interrupt) {
            msg.approval = toApproval(interrupt)   // 再次中断 → 换新卡片
            again = true
        } else {
            msg.approval.status = decision ? 'confirmed' : 'cancelled'
        }
    } catch (err) {
        msg.approval.status = 'error'
        msg.approval.error = err.message
    } finally {
        isStreaming.value = false
        awaitingApproval.value = again
    }
}

/** 查询当前会话是否有待审批中断；有则重建卡片消息（切会话/刷新页面全场景恢复） */
async function checkPendingInterrupt(sessionId) {
    if (!sessionId) return
    try {
        const resp = await fetch('/api/chat/pending/' + encodeURIComponent(sessionId), {
            method: 'POST',
            headers: authHeaders(),
        })
        if (!resp.ok) return
        const data = await resp.json()
        if (!data.interrupt) return

        const msg = reactive({
            role: 'assistant',
            content: '⏳ 等待您的审批确认…',
            tips: [],
            streaming: false,
            placeholder: true,
            approval: toApproval(data.interrupt),
        })
        messages.value.push(msg)
        awaitingApproval.value = true
    } catch (err) {
        console.warn('pending 查询失败:', err)
    }
}

export function useMessages() {
    return {
        messages, isStreaming, awaitingApproval,
        clearMessages, loadHistory, sendMessage, sendResume, checkPendingInterrupt,
    }
}
