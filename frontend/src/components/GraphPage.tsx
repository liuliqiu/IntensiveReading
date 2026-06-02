import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
} from 'd3-force'
import { fetchKnowledge } from '../api'
import { RELATION_LABELS } from '../types'
import type { Knowledge, Relation, RelationObject } from '../types'

interface GraphNode {
  id: string
  text: string | null
  kind: string | null
  x: number
  y: number
}

interface GraphEdge {
  id: string
  type: string
  description?: string
  source: string
  target: string
}

const KIND_COLORS: Record<string, string> = {
  document: '#2563eb',
  manual: '#16a34a',
  ai_explanation: '#9333ea',
  ai_concept: '#f97316',
  ai_concept_desc: '#6b7280',
}

const KIND_LABELS: Record<string, string> = {
  document: '文档',
  manual: '手动',
  ai_explanation: 'AI解释',
  ai_concept: 'AI概念',
  ai_concept_desc: 'AI概念描述',
}

function getNodeRadius(kind: string | null): number {
  return kind === 'document' ? 14 : 8
}

function getNodeColor(kind: string | null): string {
  return KIND_COLORS[kind ?? ''] ?? '#9ca3af'
}

function getNodeLabel(n: GraphNode): string {
  if (n.text) {
    return n.text.length > 12 ? n.text.slice(0, 12) + '…' : n.text
  }
  return n.id.slice(0, 8)
}

