import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchDocuments, processDocument, scrapeUrl } from '../api'
import type { DocumentListItem } from '../types'

type InputMode = 'manual' | 'url'

export default function HomePage() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState<DocumentListItem[]>([])
  const [loading, setLoading] = useState(true)

  const [mode, setMode] = useState<InputMode>('manual')

  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [creating, setCreating] = useState(false)

  const [url, setUrl] = useState('')
  const [scraping, setScraping] = useState(false)

  useEffect(() => {
    fetchDocuments()
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const sourceUrlRef = useRef('')

  const handleCreate = async () => {
    if (!title.trim() || !text.trim()) return
    setCreating(true)
    try {
      const result = await processDocument(title.trim(), text.trim(), sourceUrlRef.current)
      navigate(`/reader/${result.document.id}`, { state: result })
    } finally {
      setCreating(false)
    }
  }

  const handleScrape = async () => {
    if (!url.trim()) return
    setScraping(true)
    try {
      const result = await scrapeUrl(url.trim())
      setTitle(result.title)
      setText(result.content)
      sourceUrlRef.current = url.trim()
    } catch (e) {
      alert(`抓取失败：${e instanceof Error ? e.message : e}`)
    } finally {
      setScraping(false)
    }
  }

  const canSubmit = title.trim() && text.trim()

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">精读</h1>

      <div className="mb-10 p-6 border rounded-lg bg-white shadow-sm">
        <h2 className="text-lg font-semibold mb-4">上传新文本</h2>

        <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
          <button
            onClick={() => setMode('manual')}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
              mode === 'manual'
                ? 'bg-white shadow text-gray-900 font-medium'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            手动输入
          </button>
          <button
            onClick={() => setMode('url')}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
              mode === 'url'
                ? 'bg-white shadow text-gray-900 font-medium'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            网页抓取
          </button>
        </div>

        {mode === 'url' && (
          <div className="flex gap-2 mb-3">
            <input
              type="url"
              placeholder="输入网页 URL（如 https://example.com/article）"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleScrape()}
              className="flex-1 border rounded px-3 py-2 text-sm"
            />
            <button
              onClick={handleScrape}
              disabled={scraping || !url.trim()}
              className="px-4 py-2 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50 shrink-0"
            >
              {scraping ? '抓取中...' : '抓取网页'}
            </button>
          </div>
        )}

        <input
          type="text"
          placeholder="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full border rounded px-3 py-2 mb-3 text-sm"
        />
        <textarea
          placeholder={mode === 'url' ? '抓取网页后自动填入正文...' : '输入需要精读的长文本...'}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          className="w-full border rounded px-3 py-2 mb-3 text-sm resize-y"
        />
        <button
          onClick={handleCreate}
          disabled={creating || !canSubmit}
          className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {creating ? '分析中...' : '提交并分析'}
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
