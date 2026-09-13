import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import markdown from 'highlight.js/lib/languages/markdown'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import xml from 'highlight.js/lib/languages/xml'

// 按需注册常用语言（控制打包体积）
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('css', css)
hljs.registerLanguage('java', java)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('python', python)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('xml', xml)

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

/* 代码块渲染：语法高亮 + 语言标签 + 复制按钮（按钮点击由 ChatArea 事件委托处理） */
const renderer = new marked.Renderer()
renderer.code = function (code, infostring) {
    // marked v13+ 传入 ({ text, lang }) 对象；v12 及以前为 (code, infostring) 字符串
    if (typeof code === 'object' && code !== null) {
        infostring = code.lang
        code = code.text
    }
    const lang = (infostring || '').trim().split(/\s+/)[0].toLowerCase()
    let highlighted
    if (lang && hljs.getLanguage(lang)) {
        highlighted = hljs.highlight(code, { language: lang }).value
    } else {
        highlighted = hljs.highlightAuto(code).value
    }
    const label = (lang || 'text').replace(/[^a-z0-9+#.-]/g, '')
    return (
        '<div class="code-block">' +
        `<div class="code-block-head"><span class="code-lang">${label}</span>` +
        '<button class="code-copy-btn" type="button">复制</button></div>' +
        `<pre><code class="hljs">${highlighted}</code></pre>` +
        '</div>'
    )
}

/** Markdown → HTML（breaks:true：LLM 常用单换行分段） */
export function formatContent(text) {
    if (!text) return ''
    return marked.parse(normalizeTables(text), { breaks: true, renderer })
}
