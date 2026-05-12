export interface Token {
  id: string
  start_offsets: number[]
  text: string
  style_type: string
  ref_type: 'internal' | 'external' | 'note' | null
  ref_target_token_id: string | null
  ref_url: string | null
  ref_explanation: string | null
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
