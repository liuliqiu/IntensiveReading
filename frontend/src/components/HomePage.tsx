import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchDocuments, createDocument } from '../api'
import type { DocumentListItem } from '../types'

export default function HomePage() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState<DocumentListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchDocuments()
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async () => {
    if (!title.trim() || !text.trim()) return
    setCreating(true)
    try {
      const doc = await createDocument(title.trim(), text.trim())
      navigate(`/reader/${doc.id}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">精读</h1>

      <div className="mb-10 p-6 border rounded-lg bg-white shadow-sm">
        <h2 className="text-lg font-semibold mb-4">上传新文本</h2>
        <input
          type="text"
          placeholder="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full border rounded px-3 py-2 mb-3 text-sm"
        />
        <textarea
          placeholder="输入需要精读的长文本..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          className="w-full border rounded px-3 py-2 mb-3 text-sm resize-y"
        />
        <button
          onClick={handleCreate}
          disabled={creating || !title.trim() || !text.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? '分词中...' : '提交并分词'}
        </button>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-4">已保存的文档</h2>
        {loading && <p className="text-gray-500 text-sm">加载中...</p>}
        {!loading && docs.length === 0 && (
          <p className="text-gray-500 text-sm">暂无文档</p>
        )}
        <ul className="space-y-2">
          {docs.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between p-3 border rounded hover:bg-gray-50 cursor-pointer"
              onClick={() => navigate(`/reader/${d.id}`)}
            >
              <div>
                <div className="font-medium text-sm">{d.title}</div>
                <div className="text-xs text-gray-500">
                  {d.token_count} 个分词
                </div>
              </div>
              <div className="text-xs text-gray-400">
                {new Date(d.updated_at).toLocaleString('zh-CN')}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
