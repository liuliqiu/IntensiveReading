import { create } from 'zustand'
import type { Document, EditMode, Token } from '../types'

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

interface ReaderState {
  document: Document | null
  tokens: Token[]
  editMode: EditMode
  hoveredTokenId: string | null
  selectedTokenId: string | null
  loading: boolean
  saving: boolean
  error: string | null

  setDocument: (doc: Document) => void
  setTokens: (tokens: Token[]) => void
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
  reset: () => void
}

export const useReaderStore = create<ReaderState>((set) => ({
  document: null,
  tokens: [],
  editMode: 'view',
  hoveredTokenId: null,
  selectedTokenId: null,
  loading: false,
  saving: false,
  error: null,

  setDocument: (doc) => set({ document: doc, tokens: [...doc.tokens] }),

  setTokens: (tokens) => set({ tokens }),

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
        ...token,
        id: crypto.randomUUID(),
        start_offsets: [startOffset],
        text: token.text.slice(0, splitPos),
        ref_type: null,
        ref_target_token_id: null,
        ref_url: null,
        ref_explanation: null,
      }
      const tokenB: Token = {
        ...token,
        id: crypto.randomUUID(),
        start_offsets: [startOffset + splitPos],
        text: token.text.slice(splitPos),
        ref_type: null,
        ref_target_token_id: null,
        ref_url: null,
        ref_explanation: null,
      }

      const insertAt = remaining.length === 0 ? idx : idx + 1
      newTokens.splice(insertAt, 0, tokenA, tokenB)

      return { tokens: newTokens, selectedTokenId: null }
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
          ...token,
          id: i === 0 ? jumpId : crypto.randomUUID(),
          start_offsets: [off],
          text: token.text.slice(0, splitPos),
          ref_type: null,
          ref_target_token_id: null,
          ref_url: null,
          ref_explanation: null,
        })
        newTokens.push({
          ...token,
          id: crypto.randomUUID(),
          start_offsets: [off + splitPos],
          text: token.text.slice(splitPos),
          ref_type: null,
          ref_target_token_id: null,
          ref_url: null,
          ref_explanation: null,
        })
      }

      return { tokens: mergeTokensByText(newTokens, jumpId), selectedTokenId: jumpId }
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
        ref_type: null,
        ref_target_token_id: null,
        ref_url: null,
        ref_explanation: null,
      }

      const insertAt = idxA < idxB
        ? (remA.length === 0 ? idxA : newTokens.findIndex((t) => t.id === idA) + 1)
        : 0
      newTokens.splice(insertAt, 0, merged)

      return { tokens: newTokens, selectedTokenId: null }
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
          ref_type: null,
          ref_target_token_id: null,
          ref_url: null,
          ref_explanation: null,
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

      return { tokens: mergeTokensByText(newTokens, jumpId), selectedTokenId: jumpId }
    }),

  reset: () =>
    set({
      document: null,
      tokens: [],
      editMode: 'view',
      hoveredTokenId: null,
      selectedTokenId: null,
      loading: false,
      saving: false,
      error: null,
    }),
}))
