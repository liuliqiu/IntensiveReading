export interface Token {
  id: string
  start_offsets: number[]
  text: string
  style_type: string
}

export interface RelationObject {
  id: string
  token_id?: string | null
  document_id?: string | null
  text?: string | null
  kind?: string | null
}

export interface Knowledge {
  relation_objects: RelationObject[]
  relations: Relation[]
}

export interface RelationMember {
  kind: 'object' | 'relation'
  id: string
}

export interface Relation {
  id: string
  type: string
  members: RelationMember[]
  description?: string
}

export interface RenderToken {
  token: Token
  start_offset: number
  key: string
}

export interface Document {
  id: string
  title: string
  original_text: string
  tokens: Token[]
  relation_objects: RelationObject[]
  relations: Relation[]
  created_at: string
  updated_at: string
}

export interface DocumentListItem {
  id: string
  title: string
  token_count: number
  created_at: string
  updated_at: string
}

export type EditMode = 'view' | 'split' | 'merge'

export const STYLE_TYPES = ['default', 'keyword', 'entity', 'unknown', 'punctuation', 'number', 'connector'] as const

export const STYLE_LABELS: Record<string, string> = {
  default: '默认',
  keyword: '关键词',
  entity: '命名实体',
  unknown: '未知',
  punctuation: '标点符号',
  number: '数字',
  connector: '连接词',
}

export const RELATION_TYPES = ['refers_to', 'belongs_to', 'links_to', 'annotates', 'explains'] as const

export const RELATION_LABELS: Record<string, string> = {
  refers_to: '指代',
  belongs_to: '属于',
  links_to: '链接',
  annotates: '注释',
  explains: '解释',
  causal: '因果',
  contains: '包含',
  contrasts: '对比',
  complements: '互补',
  precedes: '递进',
  describes: '描述',
}

export interface TextLayer {
  id: string
  document_id: string
  type: string
  text: string
  tokens: Token[]
  created_at: string
  updated_at: string
}

export const LAYER_TYPES = ['summary'] as const

export const LAYER_LABELS: Record<string, string> = {
  summary: '摘要',
}

export type ViewMode = 'original' | 'layer'
