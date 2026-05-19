import { useCallback } from 'react'
import type { RenderToken } from '../types'
import { useReaderStore } from '../store'

interface Props {
  renderToken: RenderToken
  canvas?: 'document' | 'layer'
}

export default function TokenSpan({ renderToken, canvas = 'document' }: Props) {
  const { token } = renderToken
  const store = useReaderStore()

  const isSelected = canvas === 'layer'
    ? store.layerSelectedTokenId === token.id
    : store.selectedTokenId === token.id

  const hoveredTokenId = canvas === 'layer'
    ? store.layerHoveredTokenId
    : store.hoveredTokenId

  const styleClass = `s-${token.style_type}`

  const handleClick = useCallback(() => {
    if (canvas === 'layer') {
      store.setLayerSelectedToken(isSelected ? null : token.id)
    } else {
      store.setSelectedToken(isSelected ? null : token.id)
    }
  }, [canvas, isSelected, token.id, store])

  return (
    <span
      className={`relative inline cursor-pointer transition-colors px-0.5 rounded-sm
        ${styleClass}
        ${isSelected ? 'ring-2 ring-blue-400 ring-inset' : ''}
        ${hoveredTokenId === token.id ? 'bg-gray-100' : ''}
      `}
      data-style-type={token.style_type}
      onClick={handleClick}
      onMouseEnter={() => canvas === 'layer'
        ? store.setLayerHoveredToken(token.id)
        : store.setHoveredToken(token.id)}
      onMouseLeave={() => canvas === 'layer'
        ? store.setLayerHoveredToken(null)
        : store.setHoveredToken(null)}
    >
      {token.text}
    </span>
  )
}
