<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getJSON, postJSON } from '../api'

const stations = ref([])
const tickets = ref([])
const verifyCode = ref('')
const verified = ref(null)
const error = ref('')
const reasons = ref({})
const route = useRoute()

const nameOf = (code) => stations.value.find(s => s.code === code)?.name || code
const pathText = (t) => (t.path || []).map(nameOf).join(' → ')
const setError = (e) => { error.value = e?.message || String(e) }

const load = async () => {
  // 默认列表仅含有效码，作废码不在此出现。
  tickets.value = (await getJSON('/api/tickets')).items
}

const verify = async (code) => {
  const c = (code ?? verifyCode.value ?? '').trim()
  if (!c) return
  error.value = ''
  verified.value = null
  try {
    verified.value = await getJSON(`/api/tickets/${encodeURIComponent(c)}`)
  } catch (e) { setError(e) }
}

const voidTicket = async (t) => {
  const reason = (reasons.value[t.code] || '').trim()
  if (!reason) { error.value = '作废必须填写原因'; return }
  error.value = ''
  try {
    await postJSON(`/api/tickets/${encodeURIComponent(t.code)}/void`, { reason })
    reasons.value[t.code] = ''
    await load()
    // 作废后按编码仍可读原因。
    await verify(t.code)
  } catch (e) { setError(e) }
}

onMounted(async () => {
  stations.value = (await getJSON('/api/stations')).items
  await load()
  if (route.query.code) {
    verifyCode.value = route.query.code
    await verify(route.query.code)
  }
})
</script>
<template>
  <div class="page">
    <h1>乘车码</h1>

    <div class="panel">
      <h2>按编码核验</h2>
      <input v-model="verifyCode" placeholder="QR-XXXXXXXXXXXX" @keyup.enter="verify()" />
      <button @click="verify()">核验</button>
      <div v-if="verified" class="ticket-detail">
        <p><strong>{{ verified.code }}</strong>
          <span :class="verified.status === 'active' ? 'tag-active' : 'tag-void'">
            {{ verified.status === 'active' ? '有效' : '已作废' }}
          </span>
        </p>
        <p>{{ nameOf(verified.start) }} → {{ nameOf(verified.end) }} · {{ verified.hops }} 站 · ¥{{ verified.fare }}</p>
        <p class="muted">途经：{{ pathText(verified) }}</p>
        <p v-if="verified.status === 'void'" class="muted">作废原因：{{ verified.void_reason }}（{{ verified.voided_at }}）</p>
        <template v-if="verified.status === 'active'">
          <input v-model="reasons[verified.code]" placeholder="作废原因（必填）" />
          <button @click="voidTicket(verified)">作废</button>
        </template>
      </div>
    </div>

    <div class="panel">
      <h2>有效乘车码</h2>
      <p v-if="tickets.length === 0" class="muted">暂无有效乘车码，可在「票价试算」试算成功后签发。</p>
      <table v-else>
        <thead><tr><th>编码</th><th>行程</th><th>途经站</th><th>站数</th><th>票价</th><th>作废</th></tr></thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.id"
              :class="verified && verified.code === t.code ? 'row-hot' : ''">
            <td><a href="#" @click.prevent="verify(t.code)">{{ t.code }}</a></td>
            <td>{{ nameOf(t.start) }} → {{ nameOf(t.end) }}</td>
            <td class="muted">{{ pathText(t) }}</td>
            <td>{{ t.hops }}</td>
            <td>¥{{ t.fare }}</td>
            <td>
              <input v-model="reasons[t.code]" placeholder="原因" />
              <button @click="voidTicket(t)">作废</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="error" class="panel" style="border-left:3px solid #e85d04">{{ error }}</p>
  </div>
</template>

<style scoped>
.tag-active { color: #2a9d8f; font-weight: 700; margin-left: .5rem; }
.tag-void { color: #e85d04; font-weight: 700; margin-left: .5rem; }
.ticket-detail { margin-top: .75rem; padding-top: .5rem; border-top: 1px solid #243860; }
.row-hot { outline: 1px solid var(--accent); }
td input { max-width: 9rem; }
</style>
