import ReactMarkdown from 'react-markdown'
import { useReaderStore } from '../store'

export default function OriginFileCanvas() {
  const layer = useReaderStore((s) => s.originFileLayer)
  const filename = layer?.metadata?.filename || ''

  if (!layer) {
    return (
      <div className="p-8 text-center text-gray-400 text-sm">
        暂无源文件内容
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {filename && (
        <div className="text-xs text-gray-400 mb-4 pb-2 border-b">
          源文件：{filename}
        </div>
      )}
      <div className="prose prose-slate max-w-none
        prose-headings:font-semibold prose-headings:text-gray-900
        prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg
        prose-p:text-base prose-p:text-gray-700 prose-p:leading-relaxed
        prose-code:text-sm prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
        prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:text-sm
        prose-blockquote:border-l-4 prose-blockquote:border-blue-400 prose-blockquote:bg-blue-50 prose-blockquote:px-4 prose-blockquote:py-2
        prose-a:text-blue-600 prose-a:underline
        prose-strong:text-gray-900
        prose-ul:list-disc prose-ol:list-decimal
        prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:bg-gray-100 prose-th:px-3 prose-th:py-1
        prose-td:border prose-td:border-gray-300 prose-td:px-3 prose-td:py-1
        prose-hr:border-gray-300
        prose-img:max-w-full prose-img:rounded"
      >
        <ReactMarkdown>{layer.text}</ReactMarkdown>
      </div>
    </div>
  )
}
