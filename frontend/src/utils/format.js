import { marked } from 'marked'

/* GFM 表格贪婪吞行：LLM 流式输出常在两块内容间漏空行，marked 会把
   ① 相邻表格合并；② 表格后的无竖线说明文字吞进表格成为一行；③ 列表项后的表格嵌套进 <li>。
   修复：表格状态机——检测到"新表格开始"（表头行 + 下一行分隔行）且前面紧跟内容时补空行；
   表格内出现无竖线行（说明文字/新块）时强制结束表格。（从旧前端移植） */
function normalizeTables(text) {
    const lines = text.split('\n')
    const sepRe = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/
    const headRe = /^\s*\|.*\|/
    const out = []
    let inTable = false
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const next = (lines[i + 1] || '').trim()
        if (!inTable) {
            if (headRe.test(line) && sepRe.test(next)) {
                const prev = out.length ? out[out.length - 1].trim() : ''
                if (prev !== '' && !sepRe.test(prev)) {
                    out.push('')
                }
                inTable = true
            }
        } else {
            if (!line.includes('|')) {
                inTable = false
                out.push('')
            }
        }
        out.push(line)
    }
    return out.join('\n')
}

/** Markdown → HTML（breaks:true：LLM 常用单换行分段） */
export function formatContent(text) {
    if (!text) return ''
    return marked.parse(normalizeTables(text), { breaks: true })
}
