import { useRef } from 'react'
import {
  useFloating,
  useHover,
  useInteractions,
  offset,
  shift,
  arrow,
  FloatingArrow,
} from '@floating-ui/react'
import type { Token } from '../types'
import { useReaderStore } from '../store'

interface Props {
  token: Token
  isHovered: boolean
  onMouseEnter: () => void
  onMouseLeave: () => void
  onEditReferent: () => void
}

export default function TokenPopover({
  token,
  isHovered,
  onMouseEnter,
  onMouseLeave,
  onEditReferent,
}: Props) {
  const arrowRef = useRef(null)
  const { refs, floatingStyles, context } = useFloating({
    placement: 'top',
    open: isHovered,
    middleware: [offset(8), shift(), arrow({ element: arrowRef })],
  })
  const hover = useHover(context, { delay: { open: 50, close: 100 } })
  const { getReferenceProps, getFloatingProps } = useInteractions([hover])

  const tokens = useReaderStore((s) => s.tokens)
  const target = token.ref_type === 'internal' && token.ref_target_token_id
    ? tokens.find((t) => t.id === token.ref_target_token_id)
    : null

  if (!isHovered) return null

  return (
    <>
      <div
        ref={refs.setReference}
        className="absolute inset-0"
        {...getReferenceProps({ onMouseEnter, onMouseLeave })}
      />
      <div
        ref={refs.setFloating}
        style={floatingStyles}
        className="z-50 bg-white border rounded-lg shadow-lg p-4 max-w-xs text-sm"
        {...getFloatingProps({ onMouseEnter, onMouseLeave })}
      >
        <FloatingArrow ref={arrowRef} context={context} className="fill-white" />
        <div className="font-medium mb-2">
          <span className="text-gray-400">「</span>
          {token.text}
          <span className="text-gray-400">」</span>
        </div>

        {token.ref_type && (
          <div className="space-y-1 text-gray-700">
            {token.ref_type === 'internal' && target && (
              <div>
                <span className="text-gray-500 text-xs">指代：</span>
                {target.text}
              </div>
            )}
            {token.ref_type === 'external' && token.ref_url && (
              <div>
                <span className="text-gray-500 text-xs">外部：</span>
                <a
                  href={token.ref_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline"
                >
                  {token.ref_url}
                </a>
              </div>
            )}
            {token.ref_type === 'note' && token.ref_explanation && (
              <div className="text-gray-600">{token.ref_explanation}</div>
            )}
          </div>
        )}

        <button
          onClick={(e) => {
            e.stopPropagation()
            onEditReferent()
          }}
          className="mt-3 text-xs text-blue-600 hover:text-blue-800"
        >
          {token.ref_type ? '编辑指代' : '添加指代'}
        </button>
      </div>
    </>
  )
}
