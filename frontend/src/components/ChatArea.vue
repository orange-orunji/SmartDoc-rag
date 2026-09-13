<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useSessions } from '../composables/useSessions'
import { useMessages } from '../composables/useMessages'
import { formatContent } from '../utils/format'
import ApprovalCard from './ApprovalCard.vue'

const { currentSessionId, loadSessions, createSession } = useSessions()
const { messages, isStreaming, awaitingApproval, loadHistory, sendMessage, sendResume, checkPendingInterrupt } = useMessages()

const headerTitle = computed(() => currentSessionId.value || '新会话')
const inputLocked = computed(() => isStreaming.value || awaitingApproval.value)

const inputText = ref('')
const inputEl = ref(null)
const messagesEl = ref(null)

function scrollToBottom() {
    nextTick(() => {
        if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    })
}

// 消息增删 / 文本逐帧增长 → 自动滚底（对齐旧版每帧滚动行为）
watch(messages, scrollToBottom, { deep: true })

function autoGrow() {
    const el = inputEl.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 130) + 'px'
}

async function onSend() {
    const q = inputText.value.trim()
    if (!q || inputLocked.value || !currentSessionId.value) return
    inputText.value = ''
    if (inputEl.value) inputEl.value.style.height = 'auto'
    await sendMessage(q, currentSessionId.value)
}

function onKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        onSend()
    }
}

async function onDecide(msg, decision) {
    await sendResume(msg, decision, currentSessionId.value)
}

onMounted(async () => {
    // 首次进入：无当前会话则新建；加载列表与历史；恢复待审批卡片
    if (!currentSessionId.value) createSession()
    await loadSessions()
    await loadHistory(currentSessionId.value)
    await checkPendingInterrupt(currentSessionId.value)
    scrollToBottom()
})
</script>

<template>
    <main class="chat-area">
        <header class="chat-header">
            <div class="chat-header-title">
                <span class="session-title">{{ headerTitle }}</span>
            </div>
            <span class="chat-header-badge">RAG 增强检索</span>
        </header>

        <div class="chat-messages" ref="messagesEl">
            <div v-if="messages.length === 0" class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <p>选择或新建一个会话开始对话</p>
            </div>

            <div v-for="(m, i) in messages" :key="i"
                 class="message" :class="m.role === 'user' ? 'user' : 'assistant'">
                <div class="msg-role">{{ m.role === 'user' ? '你' : '助手' }}</div>
                <div v-for="(t, j) in (m.tips || [])" :key="'tip' + j" class="tool-call-tip">{{ t }}</div>
                <div class="msg-bubble" v-html="formatContent(m.content)"></div>
                <ApprovalCard v-if="m.approval" :approval="m.approval" @decide="onDecide(m, $event)" />
            </div>
        </div>

        <div class="chat-input-area">
            <div class="chat-input-row">
                <textarea ref="inputEl" v-model="inputText" rows="1" :disabled="inputLocked"
                          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
                          @keydown="onKeydown" @input="autoGrow"></textarea>
                <button class="btn-send" :disabled="inputLocked || !inputText.trim()" @click="onSend" title="发送">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                </button>
            </div>
        </div>
    </main>
</template>
