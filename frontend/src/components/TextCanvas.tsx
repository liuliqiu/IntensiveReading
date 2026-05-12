import { useMemo } from 'react'
import type { Token, RenderToken } from '../types'
import TokenSpan from './TokenSpan'

interface Props {
  tokens: Token[]
}

export default function TextCanvas({ tokens }: Props) {
  const renderItems: RenderToken[] = useMemo(() => {
    return tokens
      .flatMap((token) =>
        token.start_offsets.map((offset) => ({
          token,
          start_offset: offset,
          key: `${token.id}@${offset}`,
        }))
      )
      .sort((a, b) => a.start_offset - b.start_offset)
  }, [tokens])

  return (
    <div className="p-6">
      <div className="max-w-3xl mx-auto text-lg leading-8 text-gray-800 whitespace-pre-wrap">
        {renderItems.map((item) => (
          <TokenSpan key={item.key} renderToken={item} />
        ))}
      </div>
    </div>
  )
}
