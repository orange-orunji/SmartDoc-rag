import { ref } from 'vue'

// 全局轻提示（右下角浮出，自动消失；无需引入 UI 库）
const toasts = ref([])
let seq = 0

export function useToast() {
    function show(message, type = 'info', duration = 3000) {
        const id = ++seq
        toasts.value.push({ id, message, type })
        setTimeout(() => {
            toasts.value = toasts.value.filter((t) => t.id !== id)
        }, duration)
    }
    return { toasts, show }
}
