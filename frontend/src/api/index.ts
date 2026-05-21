import type { Document, DocumentListItem, Knowledge, TextLayer, Token } from '../types'

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

export interface ProcessDocumentResult {
  document: Document
  summary_layer: TextLayer
}

export async function processDocument(
  title: string,
  originalText: string
): Promise<ProcessDocumentResult> {
  return request('/documents/process', {
    method: 'POST',
    body: JSON.stringify({ title, original_text: originalText }),
  })
}

export async function saveDocument(
  documentId: string,
  tokens: Token[],
): Promise<Document> {
  return request(`/documents/${documentId}`, {
    method: 'PUT',
    body: JSON.stringify({ tokens }),
  })
}

export async function fetchKnowledge(): Promise<Knowledge> {
  return request('/knowledge')
}

export async function createKnowledgeObject(body: { token_id?: string | null; document_id?: string | null; text?: string | null; kind?: string }): Promise<Knowledge> {
  return request('/knowledge/objects', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteKnowledgeObject(objectId: string): Promise<Knowledge> {
  return request(`/knowledge/objects/${objectId}`, { method: 'DELETE' })
}

export async function createKnowledgeRelation(body: { type: string; members: { kind: string; id: string }[]; description?: string }): Promise<Knowledge> {
  return request('/knowledge/relations', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateKnowledgeRelation(relationId: string, body: { type?: string; members?: { kind: string; id: string }[]; description?: string }): Promise<Knowledge> {
  return request(`/knowledge/relations/${relationId}`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function deleteKnowledgeRelation(relationId: string): Promise<Knowledge> {
  return request(`/knowledge/relations/${relationId}`, { method: 'DELETE' })
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

export async function scrapeUrl(url: string): Promise<{ title: string; content: string }> {
  return request('/scrape', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
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
