import { create } from 'zustand'
import type { Document, EditMode, Relation, RelationObject, Token } from '../types'

function mergeTokensByText(tokens: Token[], keepId: string): Token[] {
  const groups = new Map<string, Token>()
  for (const t of tokens) {
    const existing = groups.get(t.text)
    if (existing) {
      existing.start_offsets.push(...t.start_offsets)
      if (t.id === keepId) existing.id = keepId
    } else {
      groups.set(t.text, { ...t })
    }
  }
  return [...groups.values()]
}

function cascadeStaleIds(
  relationObjects: RelationObject[],
  relations: Relation[],
  staleObjIds: Set<string>
): { relation_objects: RelationObject[]; relations: Relation[] } {
  const newROs = relationObjects.filter((ro) => !staleObjIds.has(ro.id))
  const staleIds = new Set<string>(staleObjIds)

  // Transitive closure: find all relations referencing stale entities
  while (true) {
    const newStale = new Set<string>()
    for (const r of relations) {
      if (staleIds.has(r.id)) continue
      if (r.members.some((m) => staleIds.has(m.id))) {
        newStale.add(r.id)
      }
    }
    if (newStale.size === 0) break
    for (const id of newStale) staleIds.add(id)
  }

  const newRelations = relations.filter((r) => !staleIds.has(r.id))
  return { relation_objects: newROs, relations: newRelations }
}

interface ReaderState {
  document: Document | null
  tokens: Token[]
  relation_objects: RelationObject[]
  relations: Relation[]
  editMode: EditMode
  hoveredTokenId: string | null
  selectedTokenId: string | null
  loading: boolean
  saving: boolean
  error: string | null

  setDocument: (doc: Document) => void
  setTokens: (tokens: Token[]) => void
  setRelationObjects: (ros: RelationObject[]) => void
  setRelations: (relations: Relation[]) => void
  setLoading: (v: boolean) => void
  setSaving: (v: boolean) => void
  setError: (e: string | null) => void
  setEditMode: (mode: EditMode) => void
  setHoveredToken: (id: string | null) => void
  setSelectedToken: (id: string | null) => void
  splitToken: (tokenId: string, startOffset: number, splitPos: number) => void
  splitTokenAll: (tokenId: string, splitPos: number) => void
  mergeTokens: (idA: string, offA: number, idB: string, offB: number) => void
  mergeAdjacentAll: (baseId: string, adjIds: string[]) => void
  updateToken: (id: string, data: Partial<Token>) => void
  addRelationObject: (ro: RelationObject) => void
  deleteRelationObject: (id: string) => void
  addRelation: (r: Relation) => void
  updateRelation: (id: string, data: Partial<Relation>) => void
  deleteRelation: (id: string) => void
  reset: () => void
}

