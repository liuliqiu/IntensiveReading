import type { Token } from '../types'
import TokenSpan from './TokenSpan'

interface Props {
  tokens: Token[]
}

export default function TextCanvas({ tokens }: Props) {
  return (
    <div className="p-6">
      <div className="max-w-3xl mx-auto text-lg leading-8 text-gray-800 whitespace-pre-wrap">
        {tokens.map((token) => (
          <TokenSpan key={token.id} token={token} />
        ))}
      </div>
    </div>
  )
}
