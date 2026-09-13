<script setup>
import { useAuth } from './composables/useAuth'
import LoginView from './views/LoginView.vue'
import ChatView from './views/ChatView.vue'

const { authed } = useAuth()
</script>

<template>
    <LoginView v-if="!authed" />
    <ChatView v-else />
</template>
