import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useReaderStore } from '../store'
import { fetchDocument } from '../api'
import Toolbar from './Toolbar'
import TextCanvas from './TextCanvas'
import SummaryCanvas from './SummaryCanvas'
import TokenActionPanel from './TokenActionPanel'

export default function ReaderPage() {
  const { id } = useParams<{ id: string }>()
  const document = useReaderStore((s) => s.document)
  const tokens = useReaderStore((s) => s.tokens)
  const loading = useReaderStore((s) => s.loading)
  const error = useReaderStore((s) => s.error)
  const viewMode = useReaderStore((s) => s.viewMode)
  const setDocument = useReaderStore((s) => s.setDocument)
  const setLoading = useReaderStore((s) => s.setLoading)
  const setError = useReaderStore((s) => s.setError)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    fetchDocument(id)
      .then((doc) => setDocument(doc))
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [id, setDocument, setLoading, setError])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        加载中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-500">
        {error}
      </div>
    )
  }

  if (!document) return null

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      <div className="flex-1 flex flex-col overflow-hidden transition-all duration-300">
        <Toolbar />
        {viewMode === 'layer' ? (
          <div className="flex-1 overflow-y-auto">
            <SummaryCanvas />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <TextCanvas tokens={tokens} canvas="document" />
          </div>
        )}
      </div>
      <div className="w-80 shrink-0 bg-white border-l shadow-lg overflow-hidden flex flex-col transition-all duration-300">
        <TokenActionPanel />
      </div>
    </div>
  )
}
