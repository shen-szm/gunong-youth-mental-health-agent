<script setup>
import { computed } from 'vue'
import { LayoutDashboard, Workflow, Bell, Users, Presentation, ShieldCheck, UserCog, FlaskConical, RefreshCw, Search, X, Download, Check, MessageCircle, Music2, BookOpen, Compass, PawPrint, ChartLine, FileCheck, CircleHelp } from '@lucide/vue'

const props = defineProps({ name: String, size: { type: Number, default: 18 } })
const icons = { today: LayoutDashboard, cases: Workflow, warnings: Bell, students: Users, lesson: Presentation, approvals: ShieldCheck, accounts: UserCog, benchmark: FlaskConical, refresh: RefreshCw, search: Search, close: X, download: Download, check: Check, chat: MessageCircle, music: Music2, daily: BookOpen, window: Compass, pet: PawPrint, trend: ChartLine, report: FileCheck }
const icon = computed(() => icons[props.name] || CircleHelp)
</script>

<template><component :is="icon" :size="size" :stroke-width="1.8" aria-hidden="true" focusable="false" class="ui-icon" /></template>

<style scoped>.ui-icon{flex-shrink:0;vertical-align:middle;display:inline-block}</style>
