<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getJSON, postJSON } from '../api'
const stations = ref([])
const start = ref('A1')
const end = ref('B2')
const out = ref(null)
const error = ref('')
const issuing = ref(false)
const router = useRouter()
const nameOf = (code) => stations.value.find(s => s.code === code)?.name || code
onMounted(async () => { stations.value = (await getJSON('/api/stations')).items })
const run = async () => {
  error.value = ''
  out.value = await postJSON('/api/quote', { start: start.value, end: end.value, persist: true })
}
const issue = async () => {
  if (!out.value?.run_id) return
  issuing.value = true
  error.value = ''
  try {
    const t = await postJSON('/api/tickets/issue', { run_id: out.value.run_id })
    await router.push({ path: '/tickets', query: { code: t.code } })
  } catch (e) {
    error.value = e.message
  } finally {
    issuing.value = false
  }
}
</script>
<template>
  <div class="page"><h1>最短站数票价</h1>
    <div class="panel">
      <select v-model="start"><option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }}</option></select>
      →
      <select v-model="end"><option v-for="s in stations" :key="s.code" :value="s.code">{{ s.name }}</option></select>
      <button @click="run">试算</button>
    </div>
    <div v-if="out" class="panel">
      <template v-if="out.reachable">
        <p>站数 {{ out.hops }} · 票价 <span class="hero-num">¥{{ out.fare }}</span></p>
        <p class="muted">途经：{{ (out.path || []).map(nameOf).join(' → ') }}</p>
        <button :disabled="issuing || !out.run_id" @click="issue">
          {{ issuing ? '签发中…' : '签发乘车码' }}
        </button>
      </template>
      <p v-else class="muted">不可达，无法签发乘车码</p>
    </div>
    <p v-if="error" class="panel" style="border-left:3px solid #e85d04">签发失败：{{ error }}</p>
  </div>
</template>