export default function GraphPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const focusNodeId = searchParams.get('focus')
  const svgRef = useRef<SVGSVGElement>(null)
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null)
  const focusAppliedRef = useRef<string | null>(null)
  const centeredRef = useRef(false)

  const [knowledge, setKnowledge] = useState<Knowledge | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showBelongsTo, setShowBelongsTo] = useState(false)
  const [selectedComponentIdx, setSelectedComponentIdx] = useState<number | null>(null)
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [tick, setTick] = useState(0)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  const [zoom, setZoom] = useState({ x: 0, y: 0, scale: 1 })
  const draggingRef = useRef(false)
  const dragStartRef = useRef({ x: 0, y: 0 })
  const nodeDragRef = useRef<string | null>(null)

  useEffect(() => {
    fetchKnowledge()
      .then(setKnowledge)
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    setSelectedComponentIdx(null)
  }, [showBelongsTo])

  const relationObjects = useMemo(() => knowledge?.relation_objects ?? [], [knowledge])
  const allRelations = useMemo(() => knowledge?.relations ?? [], [knowledge])

  const relations = useMemo(() =>
    showBelongsTo ? allRelations : allRelations.filter((r) => r.type !== 'belongs_to'),
    [allRelations, showBelongsTo])

  const relationCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const r of allRelations) {
      for (const m of r.members) {
        if (m.kind === 'object') {
          counts.set(m.id, (counts.get(m.id) ?? 0) + 1)
        }
      }
    }
    return counts
  }, [allRelations])

  const components = useMemo(() => {
    const adj = new Map<string, string[]>()
    const nodeIds = new Set<string>()
    for (const r of relations) {
      const ids = r.members.filter((m) => m.kind === 'object').map((m) => m.id)
      for (const id of ids) nodeIds.add(id)
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          if (!adj.has(ids[i])) adj.set(ids[i], [])
          if (!adj.has(ids[j])) adj.set(ids[j], [])
          adj.get(ids[i])!.push(ids[j])
          adj.get(ids[j])!.push(ids[i])
        }
      }
    }
    const visited = new Set<string>()
    const comps: string[][] = []
    for (const start of nodeIds) {
      if (visited.has(start)) continue
      const comp: string[] = []
      const queue = [start]
      visited.add(start)
      while (queue.length > 0) {
        const cur = queue.shift()!
        comp.push(cur)
        for (const nb of adj.get(cur) ?? []) {
          if (!visited.has(nb)) {
            visited.add(nb)
            queue.push(nb)
          }
        }
      }
      comps.push(comp)
    }
    return comps
  }, [relations])

  const componentLabels = useMemo(() => {
    const objMap = new Map(relationObjects.map((o) => [o.id, o]))
    return components.map((comp) => {
      const docNodeId = comp.find((id) => objMap.get(id)?.kind === 'document')
      const nodeId = docNodeId ?? comp.reduce((best, id) => {
        const bc = relationCounts.get(best) ?? 0
        const cc = relationCounts.get(id) ?? 0
        return cc > bc ? id : best
      }, comp[0])
      const obj = objMap.get(nodeId)
      const label = obj
        ? getNodeLabel({ id: obj.id, text: obj.text ?? null, kind: obj.kind ?? null, x: 0, y: 0 })
        : nodeId.slice(0, 8)
      return `${label}（${comp.length} 对象）`
    })
  }, [components, relationObjects, relationCounts])

  useEffect(() => {
    if (!focusNodeId) return
    if (focusAppliedRef.current === focusNodeId) return
    if (components.length === 0) return
    const compIdx = components.findIndex((comp) => comp.includes(focusNodeId))
    if (compIdx === -1) return
    setSelectedComponentIdx(compIdx)
    focusAppliedRef.current = focusNodeId
    centeredRef.current = false
  }, [focusNodeId, components])

  useEffect(() => {
    if (!focusNodeId) return
    if (selectedComponentIdx === null) return
    if (centeredRef.current) return
    const target = nodes.find((n) => n.id === focusNodeId)
    if (!target) return
    if (target.x === 0 && target.y === 0) return
    centeredRef.current = true
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    setZoom({
      x: rect.width / 2 - target.x,
      y: rect.height / 2 - target.y,
      scale: 1,
    })
  }, [focusNodeId, selectedComponentIdx, nodes, tick])

  useEffect(() => {
    const objectSet = new Set<string>()
    for (const r of relations) {
      for (const m of r.members) {
        if (m.kind === 'object') objectSet.add(m.id)
      }
    }

    if (selectedComponentIdx !== null && selectedComponentIdx < components.length) {
      const compSet = new Set(components[selectedComponentIdx])
      for (const id of [...objectSet]) {
        if (!compSet.has(id)) objectSet.delete(id)
      }
    }

    const objMap = new Map(relationObjects.map((o) => [o.id, o]))
    const graphNodes: GraphNode[] = []
    for (const oid of objectSet) {
      const obj = objMap.get(oid)
      if (!obj) continue
      graphNodes.push({
        id: obj.id,
        text: obj.text ?? null,
        kind: obj.kind ?? null,
        x: Math.random() * 400 + 300,
        y: Math.random() * 300 + 100,
      })
    }

    const nodeMap = new Map(graphNodes.map((n) => [n.id, n]))
    const graphEdges: GraphEdge[] = []
    for (const r of relations) {
      const src = r.members[0]
      const tgt = r.members[1]
      if (!src || !tgt || src.kind !== 'object' || tgt.kind !== 'object') continue
      if (!nodeMap.has(src.id) || !nodeMap.has(tgt.id)) continue
      graphEdges.push({
        id: r.id,
        type: r.type,
        description: r.description,
        source: src.id,
        target: tgt.id,
      })
    }

    if (simulationRef.current) {
      simulationRef.current.stop()
    }

    if (graphNodes.length === 0) {
      setNodes([])
      return
    }

    const sim = forceSimulation<GraphNode, GraphEdge>(graphNodes)
      .force('link', forceLink<GraphNode, GraphEdge>(graphEdges)
        .id((d) => d.id)
        .distance(120))
      .force('charge', forceManyBody().strength(-300))
      .force('center', forceCenter(500, 350))
      .force('collide', forceCollide<GraphNode>((d) => getNodeRadius(d.kind) + 20))
      .on('tick', () => setTick((t) => t + 1))

    simulationRef.current = sim
    setNodes(graphNodes)

    return () => {
      sim.stop()
    }
  }, [relationObjects, relations, selectedComponentIdx, components])

  const connectedIds = useMemo(() => {
    if (!hoveredNode && !hoveredEdge) return { nodes: new Set<string>(), edges: new Set<string>() }
    const nodeSet = new Set<string>()
    const edgeSet = new Set<string>()

    if (hoveredNode) {
      nodeSet.add(hoveredNode)
      for (const r of relations) {
        const ids = r.members.filter((m) => m.kind === 'object').map((m) => m.id)
        if (ids.includes(hoveredNode)) {
          edgeSet.add(r.id)
          for (const id of ids) nodeSet.add(id)
        }
      }
    }

    if (hoveredEdge) {
      edgeSet.add(hoveredEdge)
      const r = allRelations.find((rel) => rel.id === hoveredEdge)
      if (r) {
        for (const m of r.members) {
          if (m.kind === 'object') nodeSet.add(m.id)
        }
      }
    }

    return { nodes: nodeSet, edges: edgeSet }
  }, [hoveredNode, hoveredEdge, relations, allRelations])

  const objectMap = useMemo(() => {
    const m = new Map<string, RelationObject>()
    for (const o of relationObjects) m.set(o.id, o)
    return m
  }, [relationObjects])

  const getRelationById = useCallback((id: string): Relation | undefined =>
    allRelations.find((r) => r.id === id), [allRelations])

  const handleBackgroundMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target !== svgRef.current && (e.target as SVGElement).tagName !== 'svg') return
    draggingRef.current = true
    dragStartRef.current = { x: e.clientX - zoom.x, y: e.clientY - zoom.y }
    setSelectedNode(null)
  }, [zoom.x, zoom.y])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (nodeDragRef.current && simulationRef.current) {
      const svg = svgRef.current
      if (!svg) return
      const pt = svg.createSVGPoint()
      pt.x = e.clientX
      pt.y = e.clientY
      const ctm = svg.getScreenCTM()
      if (!ctm) return
      const svgPt = pt.matrixTransform(ctm.inverse())
      const correctedX = (svgPt.x - zoom.x) / zoom.scale
      const correctedY = (svgPt.y - zoom.y) / zoom.scale
      const node = simulationRef.current.nodes().find((n) => n.id === nodeDragRef.current)
      if (node) {
        node.fx = correctedX
        node.fy = correctedY
      }
      return
    }
    if (!draggingRef.current) return
    const dx = e.clientX - dragStartRef.current.x
    const dy = e.clientY - dragStartRef.current.y
    setZoom((z) => ({ ...z, x: dx, y: dy }))
  }, [zoom.x, zoom.y, zoom.scale])

  const handleMouseUp = useCallback(() => {
    draggingRef.current = false
    if (nodeDragRef.current && simulationRef.current) {
      const node = simulationRef.current.nodes().find((n) => n.id === nodeDragRef.current)
      if (node) {
        node.fx = null
        node.fy = null
      }
    }
    nodeDragRef.current = null
  }, [])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const svg = svgRef.current
    if (!svg) return
    const pt = svg.createSVGPoint()
    pt.x = e.clientX
    pt.y = e.clientY
    const ctm = svg.getScreenCTM()
    if (!ctm) return
    const svgPt = pt.matrixTransform(ctm.inverse())
    const newScale = zoom.scale * (e.deltaY < 0 ? 1.1 : 0.9)
    const clamped = Math.max(0.1, Math.min(5, newScale))
    const newX = svgPt.x - (e.clientX - zoom.x) / clamped
    const newY = svgPt.y - (e.clientY - zoom.y) / clamped
    setZoom((z) => ({
      x: z.x - (newX - svgPt.x) * clamped,
      y: z.y - (newY - svgPt.y) * clamped,
      scale: clamped,
    }))
  }, [zoom])

  const startNodeDrag = useCallback((nodeId: string) => {
    nodeDragRef.current = nodeId
    if (simulationRef.current) {
      simulationRef.current.alphaTarget(0.3).restart()
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-gray-500">
        加载中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen text-red-500">
        {error}
      </div>
    )
  }

  const visibleEdges = nodes.length > 0 ? relations.filter((r) => {
    const s = r.members[0]
    const t = r.members[1]
    if (!s || !t || s.kind !== 'object' || t.kind !== 'object') return false
    return nodes.some((n) => n.id === s.id) && nodes.some((n) => n.id === t.id)
  }) : []

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <div className="flex items-center gap-3 p-3 border-b bg-white shrink-0">
        <button
          onClick={() => navigate('/')}
          className="text-sm text-gray-500 hover:text-gray-700 px-2 py-1"
        >
          ← 返回
        </button>
        <h1 className="text-lg font-semibold text-gray-800">关系图谱</h1>
        <div className="flex-1" />
        {components.length > 1 && (
          <select
            value={selectedComponentIdx === null ? '' : selectedComponentIdx}
            onChange={(e) => {
              const v = e.target.value
              setSelectedComponentIdx(v === '' ? null : Number(v))
              focusAppliedRef.current = null
              centeredRef.current = true
            }}
            className="text-xs border rounded px-2 py-1 bg-white text-gray-700"
          >
            <option value="">全部（{nodes.length} 对象）</option>
            {componentLabels.map((label, i) => (
              <option key={i} value={i}>
                团 {i + 1}：{label}
              </option>
            ))}
          </select>
        )}
        <div className="flex items-center gap-4 text-xs">
          <label className="flex items-center gap-1.5 text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showBelongsTo}
              onChange={(e) => setShowBelongsTo(e.target.checked)}
              className="rounded"
            />
            显示「属于」关系
          </label>
          <span className="text-gray-400">
            {nodes.length} 个对象 · {visibleEdges.length} 个关系
          </span>
        </div>
        <div className="flex items-center gap-2">
          {Object.entries(KIND_COLORS).map(([kind, color]) => (
            <span key={kind} className="flex items-center gap-1 text-xs text-gray-500">
              <span
                className="inline-block rounded-full shrink-0"
                style={{ width: 8, height: 8, backgroundColor: color }}
              />
              {KIND_LABELS[kind] ?? kind}
            </span>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          style={{ cursor: draggingRef.current ? 'grabbing' : 'grab' }}
          onMouseDown={handleBackgroundMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          <g transform={`translate(${zoom.x},${zoom.y}) scale(${zoom.scale})`}>
            {visibleEdges.map((r) => {
              const srcNode = nodes.find((n) => n.id === r.members[0]?.id)
              const tgtNode = nodes.find((n) => n.id === r.members[1]?.id)
              if (!srcNode || !tgtNode) return null
              const isHighlighted = connectedIds.edges.has(r.id) || hoveredEdge === r.id
              const isDimmed = (hoveredNode || hoveredEdge) && !isHighlighted

              return (
                <g key={r.id}>
                  <line
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke={isHighlighted ? '#f59e0b' : '#cbd5e1'}
                    strokeWidth={isHighlighted ? 2 : 1}
                    opacity={isDimmed ? 0.15 : 1}
                    style={{ transition: 'opacity 0.2s' }}
                    onMouseEnter={() => setHoveredEdge(r.id)}
                    onMouseLeave={() => setHoveredEdge(null)}
                  />
                  {isHighlighted && (
                    <text
                      x={(srcNode.x + tgtNode.x) / 2}
                      y={(srcNode.y + tgtNode.y) / 2 - 6}
                      textAnchor="middle"
                      className="text-[10px] fill-amber-600 font-medium"
                      style={{ pointerEvents: 'none' }}
                    >
                      {RELATION_LABELS[r.type] ?? r.type}
                    </text>
                  )}
                  <line
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke="transparent"
                    strokeWidth={12}
                    onMouseEnter={() => setHoveredEdge(r.id)}
                    onMouseLeave={() => setHoveredEdge(null)}
                  />
                </g>
              )
            })}

            {nodes.map((n) => {
              const r = getNodeRadius(n.kind)
              const isConnected = connectedIds.nodes.has(n.id)
              const isThisHovered = hoveredNode === n.id
              const isDimmed = (hoveredNode || hoveredEdge) && !isConnected && !isThisHovered
              const count = relationCounts.get(n.id) ?? 0
              const color = getNodeColor(n.kind)

              return (
                <g
                  key={n.id}
                  transform={`translate(${n.x},${n.y})`}
                  style={{ cursor: 'pointer', transition: 'opacity 0.2s' }}
                  opacity={isDimmed ? 0.2 : 1}
                  onMouseEnter={() => setHoveredNode(n.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  onMouseDown={(e) => {
                    e.stopPropagation()
                    setSelectedNode(n.id === selectedNode ? null : n.id)
                    startNodeDrag(n.id)
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <circle
                    r={isThisHovered || selectedNode === n.id ? r + 3 : r}
                    fill={color}
                    stroke={selectedNode === n.id ? '#1e3a5f' : isThisHovered ? '#f59e0b' : 'transparent'}
                    strokeWidth={2}
                    style={{ transition: 'r 0.15s' }}
                  />
                  {count > 1 && (
                    <text
                      textAnchor="middle"
                      dy="0.35em"
                      className="text-[8px] fill-white font-medium"
                      style={{ pointerEvents: 'none' }}
                    >
                      {count > 9 ? '9+' : count}
                    </text>
                  )}
                  <text
                    textAnchor="middle"
                    dy={r + 12}
                    className="text-[10px] fill-gray-700"
                    style={{ pointerEvents: 'none' }}
                  >
                    {getNodeLabel(n)}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>
      </div>

      {selectedNode && (() => {
        const obj = objectMap.get(selectedNode)
        const node = nodes.find((n) => n.id === selectedNode)
        if (!obj || !node) return null
        const relatedRels = allRelations.filter((r) =>
          r.members.some((m) => m.kind === 'object' && m.id === selectedNode))
        return (
          <div className="absolute bottom-4 left-4 right-4 max-w-md bg-white border rounded-lg shadow-lg p-4 text-sm">
            <div className="flex items-center justify-between mb-2">
              <span
                className="inline-block w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: getNodeColor(obj.kind ?? null) }}
              />
              <span className="font-medium ml-2">{getNodeLabel(node)}</span>
              <span className="text-xs text-gray-400 ml-2">{KIND_LABELS[obj.kind ?? ''] ?? obj.kind}</span>
              <button
                onClick={() => setSelectedNode(null)}
                className="ml-auto text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            {obj.text && obj.text.length > 12 && (
              <p className="text-xs text-gray-600 mb-2">{obj.text}</p>
            )}
            <div className="text-xs text-gray-500">
              <span className="text-gray-400">关联关系:</span>
              {relatedRels.length === 0 ? ' 无' : relatedRels.map((r) => {
                const other = r.members.find((m) => m.kind === 'object' && m.id !== selectedNode)
                const otherObj = other ? objectMap.get(other.id) : null
                const otherLabel = otherObj ? getNodeLabel({
                  id: otherObj.id,
                  text: otherObj.text ?? null,
                  kind: otherObj.kind ?? null,
                  x: 0, y: 0,
                }) : '?'
                return (
                  <span key={r.id} className="inline-block mr-2">
                    {RELATION_LABELS[r.type] ?? r.type} → {otherLabel}
                  </span>
                )
              })}
            </div>
          </div>
        )
      })()}
    </div>
  )
}