export const useReaderStore = create<ReaderState>((set) => ({
  document: null,
  tokens: [],
  relation_objects: [],
  relations: [],
  editMode: 'view',
  hoveredTokenId: null,
  selectedTokenId: null,
  loading: false,
  saving: false,
  error: null,

  setDocument: (doc) => set({ document: doc, tokens: [...doc.tokens], relation_objects: [...doc.relation_objects], relations: [...doc.relations] }),

  setTokens: (tokens) => set({ tokens }),
  setRelationObjects: (relation_objects) => set({ relation_objects }),
  setRelations: (relations) => set({ relations }),

  setLoading: (v) => set({ loading: v }),
  setSaving: (v) => set({ saving: v }),
  setError: (e) => set({ error: e }),

  setEditMode: (mode) =>
    set({ editMode: mode, selectedTokenId: null, hoveredTokenId: null }),

  setHoveredToken: (id) => set({ hoveredTokenId: id }),

  setSelectedToken: (id) => set({ selectedTokenId: id }),

  splitToken: (tokenId, startOffset, splitPos) =>
    set((state) => {
      const idx = state.tokens.findIndex((t) => t.id === tokenId)
      if (idx === -1) return state
      const token = state.tokens[idx]
      if (splitPos <= 0 || splitPos >= token.text.length) return state

      const newTokens = [...state.tokens]
      const remaining = token.start_offsets.filter((o) => o !== startOffset)

      if (remaining.length === 0) {
        newTokens.splice(idx, 1)
      } else {
        newTokens[idx] = { ...token, start_offsets: remaining }
      }

      const tokenA: Token = {
        id: crypto.randomUUID(),
        start_offsets: [startOffset],
        text: token.text.slice(0, splitPos),
        style_type: 'default',
      }
      const tokenB: Token = {
        id: crypto.randomUUID(),
        start_offsets: [startOffset + splitPos],
        text: token.text.slice(splitPos),
        style_type: 'default',
      }

      const insertAt = remaining.length === 0 ? idx : idx + 1
      newTokens.splice(insertAt, 0, tokenA, tokenB)

      const { relation_objects: newROs, relations: newRels } = cascadeStaleIds(
        state.relation_objects, state.relations,
        new Set(state.relation_objects.filter((ro) => ro.token_id === tokenId).map((ro) => ro.id))
      )
      return {
        tokens: newTokens,
        relation_objects: newROs,
        relations: newRels,
        selectedTokenId: null,
      }
    }),

  splitTokenAll: (tokenId, splitPos) =>
    set((state) => {
      const token = state.tokens.find((t) => t.id === tokenId)
      if (!token) return state
      if (splitPos <= 0 || splitPos >= token.text.length) return state

      const offsets = [...token.start_offsets]
      const newTokens = state.tokens.filter((t) => t.id !== tokenId)
      const jumpId = crypto.randomUUID()

      for (let i = 0; i < offsets.length; i++) {
        const off = offsets[i]
        newTokens.push({
          id: i === 0 ? jumpId : crypto.randomUUID(),
          start_offsets: [off],
          text: token.text.slice(0, splitPos),
          style_type: 'default',
        })
        newTokens.push({
          id: crypto.randomUUID(),
          start_offsets: [off + splitPos],
          text: token.text.slice(splitPos),
          style_type: 'default',
        })
      }

      const { relation_objects: newROs2, relations: newRels2 } = cascadeStaleIds(
        state.relation_objects, state.relations,
        new Set(state.relation_objects.filter((ro) => ro.token_id === tokenId).map((ro) => ro.id))
      )
      return {
        tokens: mergeTokensByText(newTokens, jumpId),
        relation_objects: newROs2,
        relations: newRels2,
        selectedTokenId: jumpId,
      }
    }),

  mergeTokens: (idA, offA, idB, offB) =>
    set((state) => {
      const idxA = state.tokens.findIndex((t) => t.id === idA)
      const idxB = state.tokens.findIndex((t) => t.id === idB)
      if (idxA === -1 || idxB === -1) return state

      const tokenA = state.tokens[idxA]
      const tokenB = state.tokens[idxB]

      const newTokens = [...state.tokens]

      const remA = tokenA.start_offsets.filter((o) => o !== offA)
      const remB = tokenB.start_offsets.filter((o) => o !== offB)

      if (remA.length === 0) {
        newTokens.splice(idxA, 1)
      } else {
        newTokens[newTokens.findIndex((t) => t.id === idA)] = { ...tokenA, start_offsets: remA }
      }

      const bidx = newTokens.findIndex((t) => t.id === idB)
      if (bidx !== -1) {
        if (remB.length === 0) {
          newTokens.splice(bidx, 1)
        } else {
          newTokens[bidx] = { ...tokenB, start_offsets: remB }
        }
      }

      const merged: Token = {
        id: crypto.randomUUID(),
        start_offsets: [Math.min(offA, offB)],
        text: tokenA.text + tokenB.text,
        style_type: 'default',
      }

      const insertAt = idxA < idxB
        ? (remA.length === 0 ? idxA : newTokens.findIndex((t) => t.id === idA) + 1)
        : 0
      newTokens.splice(insertAt, 0, merged)

      const { relation_objects: newROs3, relations: newRels3 } = cascadeStaleIds(
        state.relation_objects, state.relations,
        new Set(state.relation_objects.filter((ro) => ro.token_id === idA || ro.token_id === idB).map((ro) => ro.id))
      )
      return {
        tokens: newTokens,
        relation_objects: newROs3,
        relations: newRels3,
        selectedTokenId: null,
      }
    }),

  updateToken: (id, data) =>
    set((state) => ({
      tokens: state.tokens.map((t) => (t.id === id ? { ...t, ...data } : t)),
    })),

  mergeAdjacentAll: (baseId, adjIds) =>
    set((state) => {
      const baseToken = state.tokens.find((t) => t.id === baseId)
      if (!baseToken) return state

      const adjTokenDatas = new Map<string, Token>()
      const adjOffMaps = new Map<string, Set<number>>()
      const adjIdsSet = new Set(adjIds)

      const allPairs: {
        baseOff: number
        adjOff: number
        adjId: string
        adjText: string
        adjFirst: boolean
      }[] = []

      for (const adjId of adjIds) {
        const adjToken = state.tokens.find((t) => t.id === adjId)
        if (!adjToken) continue
        adjTokenDatas.set(adjId, adjToken)
        adjOffMaps.set(adjId, new Set(adjToken.start_offsets))
        for (const baseOff of baseToken.start_offsets) {
          for (const adjOff of adjToken.start_offsets) {
            if (adjOff + adjToken.text.length === baseOff) {
              allPairs.push({ baseOff, adjOff, adjId, adjText: adjToken.text, adjFirst: true })
            } else if (baseOff + baseToken.text.length === adjOff) {
              allPairs.push({ baseOff, adjOff, adjId, adjText: adjToken.text, adjFirst: false })
            }
          }
        }
      }

      if (allPairs.length === 0) return state

      let newTokens = state.tokens.filter((t) => t.id !== baseId && !adjIdsSet.has(t.id))
      const baseOffs = new Set(baseToken.start_offsets)
      const jumpId = crypto.randomUUID()

      let isFirst = true
      for (const pair of allPairs) {
        baseOffs.delete(pair.baseOff)
        adjOffMaps.get(pair.adjId)?.delete(pair.adjOff)

        const mergedText = pair.adjFirst
          ? pair.adjText + baseToken.text
          : baseToken.text + pair.adjText
        const mergedOff = pair.adjFirst ? pair.adjOff : pair.baseOff

        newTokens.push({
          id: isFirst ? jumpId : crypto.randomUUID(),
          start_offsets: [mergedOff],
          text: mergedText,
          style_type: 'default',
        })
        isFirst = false
      }

      if (baseOffs.size > 0) {
        newTokens.push({ ...baseToken, start_offsets: [...baseOffs] })
      }

      for (const [adjId, offs] of adjOffMaps) {
        if (offs.size > 0) {
          const adjData = adjTokenDatas.get(adjId)
          if (adjData) {
            newTokens.push({ ...adjData, start_offsets: [...offs] })
          }
        }
      }

      const { relation_objects: newROs4, relations: newRels4 } = cascadeStaleIds(
        state.relation_objects, state.relations,
        new Set(state.relation_objects.filter((ro) => ro.token_id === baseId || (ro.token_id && adjIdsSet.has(ro.token_id))).map((ro) => ro.id))
      )
      return {
        tokens: mergeTokensByText(newTokens, jumpId),
        relation_objects: newROs4,
        relations: newRels4,
        selectedTokenId: jumpId,
      }
    }),

  addRelationObject: (ro) =>
    set((state) => ({ relation_objects: [...state.relation_objects, ro] })),

  deleteRelationObject: (id) =>
    set((state) => ({
      relation_objects: state.relation_objects.filter((ro) => ro.id !== id),
      relations: state.relations.filter((r) => !r.members.some((m) => m.id === id)),
    })),

  addRelation: (r) =>
    set((state) => ({ relations: [...state.relations, r] })),

  updateRelation: (id, data) =>
    set((state) => ({
      relations: state.relations.map((r) => (r.id === id ? { ...r, ...data } : r)),
    })),

  deleteRelation: (id) =>
    set((state) => {
      const refCount = state.relations.filter(
        (r) => r.id !== id && r.members.some((m) => m.id === id)
      ).length
      if (refCount > 0) {
        // Deletion prevented by caller; return unchanged state
        return state
      }
      return { relations: state.relations.filter((r) => r.id !== id) }
    }),

  reset: () =>
    set({
      document: null,
      tokens: [],
      relation_objects: [],
      relations: [],
      editMode: 'view',
      hoveredTokenId: null,
      selectedTokenId: null,
      loading: false,
      saving: false,
      error: null,
    }),
}))
