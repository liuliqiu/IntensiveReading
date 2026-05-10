import { useState } from 'react'
import type { Token } from '../types'
import { STYLE_TYPES, STYLE_LABELS } from '../types'

interface Props {
  token: Token
  allTokens: Token[]
  onSave: (data: Partial<Token>) => void
  onClose: () => void
}

export default function ReferentEditor({ token, allTokens, onSave, onClose }: Props) {
  const [refType, setRefType] = useState<string>(token.ref_type || '')
  const [targetId, setTargetId] = useState(token.ref_target_token_id || '')
  const [url, setUrl] = useState(token.ref_url || '')
  const [explanation, setExplanation] = useState(token.ref_explanation || '')
  const [styleType, setStyleType] = useState(token.style_type)

  const handleSave = () => {
    onSave({
      style_type: styleType,
      ref_type: (refType || null) as Token['ref_type'],
      ref_target_token_id: refType === 'internal' ? targetId : null,
      ref_url: refType === 'external' ? url : null,
      ref_explanation: refType === 'note' ? explanation : null,
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md max-h-[80vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">
          编辑分词「{token.text}」
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              样式类型
            </label>
            <select
              value={styleType}
              onChange={(e) => setStyleType(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              {STYLE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {STYLE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              指代类型
            </label>
            <select
              value={refType}
              onChange={(e) => {
                setRefType(e.target.value)
                setTargetId('')
                setUrl('')
                setExplanation('')
              }}
              className="w-full border rounded px-3 py-2 text-sm"
            >
              <option value="">无指代</option>
              <option value="internal">文中指代</option>
              <option value="external">外部链接</option>
              <option value="note">文字注释</option>
            </select>
          </div>

          {refType === 'internal' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                指代目标（文中分词）
              </label>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              >
                <option value="">选择目标...</option>
                {allTokens
                  .filter((t) => t.id !== token.id)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.text}
                    </option>
                  ))}
              </select>
            </div>
          )}

          {refType === 'external' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                外部 URL
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://..."
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
          )}

          {refType === 'note' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                解释文字
              </label>
              <textarea
                value={explanation}
                onChange={(e) => setExplanation(e.target.value)}
                rows={3}
                className="w-full border rounded px-3 py-2 text-sm resize-y"
              />
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
