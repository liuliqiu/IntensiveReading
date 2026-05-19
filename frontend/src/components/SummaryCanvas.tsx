import { useMemo } from 'react'
import type { RenderToken } from '../types'
import { useReaderStore } from '../store'
import TokenSpan from './TokenSpan'

export default function SummaryCanvas() {
  const layerTokens = useReaderStore((s) => s.layerTokens)
  const layerText = useReaderStore((s) => {
    const lid = s.selectedLayerId
    return s.layers.find((l) => l.id === lid)?.text || ''
  })

  const renderItems: RenderToken[] = useMemo(() => {
    return layerTokens
      .flatMap((token) =>
        token.start_offsets.map((offset) => ({
          token,
          start_offset: offset,
          key: `layer:${token.id}@${offset}`,
        }))
      )
      .sort((a, b) => a.start_offset - b.start_offset)
  }, [layerTokens])

  if (!layerText) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        暂无摘要，请先生成
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-3xl mx-auto text-lg leading-8 text-gray-800 whitespace-pre-wrap">
        {renderItems.map((item) => (
          <TokenSpan key={item.key} renderToken={item} canvas="layer" />
        ))}
      </div>
    </div>
  )
}
