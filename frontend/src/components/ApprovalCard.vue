<script setup>
import { computed } from 'vue'

const props = defineProps({
    approval: { type: Object, required: true },
})
const emit = defineEmits(['decide'])

const payload = computed(() => props.approval.payload || {})
const isEmail = computed(() => !!(payload.value.to || payload.value.subject))
const title = computed(() => (isEmail.value ? '📋 待确认操作 · 发送邮件' : '📋 待确认操作'))

const pending = computed(() => props.approval.status === 'pending')

const statusText = computed(() => {
    switch (props.approval.status) {
        case 'sending-confirm': return '已确认，正在执行…'
        case 'sending-cancel': return '已取消，正在通知助手…'
        case 'confirmed': return '✓ 已确认发送'
        case 'cancelled': return '✓ 已取消发送'
        case 'error': return '【错误】' + (props.approval.error || '')
        default: return ''
    }
})
const statusClass = computed(() => {
    const done = props.approval.status === 'confirmed' || props.approval.status === 'cancelled'
    return done ? 'approval-card-status done' : 'approval-card-status'
})

const attachments = computed(() =>
    Array.isArray(payload.value.attachment) ? payload.value.attachment : []
)
</script>

<template>
    <div class="approval-card">
        <div class="approval-card-title">{{ title }}</div>
        <div v-if="payload.to" class="approval-card-row">
            <span class="k">收件人</span><span class="v">{{ payload.to }}</span>
        </div>
        <div v-if="payload.subject" class="approval-card-row">
            <span class="k">主　题</span><span class="v">{{ payload.subject }}</span>
        </div>
        <div v-if="payload.body" class="approval-card-row">
            <span class="k">正　文</span><span class="v">{{ payload.body }}</span>
        </div>
        <div v-if="attachments.length" class="approval-card-row">
            <span class="k">附　件</span><span class="v">{{ attachments.join('、') }}</span>
        </div>

        <div class="approval-card-actions">
            <button class="approval-btn approval-btn-confirm" :disabled="!pending"
                    @click="emit('decide', true)">确认发送</button>
            <button class="approval-btn approval-btn-cancel" :disabled="!pending"
                    @click="emit('decide', false)">取消</button>
        </div>

        <div v-if="statusText" :class="statusClass">{{ statusText }}</div>
    </div>
</template>
