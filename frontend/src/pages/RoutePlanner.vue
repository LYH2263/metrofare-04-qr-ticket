<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
const stations = ref([])
const start = ref('A1')
const end = ref('B2')
const out = ref(null)
onMounted(async () => { stations.value = (await getJSON('/api/stations')).items })
const run = async () => { out.value = await postJSON('/api/quote', { start: start.value, end: end.value, persist: true }) }
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
      <p v-if="out.reachable">站数 {{ out.hops }} · 票价 <span class="hero-num">¥{{ out.fare }}</span></p>
      <p v-if="out.reachable" class="muted">途经 {{ out.path.join(' → ') }}</p>
      <p v-else class="muted">不可达</p>
    </div>
  </div>
</template>
