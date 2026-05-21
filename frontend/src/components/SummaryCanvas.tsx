import { useMemo } from 'react'
import type { Relation, RelationObject, RenderToken } from '../types'
import { RELATION_LABELS } from '../types'
import { useReaderStore } from '../store'
import TokenSpan from './TokenSpan'

export default function SummaryCanvas() {
  const layerTokens = useReaderStore((s) => s.layerTokens)
  const layerText = useReaderStore((s) => {
    const lid = s.selectedLayerId
    return s.layers.find((l) => l.id === lid)?.text || ''
  })
  const relationObjects = useReaderStore((s) => s.relation_objects)
  const relations = useReaderStore((s) => s.relations)
  const document = useReaderStore((s) => s.document)

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

  const { conceptObjects, conceptRelations } = useMemo(() => {
    const docId = document?.id
    const docObj = relationObjects.find((ro) => ro.kind === 'document' && ro.metadata?.document_id === docId)
    let belongsToIds = new Set<string>()
    if (docObj) {
      for (const rel of relations) {
        if (rel.type === 'belongs_to') {
          const members = rel.members
          if (members.length >= 2 && members[1].id === docObj.id) {
            belongsToIds.add(members[0].id)
          }
        }
      }
    }
    const conceptIds = new Set(
      relationObjects
        .filter((ro) => ro.kind === 'ai_concept' && belongsToIds.has(ro.id))
        .map((ro) => ro.id)
    )
    const objs = relationObjects.filter((ro) => conceptIds.has(ro.id))
    const rels = relations.filter((r) =>
      r.type !== 'belongs_to' && r.members.every((m) => conceptIds.has(m.id))
    )
    return { conceptObjects: objs, conceptRelations: rels }
  }, [relationObjects, relations, document])

  const groupedRelations = useMemo(() => {
    const groups = new Map<string, Relation[]>()
    for (const r of conceptRelations) {
      const list = groups.get(r.type) || []
      list.push(r)
      groups.set(r.type, list)
    }
    return [...groups.entries()]
  }, [conceptRelations])

  const objectMap = useMemo(() => {
    const map = new Map<string, RelationObject>()
    for (const o of conceptObjects) {
      map.set(o.id, o)
    }
    return map
  }, [conceptObjects])

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

      {conceptRelations.length > 0 && (
        <div className="max-w-3xl mx-auto mt-8 border-t pt-6">
          <h3 className="text-base font-medium text-gray-700 mb-4">概念关系分析</h3>
          {groupedRelations.map(([type, rels]) => (
            <div key={type} className="mb-4">
              <span className="inline-block px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded mb-2">
                {RELATION_LABELS[type] || type}
              </span>
              <ul className="space-y-2">
                {rels.map((r) => {
                  const src = objectMap.get(r.members[0]?.id)
                  const tgt = objectMap.get(r.members[1]?.id)
                  return (
                    <li key={r.id} className="text-sm text-gray-600">
                      <span className="font-medium text-gray-800">{src?.text || '?'}</span>
                      <span className="mx-2 text-xs text-purple-500">
                        {'→ ' + (r.description || RELATION_LABELS[r.type] || r.type) + ' →'}
                      </span>
                      <span className="font-medium text-gray-800">{tgt?.text || '?'}</span>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
      {conceptRelations.length === 0 && conceptObjects.length > 0 && (
        <div className="max-w-3xl mx-auto mt-8 border-t pt-6">
          <h3 className="text-base font-medium text-gray-700 mb-3">概念列表</h3>
          <ul className="space-y-1">
            {conceptObjects.map((o) => (
              <li key={o.id} className="text-sm text-gray-600">{o.text}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
