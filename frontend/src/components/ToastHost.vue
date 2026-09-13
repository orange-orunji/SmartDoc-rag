<script setup>
import { useToast } from '../composables/useToast'

const { toasts } = useToast()
</script>

<template>
    <div class="toast-host">
        <transition-group name="toast">
            <div v-for="t in toasts" :key="t.id" class="toast-item" :class="t.type">{{ t.message }}</div>
        </transition-group>
    </div>
</template>
