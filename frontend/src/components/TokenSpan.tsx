import { useState, useCallback } from 'react'
import type { Token } from '../types'
import { STYLE_CLASSES } from '../types'
import { useReaderStore } from '../store'
import TokenPopover from './TokenPopover'
import TokenSplitModal from './TokenSplitModal'
import ReferentEditor from './ReferentEditor'

interface Props {
  token: Token
}

export default function TokenSpan({ token }: Props) {
  const {
    editMode,
    hoveredTokenId,
    selectedTokenId,
    tokens,
    setHoveredToken,
    setSelectedToken,
    splitToken,
    mergeTokens,
    updateToken,
  } = useReaderStore()

  const [popoverOpen, setPopoverOpen] = useState(false)
  const [splitModalOpen, setSplitModalOpen] = useState(false)
  const [refEditorOpen, setRefEditorOpen] = useState(false)

  const isSelected = selectedTokenId === token.id

  const styleClass = STYLE_CLASSES[token.style_type] || STYLE_CLASSES.default

  const handleClick = useCallback(() => {
    if (editMode === 'split') {
      setSplitModalOpen(true)
    } else if (editMode === 'merge') {
      if (isSelected) {
        setSelectedToken(null)
      } else if (selectedTokenId === null) {
        setSelectedToken(token.id)
      } else {
        const idxA = tokens.findIndex((t) => t.id === selectedTokenId)
        const idxB = tokens.findIndex((t) => t.id === token.id)
        if (Math.abs(idxA - idxB) === 1) {
          const first = idxA < idxB ? selectedTokenId : token.id
          mergeTokens(first)
        } else {
          setSelectedToken(token.id)
        }
      }
    } else {
      if (isSelected) {
        setSelectedToken(null)
      } else {
        setSelectedToken(token.id)
      }
    }
  }, [editMode, isSelected, selectedTokenId, token.id, tokens, mergeTokens, setSelectedToken])

  const isMergeTarget =
    editMode === 'merge' &&
    selectedTokenId !== null &&
    selectedTokenId !== token.id &&
    (() => {
      const idxA = tokens.findIndex((t) => t.id === selectedTokenId)
      const idxB = tokens.findIndex((t) => t.id === token.id)
      return Math.abs(idxA - idxB) === 1
    })()

  return (
    <>
      <span
        className={`relative inline cursor-pointer transition-colors px-0.5 rounded-sm
          ${styleClass}
          ${isSelected ? 'ring-2 ring-blue-400 ring-inset' : ''}
          ${editMode === 'split' && hoveredTokenId === token.id ? 'bg-yellow-100' : ''}
          ${isMergeTarget ? 'bg-green-100' : ''}
        `}
        onMouseEnter={() => {
          setHoveredToken(token.id)
          setPopoverOpen(true)
        }}
        onMouseLeave={() => {
          setHoveredToken(null)
          setPopoverOpen(false)
        }}
        onClick={handleClick}
      >
        {token.text}
        <TokenPopover
          token={token}
          isHovered={popoverOpen && editMode === 'view'}
          onMouseEnter={() => setPopoverOpen(true)}
          onMouseLeave={() => setPopoverOpen(false)}
          onEditReferent={() => setRefEditorOpen(true)}
        />
      </span>

      {splitModalOpen && (
        <TokenSplitModal
          token={token}
          onSplit={(pos) => {
            splitToken(token.id, pos)
            setSplitModalOpen(false)
          }}
          onClose={() => setSplitModalOpen(false)}
        />
      )}

      {refEditorOpen && (
        <ReferentEditor
          token={token}
          allTokens={tokens}
          onSave={(data) => updateToken(token.id, data)}
          onClose={() => setRefEditorOpen(false)}
        />
      )}
    </>
  )
}
