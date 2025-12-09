<template>
  <div class="app">
    <h1>Счётчик</h1>
    <p>Значение: <strong>{{ count }}</strong></p>
    <div class="buttons">
      <button @click="decrement" :disabled="loading">-</button>
      <button @click="increment" :disabled="loading">+</button>
      <button @click="reset" :disabled="loading">Сброс</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script>
import axios from 'axios'
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export default {
  data() {
    return {
      count: 0,
      loading: false,
      error: ''
    }
  },
  mounted() {
    this.fetchCount()
  },
  methods: {
    async fetchCount() {
      this.error = ''
      try {
        const r = await axios.get(`${API_BASE}/counter`)
        this.count = r.data.value ?? 0
      } catch (e) {
        this.error = 'Ошибка при получении значения'
        console.error(e)
      }
    },
    async increment() {
      await this.change('increment')
    },
    async decrement() {
      await this.change('decrement')
    },
    async reset() {
      await this.change('reset')
    },
    async change(action) {
      this.loading = true
      this.error = ''
      try {
        const r = await axios.post(`${API_BASE}/counter/${action}`)
        this.count = r.data.value
      } catch (e) {
        this.error = e.response?.data?.error || 'Ошибка сервера'
        console.error(e)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style>
.app { max-width:420px; margin:40px auto; font-family:Arial, sans-serif; text-align:center; }
button { padding:10px 16px; margin:6px; font-size:16px; }
.error { color: #a00; margin-top:12px; }
</style>
