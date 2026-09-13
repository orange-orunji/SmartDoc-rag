<script setup>
import { ref } from 'vue'
import Sidebar from '../components/Sidebar.vue'
import ChatArea from '../components/ChatArea.vue'
import SettingsView from './SettingsView.vue'

// 移动端：侧栏抽屉开关（桌面端侧栏常驻，此状态不影响布局）
const sidebarOpen = ref(false)
// 主区域视图：chat（聊天）| settings（个人设置）
const view = ref('chat')

function openSettings() {
    view.value = 'settings'
    sidebarOpen.value = false
}
</script>

<template>
    <div class="app-layout">
        <Sidebar :open="sidebarOpen" @close="sidebarOpen = false" @open-settings="openSettings" />
        <div class="sidebar-mask" :class="{ show: sidebarOpen }" @click="sidebarOpen = false"></div>
        <SettingsView v-if="view === 'settings'" @back="view = 'chat'" />
        <ChatArea v-else @toggle-sidebar="sidebarOpen = !sidebarOpen" />
    </div>
</template>
