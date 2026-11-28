<template>
  <Teleport to="body">
    <div class="ap-overlay" @click.self="$emit('close')">
      <div class="ap-panel" role="dialog" aria-modal="true" aria-label="更换头像">
        <div class="ap-head">
          <h3>更换头像</h3>
          <button type="button" class="ap-close" aria-label="关闭" @click="$emit('close')">×</button>
        </div>

        <div class="ap-preview">
          <img v-if="preview" :src="preview" alt="当前头像" />
          <span v-else>{{ initial }}</span>
        </div>

        <p class="ap-label">预设头像</p>
        <div class="ap-grid">
          <button
            v-for="item in PRESET_AVATARS"
            :key="item.id"
            type="button"
            class="ap-option"
            :class="{ active: selection === 'preset:' + item.id }"
            :title="item.name"
            @click="choose('preset:' + item.id)"
          >
            <img :src="item.src" :alt="item.name" />
          </button>
        </div>

        <p class="ap-label">自主上传</p>
        <div class="ap-upload-row">
          <button type="button" class="ap-upload" @click="fileInput?.click()">选择本地图片</button>
          <span class="ap-hint">自动裁剪为方形，压缩后仅保存在本机</span>
        </div>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="onFile" />
        <p v-if="error" class="ap-error">{{ error }}</p>

        <div class="ap-actions">
          <button type="button" class="ap-reset" @click="choose(null)">恢复默认</button>
          <button type="button" class="ap-done" @click="$emit('close')">完成</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { PRESET_AVATARS, getAvatarSrc, getAvatarSelection, saveAvatar, fileToAvatar } from '../utils/avatar'

const props = defineProps({ nickname: { type: String, default: '' } })
const emit = defineEmits(['close', 'change'])
const fileInput = ref(null)
const error = ref('')
const selection = ref(getAvatarSelection())
const preview = ref(getAvatarSrc())
const initial = computed(() => (props.nickname || '你')[0])

function choose(value) {
  if (!saveAvatar(value)) { error.value = '保存失败，可能超出浏览器存储限制'; return }
  selection.value = value
  preview.value = getAvatarSrc()
  error.value = ''
  emit('change', preview.value)
}
async function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  try {
    const dataUrl = await fileToAvatar(file)
    choose(dataUrl)
  } catch (e) {
    error.value = e.message || '上传失败'
  }
}
</script>

<style scoped>
.ap-overlay { position: fixed; inset: 0; z-index: 400; display: grid; place-items: center; padding: 20px; background: rgba(60, 58, 52, .38); backdrop-filter: blur(4px); }
.ap-panel { width: min(400px, 100%); max-height: 88vh; overflow: auto; padding: 22px; border-radius: 18px; background: #FBFAF7; border: 1px solid #E3DFD6; box-shadow: 0 18px 50px rgba(74, 74, 69, .18); }
.ap-head { display: flex; align-items: center; justify-content: space-between; }
.ap-head h3 { font-size: 17px; font-weight: 600; color: #4A4A45; }
.ap-close { width: 30px; height: 30px; border-radius: 8px; background: transparent; color: #8B8B83; font-size: 20px; line-height: 1; }
.ap-close:hover { background: #EFEDE6; }
.ap-preview { width: 84px; height: 84px; margin: 18px auto 6px; border-radius: 24px; overflow: hidden; display: grid; place-items: center; background: var(--primary, #9CAF9C); color: #fff; font-size: 32px; border: 1px solid #E3DFD6; }
.ap-preview img { width: 100%; height: 100%; object-fit: cover; }
.ap-label { margin: 16px 0 8px; font-size: 12px; color: #8B8B83; letter-spacing: .04em; }
.ap-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.ap-option { padding: 0; border-radius: 16px; overflow: hidden; border: 2px solid transparent; background: #EFEDE6; aspect-ratio: 1; transition: transform .16s ease, border-color .16s ease; }
.ap-option img { display: block; width: 100%; height: 100%; }
.ap-option:hover { transform: translateY(-2px); }
.ap-option.active { border-color: #7C8B7D; }
.ap-upload-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ap-upload { padding: 9px 16px; border-radius: 10px; background: #EFEDE6; color: #4A4A45; font-size: 13px; border: 1px dashed #C9C4B8; }
.ap-upload:hover { background: #E7E3D9; }
.ap-hint { font-size: 11px; color: #9B978C; }
.ap-error { margin-top: 10px; color: #B4614F; font-size: 12px; }
.ap-actions { display: flex; justify-content: space-between; gap: 10px; margin-top: 20px; }
.ap-reset { padding: 9px 14px; border-radius: 10px; background: transparent; color: #8B8B83; font-size: 13px; border: 1px solid #E3DFD6; }
.ap-done { padding: 9px 22px; border-radius: 10px; background: #7C8B7D; color: #FBFAF7; font-size: 13px; }
.ap-done:hover { background: #6B7A6C; }
</style>
