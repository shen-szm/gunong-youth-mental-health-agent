// 头像工具：预设头像（内联 SVG，若竹 / 浅梅 / 奶酪 / 尼蓝色系）+ 本地上传，按用户持久化到 localStorage。
const PRESET_COLORS = {
  sage: '#8FCBA6', mist: '#8FA3B0', rose: '#E9C4C8', oat: '#EBD4A4',
  clay: '#CF9AA1', lavender: '#A9A3B5', pine: '#55A87C', sand: '#E8C783',
}

function svgAvatar(bg, body) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect width="96" height="96" rx="22" fill="${bg}"/>${body}</svg>`
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}
const soft = '#F7F3E8'
export const PRESET_AVATARS = [
  { id: 'leaf', name: '枝叶', src: svgAvatar(PRESET_COLORS.sage, `<path d="M48 74V40" stroke="${soft}" stroke-width="4" stroke-linecap="round"/><path d="M48 46C48 30 60 22 74 24C74 40 64 48 48 46Z" fill="${soft}"/><path d="M48 58C48 46 38 40 26 42C26 54 36 60 48 58Z" fill="${soft}" opacity=".8"/>`) },
  { id: 'mountain', name: '远山', src: svgAvatar(PRESET_COLORS.mist, `<path d="M14 68L38 34L56 58L66 44L84 68Z" fill="${soft}"/><circle cx="66" cy="28" r="8" fill="${soft}" opacity=".85"/>`) },
  { id: 'moon', name: '月色', src: svgAvatar(PRESET_COLORS.lavender, `<path d="M60 22A26 26 0 1 0 74 62A22 22 0 1 1 60 22Z" fill="${soft}"/><circle cx="66" cy="30" r="2.4" fill="${soft}"/>`) },
  { id: 'wave', name: '潮汐', src: svgAvatar(PRESET_COLORS.pine, `<path d="M12 56C24 44 34 44 46 56S68 68 84 54" stroke="${soft}" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M12 70C24 58 34 58 46 70S68 82 84 68" stroke="${soft}" stroke-width="5" fill="none" stroke-linecap="round" opacity=".65"/><circle cx="48" cy="30" r="7" fill="${soft}"/>`) },
  { id: 'blossom', name: '花序', src: svgAvatar(PRESET_COLORS.rose, `<g fill="${soft}"><ellipse cx="48" cy="34" rx="9" ry="14"/><ellipse cx="48" cy="62" rx="9" ry="14"/><ellipse cx="34" cy="48" rx="14" ry="9"/><ellipse cx="62" cy="48" rx="14" ry="9"/></g><circle cx="48" cy="48" r="7" fill="${PRESET_COLORS.oat}"/>`) },
  { id: 'cat', name: '团子', src: svgAvatar(PRESET_COLORS.oat, `<path d="M30 40L28 24L42 32ZM66 40L68 24L54 32Z" fill="#6B655C"/><rect x="26" y="34" width="44" height="36" rx="18" fill="#6B655C"/><circle cx="40" cy="50" r="3" fill="${soft}"/><circle cx="56" cy="50" r="3" fill="${soft}"/><path d="M44 60Q48 64 52 60" stroke="${soft}" stroke-width="2.6" fill="none" stroke-linecap="round"/>`) },
  { id: 'sun', name: '暖阳', src: svgAvatar(PRESET_COLORS.clay, `<circle cx="48" cy="48" r="16" fill="${soft}"/><g stroke="${soft}" stroke-width="4" stroke-linecap="round"><path d="M48 18V26M48 70V78M18 48H26M70 48H78M27 27L33 33M63 63L69 69M69 27L63 33M33 63L27 69"/></g>`) },
  { id: 'arch', name: '窗景', src: svgAvatar(PRESET_COLORS.sand, `<path d="M30 74V44a18 18 0 0 1 36 0V74Z" fill="${soft}"/><path d="M48 30V74M30 52H66" stroke="${PRESET_COLORS.sand}" stroke-width="3"/><circle cx="48" cy="42" r="6" fill="${PRESET_COLORS.clay}"/>`) },
]

const STORAGE_PREFIX = 'shengyu_avatar_'
function key() {
  const uid = localStorage.getItem('shengyu_user_id') || 'guest'
  return STORAGE_PREFIX + uid
}
export function getAvatarSrc() {
  try {
    const saved = localStorage.getItem(key())
    if (!saved) return null
    if (saved.startsWith('preset:')) {
      return PRESET_AVATARS.find(a => a.id === saved.slice(7))?.src || null
    }
    return saved
  } catch { return null }
}
export function getAvatarSelection() {
  try { return localStorage.getItem(key()) } catch { return null }
}
export function saveAvatar(value) {
  try {
    if (value) localStorage.setItem(key(), value)
    else localStorage.removeItem(key())
  } catch { return false }
  return true
}
// 上传图片压缩为 256px dataURL，避免 localStorage 超限。
export function fileToAvatar(file) {
  return new Promise((resolve, reject) => {
    if (!file || !/^image\//.test(file.type)) { reject(new Error('请选择图片文件')); return }
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('读取文件失败'))
    reader.onload = () => {
      const img = new Image()
      img.onerror = () => reject(new Error('图片无法解析'))
      img.onload = () => {
        const size = 256
        const canvas = document.createElement('canvas')
        canvas.width = size; canvas.height = size
        const ctx = canvas.getContext('2d')
        const side = Math.min(img.width, img.height)
        ctx.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, size, size)
        resolve(canvas.toDataURL('image/jpeg', 0.86))
      }
      img.src = reader.result
    }
    reader.readAsDataURL(file)
  })
}
