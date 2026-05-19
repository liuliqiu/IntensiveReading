import { useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReaderStore } from '../store'
import { createLayer, fetchLayers, summarizeLayer } from '../api'

export default function Toolbar() {
  const navigate = useNavigate()
  const document = useReaderStore((s) => s.document)
  const tokens = useReaderStore((s) => s.tokens)
  const viewMode = useReaderStore((s) => s.viewMode)
  const setViewMode = useReaderStore((s) => s.setViewMode)
  const selectedLayerId = useReaderStore((s) => s.selectedLayerId)
  const setSelectedLayer = useReaderStore((s) => s.setSelectedLayer)
  const setLayers = useReaderStore((s) => s.setLayers)
  const setLayerData = useReaderStore((s) => s.setLayerData)
  const summarizing = useReaderStore((s) => s.summarizing)
  const setSummarizing = useReaderStore((s) => s.setSummarizing)
  const layers = useReaderStore((s) => s.layers)

  useEffect(() => {
    if (!document) return
    fetchLayers(document.id).then((ls) => {
      setLayers(ls)
      const summaryLayer = ls.find((l) => l.type === 'summary')
      if (summaryLayer) {
        setSelectedLayer(summaryLayer.id)
        setLayerData(summaryLayer)
      }
    })
  }, [document, setLayers, setSelectedLayer, setLayerData])

  const handleSummarize = useCallback(async () => {
    if (!document) return
    setSummarizing(true)
    try {
      let layer = layers.find((l) => l.type === 'summary')
      if (!layer) {
        layer = await createLayer(document.id, 'summary')
        setSelectedLayer(layer.id)
        const ls = await fetchLayers(document.id)
        setLayers(ls)
      }
      const result = await summarizeLayer(layer.id)
      setLayerData(result)
      setSelectedLayer(result.id)
      setLayers(useReaderStore.getState().layers.map((l) => (l.id === result.id ? result : l)))
    } catch (e) {
      alert(`摘要生成失败：${e instanceof Error ? e.message : e}`)
    } finally {
      setSummarizing(false)
    }
  }, [document, layers, setSummarizing, setSelectedLayer, setLayers, setLayerData])

  const hasSummary = layers.some((l) => l.type === 'summary' && l.text)

  return (
    <div className="flex items-center gap-3 p-3 border-b bg-white shrink-0">
      <button
        onClick={() => navigate('/')}
        className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1"
      >
        ← 返回
      </button>

      <div className="flex items-center gap-1 border rounded overflow-hidden">
        {(['original', 'layer'] as const).map((mode) => {
          const labels: Record<string, string> = { original: '原文', layer: '摘要' }
          const disabled = mode !== 'original' && !hasSummary
          return (
            <button
              key={mode}
              onClick={() => !disabled && setViewMode(mode)}
              disabled={disabled}
              className={`px-2 py-1 text-xs transition-colors
                ${viewMode === mode
                  ? 'bg-blue-600 text-white'
                  : disabled
                    ? 'text-gray-300 cursor-not-allowed'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
            >
              {labels[mode]}
            </button>
          )
        })}
      </div>

      <div className="flex-1 text-sm font-medium text-gray-700 truncate">
        {document?.title}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">
          {tokens.length} 个分词
        </span>
        <button
          onClick={handleSummarize}
          disabled={summarizing || !document}
          className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {summarizing ? '生成中...' : hasSummary ? '重新生成摘要' : '🤖 生成摘要'}
        </button>
      </div>
    </div>
  )
}
