import { useState, useMemo, useCallback } from 'react'
import type { Relation, RelationMember, RelationObject, Token } from '../types'
import { STYLE_TYPES, STYLE_LABELS, RELATION_TYPES, RELATION_LABELS } from '../types'
import { useReaderStore } from '../store'
import {
  saveDocument, splitTokenByMeaning, explainObject,
  createKnowledgeObject, deleteKnowledgeObject,
  createKnowledgeRelation, updateKnowledgeRelation, deleteKnowledgeRelation,
} from '../api'

type OpTab = 'meaning' | 'char' | 'merge'

export default function TokenActionPanel() {
  const viewMode = useReaderStore((s) => s.viewMode)
  const selectedTokenId = useReaderStore((s) => s.selectedTokenId)
  const layerSelectedTokenId = useReaderStore((s) => s.layerSelectedTokenId)
  const tokens = useReaderStore((s) => s.tokens)

  const effectiveTokenId = layerSelectedTokenId || selectedTokenId
  const token = effectiveTokenId
    ? tokens.find((t) => t.id === effectiveTokenId)
    : undefined

  if (!token) {
    return <RelationOverview />
  }

  return <TokenDetail token={token} isLayerView={viewMode === 'summary'} />
}

function TokenDetail({ token, isLayerView }: { token: Token; isLayerView: boolean }) {
  const tokens = useReaderStore((s) => s.tokens)
  const relationObjects = useReaderStore((s) => s.relation_objects)
  const relations = useReaderStore((s) => s.relations)
  const document = useReaderStore((s) => s.document)
  const saving = useReaderStore((s) => s.saving)
  const explaining = useReaderStore((s) => s.explaining)
  const setSelectedToken = useReaderStore((s) => s.setSelectedToken)
  const setLayerSelectedToken = useReaderStore((s) => s.setLayerSelectedToken)
  const setSaving = useReaderStore((s) => s.setSaving)
  const setExplaining = useReaderStore((s) => s.setExplaining)
  const updateToken = useReaderStore((s) => s.updateToken)
  const splitTokenAll = useReaderStore((s) => s.splitTokenAll)
  const mergeAdjacentAll = useReaderStore((s) => s.mergeAdjacentAll)
  const setRelationObjects = useReaderStore((s) => s.setRelationObjects)
  const setRelations = useReaderStore((s) => s.setRelations)
  const setDocument = useReaderStore((s) => s.setDocument)

  const tokenRelationObject = relationObjects.find((ro) => ro.text === token.text && ro.kind !== 'document')

  const tokenRelations = useMemo(
    () =>
      tokenRelationObject
        ? relations.filter((r) => r.members.some((m) => m.id === tokenRelationObject.id))
        : [],
    [relations, tokenRelationObject]
  )

  const relatedObjectIds = useMemo(() => {
    if (!tokenRelationObject) return new Set<string>()
    const ids = new Set<string>()
    for (const rel of relations) {
      const hasCurrent = rel.members.some((m) => m.id === tokenRelationObject.id)
      if (hasCurrent) {
        for (const m of rel.members) {
          if (m.kind === 'object') ids.add(m.id)
        }
      }
    }
    return ids
  }, [relations, tokenRelationObject])

  const [styleType, setStyleType] = useState(token.style_type)

  const [editingRelId, setEditingRelId] = useState<string | null>(null)
  const [editType, setEditType] = useState<string>('')
  const [editCustomType, setEditCustomType] = useState('')
  const [editMembers, setEditMembers] = useState<RelationMember[]>([])

  const [showTextObj, setShowTextObj] = useState(false)
  const [textObjValue, setTextObjValue] = useState('')

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
            if (g) { g.ids.add(t.id); g.count++ }
            else { groups.set(key, { text: t.text, direction: 'prev', ids: new Set([t.id]), count: 1 }) }
          }
          if (so === off + token.text.length) {
            const key = `next:${t.text}`
            const g = groups.get(key)
            if (g) { g.ids.add(t.id); g.count++ }
            else { groups.set(key, { text: t.text, direction: 'next', ids: new Set([t.id]), count: 1 }) }
          }
        }
      }
    }
    return [...groups.values()]
  }, [token, tokens])

  const handleConvertToken = async () => {
    if (tokenRelationObject || !document) return
    const knowledge = await createKnowledgeObject({ text: token.text, document_id: document.id })
    setRelationObjects(knowledge.relation_objects)
    setRelations(knowledge.relations)
  }

  const handleDeleteTokenObject = async () => {
    if (!tokenRelationObject) return
    try {
      const knowledge = await deleteKnowledgeObject(tokenRelationObject.id)
      setRelationObjects(knowledge.relation_objects)
      setRelations(knowledge.relations)
    } catch (e) {
      alert(`删除失败：${e instanceof Error ? e.message : e}`)
    }
  }

  const handleAddTextObject = async () => {
    if (!textObjValue.trim() || !document) return
    const knowledge = await createKnowledgeObject({ text: textObjValue.trim(), document_id: document.id })
    setRelationObjects(knowledge.relation_objects)
    setRelations(knowledge.relations)
    setTextObjValue('')
    setShowTextObj(false)
  }

  const startCreating = () => {
    setEditingRelId('new')
    setEditType('')
    setEditCustomType('')
    setEditMembers(
      tokenRelationObject ? [{ kind: 'object' as const, id: tokenRelationObject.id }] : []
    )
  }

  const startEditing = (rel: Relation) => {
    setEditingRelId(rel.id)
    setEditType(rel.type)
    setEditCustomType('')
    setEditMembers(rel.members.map((m) => ({ ...m })))
  }

  const cancelEditing = () => setEditingRelId(null)

  const toggleMemberSelection = (kind: 'object' | 'relation', id: string) => {
    setEditMembers((prev) => {
      const idx = prev.findIndex((m) => m.kind === kind && m.id === id)
      if (idx >= 0) return prev.filter((_, i) => i !== idx)
      return [...prev, { kind, id }]
    })
  }

  const isMemberSelected = (kind: 'object' | 'relation', id: string) =>
    editMembers.some((m) => m.kind === kind && m.id === id)

  const commitEditing = async () => {
    const type = editType === '__custom__' ? editCustomType.trim() : editType
    if (!type) return
    if (editMembers.length < 2) return

    try {
      if (editingRelId === 'new') {
        const knowledge = await createKnowledgeRelation({ type, members: editMembers.map((m) => ({ ...m })) })
        setRelationObjects(knowledge.relation_objects)
        setRelations(knowledge.relations)
      } else if (editingRelId) {
        const knowledge = await updateKnowledgeRelation(editingRelId, { type, members: editMembers.map((m) => ({ ...m })) })
        setRelationObjects(knowledge.relation_objects)
        setRelations(knowledge.relations)
      }
    } catch (e) {
      alert(`操作失败：${e instanceof Error ? e.message : e}`)
    }
    setEditingRelId(null)
  }

  const handleSave = async () => {
    if (!document) return
    setSaving(true)
    try {
      const state = useReaderStore.getState()
      const saved = await saveDocument(document.id, state.tokens)
      useReaderStore.setState({
        tokens: saved.tokens,
        relation_objects: saved.relation_objects,
        relations: saved.relations,
      })
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
      useReaderStore.setState({
        tokens: [...updated.tokens],
        relation_objects: updated.relation_objects || [],
        relations: updated.relations || [],
      })
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

  const handleAIExplain = useCallback(async () => {
    if (!document || !tokenRelationObject) return
    setExplaining(true)
    try {
      const updated = await explainObject(document.id, tokenRelationObject.id)
      setDocument(updated)
    } catch (e) {
      alert(`AI解释失败：${e instanceof Error ? e.message : e}`)
    } finally {
      setExplaining(false)
    }
  }, [document, tokenRelationObject, setExplaining, setDocument])

  const resolveObjectDisplay = (obj: RelationObject): string => {
    if (obj.text) {
      const short = obj.text.slice(0, 20)
      return obj.text.length > 20 ? short + '…' : short
    }
    return obj.id.slice(0, 8)
  }

  const resolveRelationDisplay = (rel: Relation): string => {
    const typeLabel = isPredefined(rel.type) ? RELATION_LABELS[rel.type] || rel.type : rel.type
    const summary = rel.members
      .map((m) => {
        if (m.kind === 'object') {
          const obj = relationObjects.find((ro) => ro.id === m.id)
          return obj ? resolveObjectDisplay(obj) : '?'
        }
        const r = relations.find((rr) => rr.id === m.id)
        if (r) {
          const tl = isPredefined(r.type) ? RELATION_LABELS[r.type] || r.type : r.type
          return `[${tl}]`
        }
        return '?'
      })
      .join(' → ')
    return `${typeLabel}: ${summary}`
  }

  const resolveMemberDisplay = (m: RelationMember): string => {
    if (m.kind === 'object') {
      const obj = relationObjects.find((ro) => ro.id === m.id)
      return obj ? resolveObjectDisplay(obj) : '?'
    }
    const rel = relations.find((r) => r.id === m.id)
    if (rel) {
      const tl = isPredefined(rel.type) ? RELATION_LABELS[rel.type] || rel.type : rel.type
      return `[关系:${tl}]`
    }
    return '?'
  }

  const isPredefined = (t: string) => (RELATION_TYPES as readonly string[]).includes(t)

  const TAB_LABELS: Record<OpTab, string> = { meaning: '拆分含义', char: '分词拆分', merge: '合并相邻' }

  const closePanel = () => {
    if (isLayerView) setLayerSelectedToken(null)
    else setSelectedToken(null)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="font-medium text-lg truncate flex-1">
          {isLayerView && <span className="text-xs text-gray-400 mr-1">摘要</span>}
          <span className="text-gray-400">「</span>
          {token.text}
          <span className="text-gray-400">」</span>
        </div>
        <button
          onClick={closePanel}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-2 shrink-0"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Style type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">样式类型</label>
          <select
            value={styleType}
            onChange={(e) => {
              setStyleType(e.target.value)
              updateToken(token.id, { style_type: e.target.value })
            }}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            {STYLE_TYPES.map((t) => (
              <option key={t} value={t}>{STYLE_LABELS[t]}</option>
            ))}
          </select>
        </div>

        {/* AI Explain button */}
        {tokenRelationObject && (
          <div>
            <button
              onClick={handleAIExplain}
              disabled={explaining}
              className="w-full px-3 py-2 text-xs bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              {explaining ? 'AI解释中...' : '🤖 AI 解释'}
            </button>
          </div>
        )}

        {/* Relation Objects */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">关系对象</span>
            <button
              onClick={() => setShowTextObj(!showTextObj)}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              + 文本对象
            </button>
          </div>

          {showTextObj && (
            <div className="border rounded p-2 bg-gray-50 space-y-2">
              <input
                value={textObjValue}
                onChange={(e) => setTextObjValue(e.target.value)}
                className="w-full border rounded px-2 py-1 text-xs"
                placeholder="输入文本…"
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddTextObject() }}
              />
              <div className="flex gap-2">
                <button onClick={() => setShowTextObj(false)} className="flex-1 px-2 py-1 text-xs border rounded hover:bg-gray-100">取消</button>
                <button onClick={handleAddTextObject} disabled={!textObjValue.trim()} className="flex-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">添加</button>
              </div>
            </div>
          )}

          {tokenRelationObject ? (
            <div className="border rounded p-2 text-xs flex items-center justify-between gap-2">
              <span className="text-gray-500">
                「{token.text}」
              </span>
              <button onClick={handleDeleteTokenObject} className="text-gray-400 hover:text-red-500 shrink-0">✕</button>
            </div>
          ) : (
            <button onClick={handleConvertToken} className="w-full px-3 py-2 text-xs border rounded bg-blue-50 text-blue-700 hover:bg-blue-100">
              将「{token.text}」转为关系对象
            </button>
          )}

          {tokenRelationObject && relationObjects
            .filter((ro) => ro.id !== tokenRelationObject.id && relatedObjectIds.has(ro.id) && ro.kind !== 'document')
            .map((ro) => {
              return (
                <div key={ro.id} className="border rounded p-2 text-xs flex items-center justify-between gap-2">
                  <span className="text-gray-500 truncate">
                    {resolveObjectDisplay(ro)}
                  </span>
                </div>
              )
            })}

          {relationObjects
            .filter((ro) => ro.kind !== 'document' && (tokenRelationObject ? relatedObjectIds.has(ro.id) && ro.id !== tokenRelationObject.id : true))
            .map((ro) => {
              return (
                <div key={ro.id} className="border rounded p-2 text-xs flex items-center justify-between gap-2">
                  <span className="text-gray-500 truncate">
                    <span className="text-gray-400">文本 </span>
                    {resolveObjectDisplay(ro)}
                  </span>
                  <button
                    onClick={async () => {
                      try {
                        const knowledge = await deleteKnowledgeObject(ro.id)
                        setRelationObjects(knowledge.relation_objects)
                        setRelations(knowledge.relations)
                      } catch (e) {
                        alert(`删除失败：${e instanceof Error ? e.message : e}`)
                      }
                    }}
                    className="text-gray-400 hover:text-red-500 shrink-0"
                  >✕</button>
                </div>
              )
            })}
        </div>

        <div className="border-t" />

        {/* Relations */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">关系</span>
            <button
              onClick={startCreating}
              disabled={!tokenRelationObject && relationObjects.filter((ro) => ro.kind !== 'document').length === 0}
              className="text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-300"
            >
              + 添加关系
            </button>
          </div>

          {tokenRelations.map((rel) => (
            <div key={rel.id} className={`border rounded p-2 text-xs ${editingRelId === rel.id ? 'ring-2 ring-blue-300' : ''}`}>
              {editingRelId === rel.id ? null : (
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 truncate flex-1 min-w-0">
                    <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-700 shrink-0">
                      {isPredefined(rel.type) ? RELATION_LABELS[rel.type] || rel.type : rel.type}
                    </span>
                    <span className="text-gray-400 shrink-0">:</span>
                    <span className="text-gray-500 truncate">
                      {rel.members.map((m, i) => (i > 0 ? ' → ' : '') + resolveMemberDisplay(m))}
                    </span>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <button onClick={() => startEditing(rel)} className="text-gray-400 hover:text-gray-600">编辑</button>
                    <button onClick={async () => {
                      try {
                        const knowledge = await deleteKnowledgeRelation(rel.id)
                        setRelationObjects(knowledge.relation_objects)
                        setRelations(knowledge.relations)
                      } catch (e) {
                        alert(`删除失败：${e instanceof Error ? e.message : e}`)
                      }
                    }} className="text-red-400 hover:text-red-600">删除</button>
                  </div>
                </div>
              )}
            </div>
          ))}

          {editingRelId && (
            <div className="border rounded p-3 space-y-3 bg-gray-50">
              <div>
                <label className="block text-xs text-gray-500 mb-1">类型</label>
                <select
                  value={isPredefined(editType) ? editType : '__custom__'}
                  onChange={(e) => {
                    const v = e.target.value
                    setEditType(v === '__custom__' ? '' : v)
                    if (v !== '__custom__') setEditCustomType('')
                  }}
                  className="w-full border rounded px-2 py-1.5 text-xs"
                >
                  <option value="">选择类型…</option>
                  {RELATION_TYPES.map((t) => (
                    <option key={t} value={t}>{RELATION_LABELS[t]}</option>
                  ))}
                  <option value="__custom__">自定义…</option>
                </select>
                {(!editType || editType === '__custom__') && (
                  <input
                    value={editCustomType}
                    onChange={(e) => { setEditCustomType(e.target.value); setEditType('__custom__') }}
                    placeholder="输入自定义类型"
                    className="w-full border rounded px-2 py-1.5 text-xs mt-1"
                  />
                )}
              </div>

              <div>
                <label className="block text-xs text-gray-500 mb-1">选择对象（已选 {editMembers.length}）</label>
                <div className="max-h-48 overflow-y-auto border rounded bg-white divide-y">
                  {relationObjects.map((ro) => (
                    <label key={`obj:${ro.id}`} className="flex items-center gap-2 px-2 py-1.5 text-xs hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={isMemberSelected('object', ro.id)} onChange={() => toggleMemberSelection('object', ro.id)} />
                      <span className="text-gray-400 shrink-0">{ro.kind === 'document' ? '文档' : '对象'}</span>
                      <span className="text-gray-700 truncate">{resolveObjectDisplay(ro)}</span>
                    </label>
                  ))}
                  {relations.filter((r) => r.id !== editingRelId).map((rel) => (
                    <label key={`rel:${rel.id}`} className="flex items-center gap-2 px-2 py-1.5 text-xs hover:bg-gray-50 cursor-pointer">
                      <input type="checkbox" checked={isMemberSelected('relation', rel.id)} onChange={() => toggleMemberSelection('relation', rel.id)} />
                      <span className="text-gray-400 shrink-0">关系</span>
                      <span className="text-gray-700 truncate">{resolveRelationDisplay(rel)}</span>
                    </label>
                  ))}
                  {relationObjects.length === 0 && relations.length === 0 && (
                    <div className="px-2 py-3 text-xs text-gray-400 text-center">暂无关系对象或关系，请先创建</div>
                  )}
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={cancelEditing} className="flex-1 px-3 py-1.5 text-xs border rounded hover:bg-gray-100">取消</button>
                <button
                  onClick={commitEditing}
                  disabled={!(isPredefined(editType) ? editType : editCustomType.trim()) || editMembers.length < 2}
                  className="flex-1 px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {editingRelId === 'new' ? '添加' : '保存'}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="border-t" />

        {/* Operations */}
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wide">操作</div>

        <div className="flex border rounded overflow-hidden">
          {(Object.keys(TAB_LABELS) as OpTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setOpTab(tab)}
              className={`flex-1 px-2 py-1.5 text-xs transition-colors ${opTab === tab ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        {opTab === 'meaning' && (
          <div className="border rounded p-3">
            {token.start_offsets.length <= 1 ? (
              <div className="text-xs text-gray-400">该分词仅出现一次，无需拆分</div>
            ) : (
              <div>
                <p className="text-xs text-gray-600 mb-2">勾选要移走的出现位置（{token.start_offsets.length} 处）：</p>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {token.start_offsets.map((off) => {
                    const ctxStart = Math.max(0, off - 8)
                    const ctxEnd = Math.min(document?.original_text.length || 0, off + token.text.length + 8)
                    const ctx = document?.original_text.slice(ctxStart, ctxEnd) || ''
                    const innerStart = off - ctxStart
                    const innerEnd = innerStart + token.text.length
                    return (
                      <label key={off} className="flex items-center gap-2 text-xs cursor-pointer hover:bg-orange-100 px-1 py-0.5 rounded">
                        <input type="checkbox" checked={checkedOffsets.has(off)} onChange={() => toggleOffset(off)} />
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
                  <button onClick={() => setCheckedOffsets(new Set())} className="px-3 py-1 text-xs border rounded hover:bg-gray-50">取消</button>
                  <button onClick={handleSplitMeaning} disabled={checkedOffsets.size === 0 || checkedOffsets.size >= token.start_offsets.length} className="px-3 py-1 text-xs bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50">确认拆分</button>
                </div>
              </div>
            )}
          </div>
        )}

        {opTab === 'char' && (
          <div className="border rounded p-3">
            <div className="flex items-center flex-wrap justify-center gap-0 mb-2 py-2 bg-gray-50 rounded text-base">
              {chars.map((ch, i) => (
                <span key={i}>
                  {i > 0 && (
                    <button onClick={() => setCharSplitPos(i)} className={`inline-block w-1.5 h-6 mx-0.5 rounded-sm transition-colors cursor-pointer ${charSplitPos === i ? 'bg-blue-500' : 'bg-gray-300 hover:bg-blue-300'}`} />
                  )}
                  <span className="inline-block px-0.5">{ch}</span>
                </span>
              ))}
            </div>
            <button onClick={handleCharSplit} disabled={charSplitPos === null} className="w-full px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">确认拆分</button>
          </div>
        )}

        {opTab === 'merge' && (
          <div className="border rounded p-3 space-y-2">
            {adjacentGroups.length === 0 ? (
              <div className="text-xs text-gray-400">无可合并的相邻分词</div>
            ) : (
              adjacentGroups.map((g) => (
                <div key={`${g.direction}:${g.text}`} className="flex items-center justify-between gap-2 p-2 border rounded text-xs">
                  <span className="text-gray-500 truncate">
                    {g.direction === 'prev' ? '← 合并「' : '合并→「'}
                    <span className="font-medium text-gray-700">{g.text}</span>
                    」{g.count > 1 && <span>（{g.count}处）</span>}
                  </span>
                  <button onClick={() => handleMergeGroup([...g.ids])} className="px-2 py-0.5 bg-green-600 text-white rounded hover:bg-green-700 shrink-0">合并</button>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex gap-3 p-4 border-t shrink-0">
        <button onClick={closePanel} className="flex-1 px-4 py-2 text-sm border rounded hover:bg-gray-50">关闭</button>
        <button onClick={handleSave} disabled={saving} className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {saving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  )

  function toggleOffset(off: number) {
    setCheckedOffsets((prev) => {
      const next = new Set(prev)
      if (next.has(off)) next.delete(off); else next.add(off)
      return next
    })
  }
}

function RelationOverview() {
  const document = useReaderStore((s) => s.document)
  const tokens = useReaderStore((s) => s.tokens)
  const relationObjects = useReaderStore((s) => s.relation_objects)
  const relations = useReaderStore((s) => s.relations)
  const setSelectedToken = useReaderStore((s) => s.setSelectedToken)
  const isPredefined = (t: string) => (RELATION_TYPES as readonly string[]).includes(t)

  const docRelations = useMemo(() => {
    if (!document) return relations.filter((r) => r.type !== 'belongs_to')
    const docId = document.id
    const docObj = relationObjects.find((ro) => ro.kind === 'document' && ro.metadata?.document_id === docId)
    if (!docObj) return []
    const belongsToObjIds = new Set<string>()
    for (const rel of relations) {
      if (rel.type === 'belongs_to') {
        const members = rel.members
        if (members.length >= 2 && members[1].id === docObj.id) {
          belongsToObjIds.add(members[0].id)
        }
      }
    }
    return relations.filter((rel) =>
      rel.type !== 'belongs_to' &&
      rel.members.some((m) => m.kind === 'object' && belongsToObjIds.has(m.id))
    )
  }, [relations, relationObjects, document])

  const resolveObjectDisplay = (obj: RelationObject, tkns: Token[]): string => {
    if (obj.text) {
      const short = obj.text.slice(0, 16)
      return obj.text.length > 16 ? short + '…' : short
    }
    return obj.id.slice(0, 8)
  }

  const resolveMemberDisplay = (m: RelationMember, ros: RelationObject[], rels: Relation[], tkns: Token[]): string => {
    if (m.kind === 'object') {
      const obj = ros.find((ro) => ro.id === m.id)
      return obj ? resolveObjectDisplay(obj, tkns) : '?'
    }
    const rel = rels.find((r) => r.id === m.id)
    if (rel) {
      const tl = isPredefined(rel.type) ? RELATION_LABELS[rel.type] || rel.type : rel.type
      return `[${tl}]`
    }
    return '?'
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="font-medium text-lg">关系概览</div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {docRelations.length === 0 ? (
          <div className="text-sm text-gray-400 text-center mt-8">
            暂无关系
            <br />
            <span className="text-xs">点击文中分词，将其转为关系对象后创建</span>
          </div>
        ) : (
          <div className="space-y-2">
            {docRelations.map((rel) => (
              <div key={rel.id} className="border rounded p-2.5 text-xs hover:bg-gray-50 transition-colors">
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-700 font-medium">
                    {isPredefined(rel.type) ? RELATION_LABELS[rel.type] || rel.type : rel.type}
                  </span>
                  <span className="text-gray-400">({rel.members.length} 个对象)</span>
                </div>
                <div className="text-gray-500 space-x-1">
                  {rel.members.map((m, i) => (
                    <span key={i}>
                      {i > 0 && <span className="text-gray-300 mx-0.5">→</span>}
                      <span
                        className={`cursor-pointer hover:text-blue-600 ${m.kind === 'relation' ? 'text-purple-600' : ''}`}
                        onClick={() => {
                          if (m.kind === 'object') {
                            const obj = relationObjects.find((ro) => ro.id === m.id)
                            if (obj?.text) {
                              const matchingToken = tokens.find((t) => t.text === obj.text)
                              if (matchingToken) setSelectedToken(matchingToken.id)
                            }
                          }
                        }}
                      >
                        {resolveMemberDisplay(m, relationObjects, relations, tokens)}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
