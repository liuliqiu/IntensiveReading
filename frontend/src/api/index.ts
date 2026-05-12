import type { Document, DocumentListItem, Token } from '../types'

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail || res.statusText
    throw new Error(detail)
  }
  return res.json()
}

export async function fetchDocuments(): Promise<DocumentListItem[]> {
  return request('/documents')
}

export async function fetchDocument(id: string): Promise<Document> {
  return request(`/documents/${id}`)
}

export async function createDocument(
  title: string,
  originalText: string
): Promise<Document> {
  return request('/documents', {
    method: 'POST',
    body: JSON.stringify({ title, original_text: originalText }),
  })
}

export async function saveTokens(
  documentId: string,
  tokens: Token[]
): Promise<Token[]> {
  return request(`/documents/${documentId}/tokens`, {
    method: 'PUT',
    body: JSON.stringify({ tokens }),
  })
}

export async function updateToken(
  tokenId: string,
  data: Partial<Token>
): Promise<Token> {
  return request(`/tokens/${tokenId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function splitTokenByMeaning(
  tokenId: string,
  offsetsToMove: number[]
): Promise<Document> {
  return request(`/tokens/${tokenId}/split`, {
    method: 'POST',
    body: JSON.stringify({ offsets_to_move: offsetsToMove }),
  })
}
