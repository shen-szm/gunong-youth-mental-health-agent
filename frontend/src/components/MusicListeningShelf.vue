<script setup>
import { computed, ref, onBeforeUnmount, watch } from 'vue'
import { Howl } from 'howler'
import { Play, Pause, SkipForward, Volume2, Music2 } from '@lucide/vue'
const emit = defineEmits(['playing'])
const tracks = [
  { title: '房间旋律 01', detail: '熟悉的房间背景曲', src: '/audio/bgm.mp3' },
  { title: '房间旋律 02', detail: '换一段旋律，停留一会儿', src: '/audio/bgm-song2.mp3' },
  { title: '房间旋律 03', detail: '给这一刻留一点空间', src: '/audio/bgm-song3.mp3' },
]
const current = ref(0), playing = ref(false), loading = ref(false), error = ref(''), duration = ref(0), position = ref(0), volume = ref(35), sleep = ref('0')
let sound, interval, deadline = 0
const track = computed(() => tracks[current.value])
const format = seconds => `${Math.floor((seconds || 0) / 60)}:${String(Math.floor((seconds || 0) % 60)).padStart(2, '0')}`
function pause() { sound?.pause(); playing.value = false }
function play(index = current.value) {
  if (loading.value && index === current.value) return
  if (sound && index === current.value && !error.value) { if (playing.value) pause(); else sound.play(); return }
  sound?.unload(); clearInterval(interval)
  current.value = index; error.value = ''; position.value = 0; duration.value = 0; playing.value = false; loading.value = true
  const player = new Howl({ src: [tracks[index].src], html5: true, preload: false, volume: volume.value / 100,
    onload: () => { if (sound !== player) return; duration.value = player.duration(); loading.value = false },
    onplay: () => { if (sound !== player) return; playing.value = true; loading.value = false; emit('playing') },
    onpause: () => { if (sound === player) playing.value = false },
    onend: () => { if (sound === player) { playing.value = false; position.value = 0 } },
    onloaderror: () => fail(player), onplayerror: () => fail(player),
  })
  sound = player; player.load(); player.play()
  interval = setInterval(() => { if (sound !== player) return; if (playing.value) position.value = Number(player.seek()) || 0; if (deadline && Date.now() >= deadline) { pause(); sleep.value = '0'; deadline = 0 } }, 500)
}
function fail(player) { if (sound !== player) return; playing.value = false; loading.value = false; error.value = '这首暂时无法播放，可以重试或选择另一首。' }
function seek(event) { const value = Math.min(duration.value, Math.max(0, Number(event.target.value))); sound?.seek(value); position.value = value }
watch(volume, value => sound?.volume(value / 100))
watch(sleep, value => { deadline = Number(value) ? Date.now() + Number(value) * 60000 : 0 })
onBeforeUnmount(() => { sound?.unload(); clearInterval(interval) })
defineExpose({ pause })
</script>

<template>
  <section class="listening-shelf" aria-labelledby="listening-title">
    <header><Music2 :size="22" aria-hidden="true" /><div><h3 id="listening-title">先听一首，不必先说明心情</h3><p>三首现有房间曲目可直接播放，关闭面板即停止。</p></div></header>
    <div class="listening-tracks"><button v-for="(item, index) in tracks" :key="item.src" :aria-pressed="current === index" @click="play(index)"><span>0{{ index + 1 }}</span><strong>{{ item.title }}</strong><small>{{ item.detail }}</small><em>{{ current === index && playing ? '正在播放' : '点击收听' }}</em></button></div>
    <div class="listening-player"><button :disabled="loading" :aria-label="playing ? '暂停当前曲目' : '播放当前曲目'" @click="play()"><Pause v-if="playing" :size="20" aria-hidden="true" /><Play v-else :size="20" aria-hidden="true" /></button><div><strong>{{ track.title }}</strong><small role="status">{{ loading ? '正在加载…' : playing ? '正在播放' : '已暂停' }}</small></div><button aria-label="下一首" @click="play((current + 1) % tracks.length)"><SkipForward :size="20" aria-hidden="true" /></button></div>
    <label class="listening-progress"><span class="sr-only">播放进度</span><span>{{ format(position) }}</span><input aria-label="播放进度" type="range" min="0" :max="duration || 1" :value="position" :disabled="!duration" step="1" @input="seek" /><span>{{ format(duration) }}</span></label>
    <div class="listening-settings"><label><Volume2 :size="16" aria-hidden="true" /><span>音量</span><input v-model="volume" aria-label="音量" type="range" min="0" max="100" /></label><label>定时停止<select v-model="sleep"><option value="0">不设定</option><option value="15">15 分钟</option><option value="30">30 分钟</option></select></label></div>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.listening-shelf{padding:20px 0;color:#f4eddf;border-bottom:1px solid #756c60;margin-bottom:20px}.listening-shelf header{display:flex;align-items:center;gap:12px}.listening-shelf h3{margin:0;font-size:20px}.listening-shelf p{color:#d7cbb7;font-size:13px;line-height:1.6}.listening-tracks{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap}.listening-tracks button{flex:1;min-width:145px;display:grid;gap:8px;text-align:left;padding:14px;border:1px solid #82745f;border-radius:10px;background:#302923;color:#f4eddf;cursor:pointer}.listening-tracks button[aria-pressed=true]{border-color:#ead29b;background:#493e2d}.listening-tracks span,.listening-tracks small{color:#d7cbb7;font-size:12px}.listening-tracks em{font-size:11px;color:#efd79c;font-style:normal}.listening-player{display:flex;align-items:center;gap:14px}.listening-player>div{flex:1}.listening-player small{display:block;margin-top:4px;color:#d7cbb7}.listening-player button{display:grid;place-items:center;width:42px;height:42px;border:0;border-radius:50%;background:#ead29b;color:#33291d;cursor:pointer}.listening-progress{display:flex;align-items:center;gap:12px;margin:15px 0;font-size:12px}.listening-progress input{flex:1;min-width:0}.listening-settings{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;font-size:12px}.listening-settings label{display:flex;align-items:center;gap:8px}.listening-settings input{width:100px}.listening-settings select{padding:7px;border-radius:6px;border:1px solid #82745f;background:#302923;color:#f4eddf}.listening-shelf input{accent-color:#ead29b}.listening-shelf :focus-visible{outline:3px solid #ead29b;outline-offset:3px}.listening-shelf button:disabled{opacity:.6;cursor:wait}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
</style>
