export interface Token {
  id: string
  start_offset: number
  text: string
  style_type: string
  ref_type: 'internal' | 'external' | 'note' | null
  ref_target_token_id: string | null
  ref_url: string | null
  ref_explanation: string | null
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

export const STYLE_TYPES = ['default', 'keyword', 'entity', 'unknown', 'punctuation', 'number'] as const

export const STYLE_LABELS: Record<string, string> = {
  default: '默认',
  keyword: '关键词',
  entity: '命名实体',
  unknown: '未知',
  punctuation: '标点符号',
  number: '数字',
}

export const STYLE_CLASSES: Record<string, string> = {
  default: 'border-b-2 border-b-gray-300',
  keyword: 'border-b-2 border-b-blue-400 bg-blue-50/50',
  entity: 'border-b-2 border-b-purple-400 bg-purple-50/50',
  unknown: 'border-b-2 border-b-red-400 bg-red-50/50',
  punctuation: 'border-b border-b-gray-200 text-gray-400',
  number: 'border-b-2 border-b-amber-400 bg-amber-50/30',
}
