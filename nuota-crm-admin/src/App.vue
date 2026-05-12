<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import Layout from './components/Layout.vue';

const route = useRoute();
const isLogin = computed(() => route.path === '/login');
</script>

<template>
  <router-view v-if="isLogin" />
  <Layout v-else />
</template>

<style>
html, body, #app { height: 100%; margin: 0; }
#app { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; color: #303133; background: #f5f7fa; }
</style>
