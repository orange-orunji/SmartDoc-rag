<script setup>
import { computed } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useSessions } from '../composables/useSessions'

const { username, logout } = useAuth()
const { sessions, currentSessionId, loadSessions, createSession, switchSession, deleteSession, renameSession } = useSessions()

const initial = computed(() => (username.value.charAt(0) || '?').toUpperCase())

async function onNew() {
    createSession()
    await loadSessions()
}

async function onRename(sessionId) {
    const newName = prompt('请输入新的会话名称：', sessionId)
    if (!newName || !newName.trim() || newName.trim() === sessionId) return
    try {
        await renameSession(sessionId, newName.trim())
    } catch (err) {
        alert(err.message)
    }
}

async function onDelete(sessionId) {
    if (!confirm(`确定要删除会话 "${sessionId}" 吗？`)) return
    try {
        await deleteSession(sessionId)
    } catch (err) {
        alert(err.message)
    }
}
</script>

<template>
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="brand-mini">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                <span>企业知识库</span>
            </div>
            <button class="btn-logout" @click="logout" title="退出登录">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                    <polyline points="16 17 21 12 16 7"/>
                    <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                <span>退出</span>
            </button>
        </div>

        <div class="sidebar-user">
            <div class="avatar">{{ initial }}</div>
            <div class="sidebar-user-info">
                <span class="sidebar-username">{{ username }}</span>
                <span class="sidebar-user-role">普通用户</span>
            </div>
        </div>

        <div class="sidebar-section">
            <button class="btn-new-session" @click="onNew">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                新建会话
            </button>
        </div>

        <div class="sidebar-section-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            我的会话
        </div>
        <div class="session-list">
            <div v-if="sessions.length === 0" class="session-list-hint">暂无会话，点击上方新建</div>
            <div v-for="s in sessions" :key="s"
                 class="session-item" :class="{ active: s === currentSessionId }"
                 @click="switchSession(s)">
                <span class="session-name">{{ s }}</span>
                <button class="btn-icon" @click.stop="onRename(s)" title="重命名">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                </button>
                <button class="btn-icon danger" @click.stop="onDelete(s)" title="删除">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        <line x1="10" y1="11" x2="10" y2="17"/>
                        <line x1="14" y1="11" x2="14" y2="17"/>
                    </svg>
                </button>
            </div>
        </div>

        <div class="upload-area">
            <div class="sidebar-section-label">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                上传文档
            </div>
            <label class="btn-upload" title="界面迁移中：上传功能后续接入">选择文件上传</label>
            <div class="upload-status"></div>
        </div>
    </aside>
</template>
