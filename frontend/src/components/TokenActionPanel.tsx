import { useState, useMemo } from 'react'
import type { Token } from '../types'
import { STYLE_TYPES, STYLE_LABELS } from '../types'
import { useReaderStore } from '../store'
import { saveTokens, splitTokenByMeaning } from '../api'

type OpTab = 'meaning' | 'char' | 'merge'

export default function TokenActionPanel() {
  const tokens = useReaderStore((s) => s.tokens)
  const selectedTokenId = useReaderStore((s) => s.selectedTokenId)
  const document = useReaderStore((s) => s.document)
  const saving = useReaderStore((s) => s.saving)
  const setSelectedToken = useReaderStore((s) => s.setSelectedToken)
  const setSaving = useReaderStore((s) => s.setSaving)
  const updateToken = useReaderStore((s) => s.updateToken)
  const splitTokenAll = useReaderStore((s) => s.splitTokenAll)
  const mergeAdjacentAll = useReaderStore((s) => s.mergeAdjacentAll)

  const token = tokens.find((t) => t.id === selectedTokenId)
  if (!token) {
    setSelectedToken(null)
    return null
  }

  const [refType, setRefType] = useState<string>(token.ref_type || '')
  const [targetId, setTargetId] = useState(token.ref_target_token_id || '')
  const [url, setUrl] = useState(token.ref_url || '')
  const [explanation, setExplanation] = useState(token.ref_explanation || '')
  const [styleType, setStyleType] = useState(token.style_type)
  const [opTab, setOpTab] = useState<OpTab>('meaning')
  const [checkedOffsets, setCheckedOffsets] = useState<Set<number>>(new Set())
  const [charSplitPos, setCharSplitPos] = useState<number | null>(null)
  const chars = [...token.text]

  const adjacentGroups = useMemo(() => {
    const groups = new Map<string, { text: string; direction: 'prev' | 'next'; ids: Set<string>; count: number }>()
    for (const off of token.start_offsets) {
      for (const t of tokens) {
        for (const so of t.start_offsets) {
          if (so + t.text.length === off) {
            const key = `prev:${t.text}`
            const g = groups.get(key)
            if (g) {
              g.ids.add(t.id)
              g.count++
            } else {
              groups.set(key, { text: t.text, direction: 'prev', ids: new Set([t.id]), count: 1 })
            }
          }
          if (so === off + token.text.length) {
            const key = `next:${t.text}`
            const g = groups.get(key)
            if (g) {
              g.ids.add(t.id)
              g.count++
            } else {
              groups.set(key, { text: t.text, direction: 'next', ids: new Set([t.id]), count: 1 })
            }
          }
        }
      }
    }
    return [...groups.values()]
  }, [token, tokens])

  const handleSave = async () => {
    updateToken(token.id, {
      style_type: styleType,
      ref_type: (refType || null) as Token['ref_type'],
      ref_target_token_id: refType === 'internal' ? targetId : null,
      ref_url: refType === 'external' ? url : null,
      ref_explanation: refType === 'note' ? explanation : null,
    })
    if (!document) return
    setSaving(true)
    try {
      const saved = await saveTokens(document.id, useReaderStore.getState().tokens)
      useReaderStore.setState({ tokens: saved })
    } catch (e) {
      alert(`保存失败：${e instanceof Error ? e.message : e}`)
    } finally {
      setSaving(false)
    }
  }

  const handleSplitMeaning = async () => {
    if (checkedOffsets.size === 0 || checkedOffsets.size >= token.start_offsets.length) return
    try {
      const updated = await splitTokenByMeaning(token.id, [...checkedOffsets])
      useReaderStore.setState({ tokens: [...updated.tokens] })
    } catch (e) {
      alert(`拆分失败：${e instanceof Error ? e.message : e}`)
    }
    setSelectedToken(null)
  }

  const handleCharSplit = () => {
    if (charSplitPos === null) return
    splitTokenAll(token.id, charSplitPos)
    setCharSplitPos(null)
  }

  const handleMergeGroup = (ids: string[]) => {
    mergeAdjacentAll(token.id, ids)
  }

  const toggleOffset = (off: number) => {
    setCheckedOffsets((prev) => {
      const next = new Set(prev)
      if (next.has(off)) next.delete(off)
      else next.add(off)
      return next
    })
  }

  const target =
    token.ref_type === 'internal' && token.ref_target_token_id
      ? tokens.find((t) => t.id === token.ref_target_token_id)
      : null

  const TAB_LABELS: Record<OpTab, string> = {
    meaning: '拆分含义',
    char: '分词拆分',
    merge: '合并相邻',
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="font-medium text-lg truncate flex-1">
          <span className="text-gray-400">「</span>
          {token.text}
          <span className="text-gray-400">」</span>
        </div>
        <button
          onClick={() => setSelectedToken(null)}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-2 shrink-0"
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* ── Style type ── */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            样式类型
          </label>
          <select
            value={styleType}
            onChange={(e) => setStyleType(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            {STYLE_TYPES.map((t) => (
              <option key={t} value={t}>
                {STYLE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>

        {/* ── Referent type ── */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            指代类型
          </label>
          <select
            value={refType}
            onChange={(e) => {
              setRefType(e.target.value)
              setTargetId('')
              setUrl('')
              setExplanation('')
            }}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="">无指代</option>
            <option value="internal">文中指代</option>
            <option value="external">外部链接</option>
            <option value="note">文字注释</option>
          </select>
        </div>

        {refType === 'internal' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              指代目标（文中分词）
            </label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">选择目标...</option>
              {tokens
                .filter((t) => t.id !== token.id)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.text}
                  </option>
                ))}
            </select>
          </div>
        )}

        {refType === 'external' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              外部 URL
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://..."
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
        )}

        {refType === 'note' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              解释文字
            </label>
            <textarea
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              rows={3}
              className="w-full border rounded px-3 py-2 text-sm resize-y"
            />
          </div>
        )}

        {token.ref_type && (
          <div className="bg-gray-50 rounded p-3 text-sm">
            <div className="text-xs text-gray-400 mb-1">当前指代</div>
            {token.ref_type === 'internal' && target && (
              <div className="text-gray-700">
                指代 → <span className="font-medium">{target.text}</span>
              </div>
            )}
            {token.ref_type === 'external' && token.ref_url && (
              <a
                href={token.ref_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline break-all"
              >
                {token.ref_url}
              </a>
            )}
            {token.ref_type === 'note' && token.ref_explanation && (
              <div className="text-gray-600">{token.ref_explanation}</div>
            )}
          </div>
        )}

        {/* ── Divider ── */}
        <div className="border-t" />

        {/* ── Operations (tabs) ── */}
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wide">
          操作
        </div>

        {/* Tab bar */}
        <div className="flex border rounded overflow-hidden">
          {(Object.keys(TAB_LABELS) as OpTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setOpTab(tab)}
              className={`flex-1 px-2 py-1.5 text-xs transition-colors
                ${opTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        {/* Tab: Meaning split */}
        {opTab === 'meaning' && (
          <div className="border rounded p-3">
            {token.start_offsets.length <= 1 ? (
              <div className="text-xs text-gray-400">该分词仅出现一次，无需拆分</div>
            ) : (
              <div>
                <p className="text-xs text-gray-600 mb-2">
                  勾选要移走的出现位置（{token.start_offsets.length} 处）：
                </p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {token.start_offsets.map((off) => {
                    const ctxStart = Math.max(0, off - 8)
                    const ctxEnd = Math.min(
                      document?.original_text.length || 0,
                      off + token.text.length + 8
                    )
                    const ctx = document?.original_text.slice(ctxStart, ctxEnd) || ''
                    const innerStart = off - ctxStart
                    const innerEnd = innerStart + token.text.length
                    return (
                      <label
                        key={off}
                        className="flex items-center gap-2 text-xs cursor-pointer hover:bg-orange-100 px-1 py-0.5 rounded"
                      >
                        <input
                          type="checkbox"
                          checked={checkedOffsets.has(off)}
                          onChange={() => toggleOffset(off)}
                        />
                        <span className="text-gray-400 w-10 shrink-0">#{off}</span>
                        <span className="truncate">
                          {ctx.slice(0, innerStart)}
                          <strong>{ctx.slice(innerStart, innerEnd)}</strong>
                          {ctx.slice(innerEnd)}
                        </span>
                      </label>
                    )
                  })}
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => setCheckedOffsets(new Set())}
                    className="px-3 py-1 text-xs border rounded hover:bg-gray-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSplitMeaning}
                    disabled={
                      checkedOffsets.size === 0 ||
                      checkedOffsets.size >= token.start_offsets.length
                    }
                    className="px-3 py-1 text-xs bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50"
                  >
                    确认拆分
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Char split */}
        {opTab === 'char' && (
          <div className="border rounded p-3">
            <div className="flex items-center flex-wrap justify-center gap-0 mb-2 py-2 bg-gray-50 rounded text-base">
              {chars.map((ch, i) => (
                <span key={i}>
                  {i > 0 && (
                    <button
                      onClick={() => setCharSplitPos(i)}
                      className={`inline-block w-1.5 h-6 mx-0.5 rounded-sm transition-colors cursor-pointer
                        ${charSplitPos === i
                          ? 'bg-blue-500'
                          : 'bg-gray-300 hover:bg-blue-300'
                        }`}
                    />
                  )}
                  <span className="inline-block px-0.5">{ch}</span>
                </span>
              ))}
            </div>
            <button
              onClick={handleCharSplit}
              disabled={charSplitPos === null}
              className="w-full px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              确认拆分
            </button>
          </div>
        )}

        {/* Tab: Merge adjacent */}
        {opTab === 'merge' && (
          <div className="border rounded p-3 space-y-2">
            {adjacentGroups.length === 0 ? (
              <div className="text-xs text-gray-400">无可合并的相邻分词</div>
            ) : (
              adjacentGroups.map((g) => (
                <div
                  key={`${g.direction}:${g.text}`}
                  className="flex items-center justify-between gap-2 p-2 border rounded text-xs"
                >
                  <span className="text-gray-500 truncate">
                    {g.direction === 'prev' ? '← 合并「' : '合并→「'}
                    <span className="font-medium text-gray-700">{g.text}</span>
                    」{g.count > 1 && <span>（{g.count}处）</span>}
                  </span>
                  <button
                    onClick={() => handleMergeGroup([...g.ids])}
                    className="px-2 py-0.5 bg-green-600 text-white rounded hover:bg-green-700 shrink-0"
                  >
                    合并
                  </button>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex gap-3 p-4 border-t shrink-0">
        <button
          onClick={() => setSelectedToken(null)}
          className="flex-1 px-4 py-2 text-sm border rounded hover:bg-gray-50"
        >
          关闭
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )
}
