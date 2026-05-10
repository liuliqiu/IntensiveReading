import { create } from 'zustand'
import type { Document, EditMode, Token } from '../types'

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
  setLoading: (v: boolean) => void
  setSaving: (v: boolean) => void
  setError: (e: string | null) => void
  setEditMode: (mode: EditMode) => void
  setHoveredToken: (id: string | null) => void
  setSelectedToken: (id: string | null) => void
  splitToken: (tokenId: string, splitPos: number) => void
  mergeTokens: (tokenId: string) => void
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

  setLoading: (v) => set({ loading: v }),
  setSaving: (v) => set({ saving: v }),
  setError: (e) => set({ error: e }),

  setEditMode: (mode) =>
    set({ editMode: mode, selectedTokenId: null, hoveredTokenId: null }),

  setHoveredToken: (id) => set({ hoveredTokenId: id }),

  setSelectedToken: (id) => set({ selectedTokenId: id }),

  splitToken: (tokenId, splitPos) =>
    set((state) => {
      const idx = state.tokens.findIndex((t) => t.id === tokenId)
      if (idx === -1) return state
      const token = state.tokens[idx]
      if (splitPos <= 0 || splitPos >= token.text.length) return state

      const tokenA: Token = {
        ...token,
        id: crypto.randomUUID(),
        text: token.text.slice(0, splitPos),
      }
      const tokenB: Token = {
        ...token,
        id: crypto.randomUUID(),
        start_offset: token.start_offset + splitPos,
        text: token.text.slice(splitPos),
      }
      const newTokens = [...state.tokens]
      newTokens.splice(idx, 1, tokenA, tokenB)
      return { tokens: newTokens, selectedTokenId: null }
    }),

  mergeTokens: (tokenId) =>
    set((state) => {
      const idx = state.tokens.findIndex((t) => t.id === tokenId)
      if (idx === -1 || idx >= state.tokens.length - 1) return state
      const a = state.tokens[idx]
      const b = state.tokens[idx + 1]
      if (a.start_offset + a.text.length !== b.start_offset) return state

      const merged: Token = {
        ...a,
        id: crypto.randomUUID(),
        text: a.text + b.text,
        ref_type: null,
        ref_target_token_id: null,
        ref_url: null,
        ref_explanation: null,
      }
      const newTokens = [...state.tokens]
      newTokens.splice(idx, 2, merged)
      return { tokens: newTokens, selectedTokenId: null }
    }),

  updateToken: (id, data) =>
    set((state) => ({
      tokens: state.tokens.map((t) => (t.id === id ? { ...t, ...data } : t)),
    })),

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
