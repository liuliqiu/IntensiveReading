import { useNavigate } from 'react-router-dom'
import type { EditMode } from '../types'
import { useReaderStore } from '../store'
import { saveTokens } from '../api'

const MODE_LABELS: Record<EditMode, string> = { view: '查看', split: '拆分', merge: '合并' }

export default function Toolbar() {
  const navigate = useNavigate()
  const {
    document,
    editMode,
    tokens,
    saving,
    setEditMode,
    setSaving,
  } = useReaderStore()

  const handleSave = async () => {
    if (!document) return
    setSaving(true)
    try {
      const saved = await saveTokens(document.id, tokens)
      useReaderStore.setState({ tokens: saved })
    } catch (e) {
      alert(`保存失败：${e instanceof Error ? e.message : e}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex items-center gap-3 p-3 border-b bg-white sticky top-0 z-40">
      <button
        onClick={() => navigate('/')}
        className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1"
      >
        ← 返回
      </button>

      <div className="flex-1 text-sm font-medium text-gray-700 truncate">
        {document?.title}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">
          {tokens.length} 个分词
        </span>
      </div>

      <div className="flex items-center gap-1 border rounded overflow-hidden">
        {(['view', 'split', 'merge'] as EditMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setEditMode(mode)}
            className={`px-3 py-1.5 text-xs transition-colors
              ${editMode === mode
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
          >
            {MODE_LABELS[mode]}
          </button>
        ))}
      </div>

      <button
        onClick={handleSave}
        disabled={saving || editMode !== 'view'}
        className={`px-3 py-1.5 text-xs rounded transition-colors
          ${editMode === 'view'
            ? 'bg-green-600 text-white hover:bg-green-700'
            : 'bg-gray-200 text-gray-400'
          } disabled:opacity-50`}
      >
        {saving ? '保存中...' : '保存'}
      </button>
    </div>
  )
}
