export function createIslandBridge() {
  const listeners = new Map()
  return {
    emit(event, payload) {
      for (const listener of listeners.get(event) || []) listener(payload)
    },
    on(event, listener) {
      const bucket = listeners.get(event) || new Set()
      bucket.add(listener)
      listeners.set(event, bucket)
      return () => bucket.delete(listener)
    },
    clear() {
      listeners.clear()
    },
  }
}
