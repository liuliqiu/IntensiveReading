import type { Document, DocumentListItem, Relation, RelationObject, TextLayer, Token } from '../types'

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

export async function saveDocument(
  documentId: string,
  tokens: Token[],
  relationObjects: RelationObject[],
  relations: Relation[]
): Promise<Document> {
  return request(`/documents/${documentId}`, {
    method: 'PUT',
    body: JSON.stringify({ tokens, relation_objects: relationObjects, relations }),
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

export async function createLayer(
  documentId: string,
  type: string
): Promise<TextLayer> {
  return request(`/documents/${documentId}/layers`, {
    method: 'POST',
    body: JSON.stringify({ type }),
  })
}

export async function fetchLayers(documentId: string): Promise<TextLayer[]> {
  return request(`/documents/${documentId}/layers`)
}

export async function fetchLayer(layerId: string): Promise<TextLayer> {
  return request(`/layers/${layerId}`)
}

export async function saveLayer(
  layerId: string,
  tokens: Token[]
): Promise<TextLayer> {
  return request(`/layers/${layerId}`, {
    method: 'PUT',
    body: JSON.stringify({ tokens }),
  })
}

export async function deleteLayer(layerId: string): Promise<void> {
  return request(`/layers/${layerId}`, { method: 'DELETE' })
}

export async function summarizeLayer(layerId: string): Promise<TextLayer> {
  return request(`/layers/${layerId}/summarize`, { method: 'POST' })
}

export async function analyzeConcepts(layerId: string): Promise<Document> {
  return request(`/layers/${layerId}/concepts`, { method: 'POST' })
}

export async function explainObject(
  documentId: string,
  objectId: string,
  contextWindow: number = 200
): Promise<Document> {
  return request(`/documents/${documentId}/objects/${objectId}/explain`, {
    method: 'POST',
    body: JSON.stringify({ context_window: contextWindow }),
  })
}
