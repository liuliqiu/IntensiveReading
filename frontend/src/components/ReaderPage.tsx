import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useReaderStore } from '../store'
import { fetchDocument } from '../api'
import Toolbar from './Toolbar'
import TextCanvas from './TextCanvas'

export default function ReaderPage() {
  const { id } = useParams<{ id: string }>()
  const { document, tokens, loading, error, setDocument, setLoading, setError } =
    useReaderStore()

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
    <div className="min-h-screen bg-gray-50">
      <Toolbar />
      <TextCanvas tokens={tokens} />
    </div>
  )
}
