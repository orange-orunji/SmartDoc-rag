<script setup>
import { computed, ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits(['back'])

const { username, shownName, displayName, avatarUrl, bio, updateProfile, uploadAvatar, changePassword } = useAuth()

const initial = computed(() => (shownName.value.charAt(0) || '?').toUpperCase())

// ── 基本资料 ──
const nameInput = ref(displayName.value)
const bioInput = ref(bio.value)
const profileMsg = ref('')
const profileMsgType = ref('success')
const savingProfile = ref(false)

async function onSaveProfile() {
    savingProfile.value = true
    profileMsg.value = ''
    try {
        await updateProfile({ display_name: nameInput.value, bio: bioInput.value })
        profileMsgType.value = 'success'
        profileMsg.value = '资料已保存'
        setTimeout(() => { if (profileMsgType.value === 'success') profileMsg.value = '' }, 2500)
    } catch (err) {
        profileMsgType.value = 'error'
        profileMsg.value = err.message
    } finally {
        savingProfile.value = false
    }
}

// ── 头像上传 ──
const fileInput = ref(null)
const avatarPreview = ref('')     // 本地即时预览（objectURL）
const uploadingAvatar = ref(false)
const avatarMsg = ref('')

const shownAvatar = computed(() => avatarPreview.value || avatarUrl.value)

function pickAvatar() {
    fileInput.value?.click()
}

async function onAvatarChange(e) {
    const file = e.target.files?.[0]
    e.target.value = ''           // 允许重复选择同一文件
    if (!file) return
    uploadingAvatar.value = true
    avatarMsg.value = ''
    try {
        let uploadFile = file
        try {
            uploadFile = await compressImage(file)
        } catch {
            // 浏览器无法解码（如 heic）→ 回退原文件，由后端校验兜底
        }
        avatarPreview.value = URL.createObjectURL(uploadFile)
        await uploadAvatar(uploadFile)
        avatarMsg.value = '头像已更新'
        avatarPreview.value = ''  // 切回服务器 URL（avatarUrl 已更新）
        setTimeout(() => { avatarMsg.value = '' }, 2500)
    } catch (err) {
        avatarMsg.value = err.message
        avatarPreview.value = ''
    } finally {
        uploadingAvatar.value = false
    }
}

/** 前端压缩：统一为 ≤512px 的 JPEG（大图免超限、多格式兼容、省流量存储） */
async function compressImage(file, maxSize = 512, quality = 0.88) {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, maxSize / Math.max(bitmap.width, bitmap.height))
    const w = Math.max(1, Math.round(bitmap.width * scale))
    const h = Math.max(1, Math.round(bitmap.height * scale))
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    canvas.getContext('2d').drawImage(bitmap, 0, 0, w, h)
    bitmap.close?.()
    const blob = await new Promise((resolve, reject) =>
        canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('压缩失败'))), 'image/jpeg', quality)
    )
    return new File([blob], 'avatar.jpg', { type: 'image/jpeg' })
}

// ── 修改密码 ──
const oldPwd = ref('')
const newPwd = ref('')
const newPwd2 = ref('')
const pwdMsg = ref('')
const pwdMsgType = ref('success')
const savingPwd = ref(false)

async function onChangePassword() {
    if (!oldPwd.value || !newPwd.value) {
        pwdMsgType.value = 'error'
        pwdMsg.value = '请填写原密码与新密码'
        return
    }
    if (newPwd.value !== newPwd2.value) {
        pwdMsgType.value = 'error'
        pwdMsg.value = '两次输入的新密码不一致'
        return
    }
    if (newPwd.value.length < 6) {
        pwdMsgType.value = 'error'
        pwdMsg.value = '新密码至少 6 位'
        return
    }
    savingPwd.value = true
    pwdMsg.value = ''
    try {
        await changePassword(oldPwd.value, newPwd.value)
        pwdMsgType.value = 'success'
        pwdMsg.value = '密码修改成功'
        oldPwd.value = newPwd.value = newPwd2.value = ''
    } catch (err) {
        pwdMsgType.value = 'error'
        pwdMsg.value = err.message
    } finally {
        savingPwd.value = false
    }
}
</script>

<template>
    <main class="settings-page">
        <div class="settings-header">
            <button class="btn-back" @click="emit('back')" title="返回聊天">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"/>
                    <polyline points="12 19 5 12 12 5"/>
                </svg>
            </button>
            <h1 class="settings-title">个人设置</h1>
        </div>

        <div class="settings-inner">
            <!-- 头像 -->
            <section class="settings-card">
                <h3>头像</h3>
                <div class="avatar-edit-row">
                    <div class="avatar-preview">
                        <img v-if="shownAvatar" :src="shownAvatar" alt="头像" />
                        <span v-else>{{ initial }}</span>
                    </div>
                    <div class="avatar-edit-info">
                        <button class="btn btn-primary" :disabled="uploadingAvatar" @click="pickAvatar">
                            {{ uploadingAvatar ? '上传中…' : '上传新头像' }}
                        </button>
                        <p class="settings-hint">支持 jpg / png / webp / gif，大图自动压缩至 512px；不超过 5MB</p>
                        <p v-if="avatarMsg" class="settings-msg">{{ avatarMsg }}</p>
                    </div>
                    <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onAvatarChange" />
                </div>
            </section>

            <!-- 基本资料 -->
            <section class="settings-card">
                <h3>基本资料</h3>
                <div class="settings-field">
                    <label>登录账号</label>
                    <input type="text" :value="username" disabled />
                    <p class="settings-hint">登录账号不可修改</p>
                </div>
                <div class="settings-field">
                    <label>昵称（显示名）</label>
                    <input v-model="nameInput" type="text" maxlength="30" placeholder="留空则显示登录名" />
                </div>
                <div class="settings-field">
                    <label>个性签名</label>
                    <textarea v-model="bioInput" rows="2" maxlength="100" placeholder="一句话介绍自己（100 字内）"></textarea>
                </div>
                <div class="settings-actions">
                    <button class="btn btn-primary" :disabled="savingProfile" @click="onSaveProfile">
                        {{ savingProfile ? '保存中…' : '保存资料' }}
                    </button>
                    <span v-if="profileMsg" class="settings-msg" :class="profileMsgType">{{ profileMsg }}</span>
                </div>
            </section>

            <!-- 修改密码 -->
            <section class="settings-card">
                <h3>修改密码</h3>
                <div class="settings-field">
                    <label>原密码</label>
                    <input v-model="oldPwd" type="password" placeholder="请输入当前密码" autocomplete="current-password" />
                </div>
                <div class="settings-field">
                    <label>新密码</label>
                    <input v-model="newPwd" type="password" placeholder="至少 6 位" autocomplete="new-password" />
                </div>
                <div class="settings-field">
                    <label>确认新密码</label>
                    <input v-model="newPwd2" type="password" placeholder="再次输入新密码" autocomplete="new-password" />
                </div>
                <div class="settings-actions">
                    <button class="btn btn-primary" :disabled="savingPwd" @click="onChangePassword">
                        {{ savingPwd ? '提交中…' : '修改密码' }}
                    </button>
                    <span v-if="pwdMsg" class="settings-msg" :class="pwdMsgType">{{ pwdMsg }}</span>
                </div>
            </section>
        </div>
    </main>
</template>
