<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'

const stations = ref([])
const start = ref('A1')
const end = ref('B2')
const quote = ref(null)
const quoteErr = ref('')
const issueMsg = ref('')
const issueErr = ref('')
const tickets = ref([])
const showVoided = ref(false)
const verifyCode = ref('')
const verifyOut = ref(null)
const verifyErr = ref('')
const voidFor = ref('')
const voidReason = ref('')
const voidErr = ref('')

const errText = (e) => {
  try { return JSON.parse(e.message).detail || e.message } catch { return e.message }
}
const loadTickets = async () => {
  tickets.value = (await getJSON('/api/tickets' + (showVoided.value ? '?include_voided=true' : ''))).items
}
onMounted(async () => {
  stations.value = (await getJSON('/api/stations')).items
  await loadTickets()
})

const runQuote = async () => {
  quote.value = null; quoteErr.value = ''; issueMsg.value = ''; issueErr.value = ''
  try {
    quote.value = await postJSON('/api/quote', { start: start.value, end: end.value, persist: true })
    if (!quote.value.reachable) quoteErr.value = '不可达，不能签发乘车码'
  } catch (e) { quoteErr.value = errText(e) }
}

const issue = async () => {
  issueMsg.value = ''; issueErr.value = ''
  try {
    const t = await postJSON('/api/tickets', { run_id: quote.value.run_id })
    issueMsg.value = '已签发乘车码 ' + t.code
    quote.value = null // 一张码对应一次成功询价，再签需重新试算
    await loadTickets()
  } catch (e) { issueErr.value = errText(e) }
}

const verify = async () => {
  verifyOut.value = null; verifyErr.value = ''
  if (!verifyCode.value.trim()) { verifyErr.value = '请输入乘车码编码'; return }
  try {
    verifyOut.value = await postJSON('/api/tickets/verify', { code: verifyCode.value.trim() })
  } catch (e) { verifyErr.value = errText(e) }
}

const askVoid = (code) => { voidFor.value = code; voidReason.value = ''; voidErr.value = '' }
const doVoid = async () => {
  voidErr.value = ''
  if (!voidReason.value.trim()) { voidErr.value = '作废原因必填'; return }
  try {
    await postJSON('/api/tickets/' + voidFor.value + '/void', { reason: voidReason.value.trim() })
    voidFor.value = ''
    await loadTickets()
  } catch (e) { voidErr.value = errText(e) }
}
</script>

<template>
  <div class="page"><h1>乘车码</h1>

    <div class="panel">
      <h2>试算签发</h2>
      <p>
        <select v-model="start"><option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }}</option></select>
        →
        <select v-model="end"><option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }}</option></select>
        <button @click="runQuote">试算</button>
      </p>
      <div v-if="quote && quote.reachable">
        <p>站数 {{ quote.hops }} · 票价 <span class="hero-num">¥{{ quote.fare }}</span></p>
        <p class="muted">途经 {{ quote.path.join(' → ') }}</p>
        <button @click="issue">签发乘车码</button>
      </div>
      <p v-if="quoteErr" class="err">{{ quoteErr }}</p>
      <p v-if="issueErr" class="err">{{ issueErr }}</p>
      <p v-if="issueMsg" class="ok">{{ issueMsg }}</p>
    </div>

    <div class="panel">
      <h2>按编码核验</h2>
      <p>
        <input v-model="verifyCode" placeholder="乘车码编码，如 QR-…" @keyup.enter="verify" />
        <button @click="verify">核验</button>
      </p>
      <div v-if="verifyOut">
        <template v-if="verifyOut.valid">
          <p class="ok">有效 · {{ verifyOut.ticket.start }} → {{ verifyOut.ticket.end }} · 站数 {{ verifyOut.ticket.hops }} · 票价 ¥{{ verifyOut.ticket.fare }}</p>
          <p class="muted">途经 {{ verifyOut.ticket.path.join(' → ') }}</p>
        </template>
        <p v-else class="err">无效（已作废）<span v-if="verifyOut.ticket.void_reason"> · 原因：{{ verifyOut.ticket.void_reason }}</span></p>
      </div>
      <p v-if="verifyErr" class="err">{{ verifyErr }}</p>
    </div>

    <div class="panel">
      <h2>乘车码列表</h2>
      <p><label><input type="checkbox" v-model="showVoided" @change="loadTickets" /> 显示已作废</label></p>
      <table v-if="tickets.length">
        <tr><th>编码</th><th>起讫</th><th>途经</th><th>站数</th><th>票价</th><th>状态</th><th></th></tr>
        <tr v-for="t in tickets" :key="t.code">
          <td>{{ t.code }}</td>
          <td>{{ t.start }} → {{ t.end }}</td>
          <td class="muted">{{ t.path.join(' → ') }}</td>
          <td>{{ t.hops }}</td>
          <td>¥{{ t.fare }}</td>
          <td>{{ t.status === 'valid' ? '有效' : '已作废' }}</td>
          <td><button v-if="t.status === 'valid'" @click="askVoid(t.code)">作废</button></td>
        </tr>
      </table>
      <p v-else class="muted">暂无乘车码</p>
      <div v-if="voidFor" class="panel">
        <p>作废 {{ voidFor }}（原因必填）</p>
        <p>
          <input v-model="voidReason" placeholder="作废原因" @keyup.enter="doVoid" />
          <button @click="doVoid">确认作废</button>
          <button @click="voidFor = ''">取消</button>
        </p>
        <p v-if="voidErr" class="err">{{ voidErr }}</p>
      </div>
    </div>
  </div>
</template>
