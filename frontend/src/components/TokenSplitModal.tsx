import { useState } from 'react'
import type { Token } from '../types'

interface Props {
  token: Token
  onSplit: (splitPos: number) => void
  onClose: () => void
}

export default function TokenSplitModal({ token, onSplit, onClose }: Props) {
  const [splitPos, setSplitPos] = useState<number | null>(null)
  const chars = [...token.text]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-3">拆分分词「{token.text}」</h3>
        <p className="text-sm text-gray-500 mb-4">
          点击两个字之间的间隙来确定拆分位置
        </p>

        <div className="flex items-center flex-wrap justify-center gap-0 mb-4 p-4 border rounded bg-gray-50 text-xl">
          {chars.map((ch, i) => (
            <span key={i}>
              {i > 0 && (
                <button
                  onClick={() => setSplitPos(i)}
                  className={`inline-block w-2 h-8 mx-0.5 rounded-sm transition-colors cursor-pointer
                    ${splitPos === i
                      ? 'bg-blue-500'
                      : 'bg-gray-300 hover:bg-blue-300'
                    }`}
                  title={`在「${chars[i - 1]}」和「${ch}」之间拆分`}
                />
              )}
              <span className="inline-block px-0.5">{ch}</span>
            </span>
          ))}
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={() => splitPos !== null && onSplit(splitPos)}
            disabled={splitPos === null}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            拆分
          </button>
        </div>
      </div>
    </div>
  )
}
