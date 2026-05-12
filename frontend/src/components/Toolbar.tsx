import { useNavigate } from 'react-router-dom'
import { useReaderStore } from '../store'

export default function Toolbar() {
  const navigate = useNavigate()
  const { document, tokens } = useReaderStore()

  return (
    <div className="flex items-center gap-3 p-3 border-b bg-white shrink-0">
      <button
        onClick={() => navigate('/')}
        className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1"
      >
        ← 返回
      </button>

      <div className="flex-1 text-sm font-medium text-gray-700 truncate">
        {document?.title}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">
          {tokens.length} 个分词
        </span>
      </div>
    </div>
  )
}
