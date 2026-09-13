<script setup>
import { useAuth } from './composables/useAuth'
import LoginView from './views/LoginView.vue'
import ChatView from './views/ChatView.vue'
import ToastHost from './components/ToastHost.vue'

const { authed } = useAuth()
</script>

<template>
    <LoginView v-if="!authed" />
    <ChatView v-else />
    <ToastHost />
</template>
