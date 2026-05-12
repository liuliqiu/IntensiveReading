import { useCallback } from 'react'
import type { RenderToken } from '../types'
import { useReaderStore } from '../store'

interface Props {
  renderToken: RenderToken
}

export default function TokenSpan({ renderToken }: Props) {
  const { token } = renderToken
  const {
    hoveredTokenId,
    selectedTokenId,
    setSelectedToken,
    setHoveredToken,
  } = useReaderStore()

  const isSelected = selectedTokenId === token.id
  const styleClass = `s-${token.style_type}`

  const handleClick = useCallback(() => {
    if (isSelected) {
      setSelectedToken(null)
    } else {
      setSelectedToken(token.id)
    }
  }, [isSelected, token.id, setSelectedToken])

  return (
    <span
      className={`relative inline cursor-pointer transition-colors px-0.5 rounded-sm
        ${styleClass}
        ${isSelected ? 'ring-2 ring-blue-400 ring-inset' : ''}
        ${hoveredTokenId === token.id ? 'bg-gray-100' : ''}
      `}
      data-style-type={token.style_type}
      onClick={handleClick}
      onMouseEnter={() => setHoveredToken(token.id)}
      onMouseLeave={() => setHoveredToken(null)}
    >
      {token.text}
    </span>
  )
}
