'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { geoGraticule10, geoNaturalEarth1, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'
import type { Feature, FeatureCollection, Geometry } from 'geojson'

/** 지도가 아는 작품 한 편. countryNum 은 world-atlas 의 숫자 id(works/countries.json 의 num). */
export type MapWork = { work: string; title: string; country: string; countryNum: string }

type Group = { name: string; works: MapWork[] }
type CountryFeature = Feature<Geometry, { name: string }> & { id: string }

const W = 960, H = 500
/* 이름표는 편 수가 많은 나라에만. 덴마크·체코처럼 작은 나라는 옆으로 밀어 겹치지 않게. */
const LABEL_MIN = 9
const NUDGE: Record<string, [number, number]> = { '208': [10, -6], '203': [0, 8] }

/** 세계 문학 전집의 나라별 지도. 나라에 마우스를 얹으면 그 나라의 작품 목록이 뜨고,
 *  누르면 onSelect 로 그 나라를 골라 아래 칩·카드가 걸러진다. 같은 나라를 다시 누르면 푼다.
 *  지형은 /world/countries-110m.json (Natural Earth 110m, world-atlas) — 외부 지도 서비스를 쓰지 않는다. */
export function WorldMap({ works, selected, onSelect }: {
  works: MapWork[]
  selected: string
  onSelect: (country: string) => void
}) {
  const wrap = useRef<HTMLDivElement>(null)
  const [features, setFeatures] = useState<CountryFeature[]>([])
  const [failed, setFailed] = useState(false)
  const [tip, setTip] = useState<{ x: number; y: number; g: Group } | null>(null)

  useEffect(() => {
    let alive = true
    fetch('/world/countries-110m.json').then(r => r.json()).then(topo => {
      if (!alive) return
      const fc = feature(topo, topo.objects.countries) as unknown as FeatureCollection<Geometry, { name: string }>
      setFeatures(fc.features.map(f => ({ ...f, id: String(f.id) })))
    }).catch(() => alive && setFailed(true))
    return () => { alive = false }
  }, [])

  // 나라(숫자 id) → 작품 묶음. 제목순으로 꽂는다.
  const groups = useMemo(() => {
    const m: Record<string, Group> = {}
    for (const w of works) {
      if (!w.countryNum) continue
      ;(m[w.countryNum] ??= { name: w.country, works: [] }).works.push(w)
    }
    for (const g of Object.values(m)) g.works.sort((a, b) => a.title.localeCompare(b.title, 'ko'))
    return m
  }, [works])
  const maxN = Math.max(1, ...Object.values(groups).map(g => g.works.length))
  /* 물감 농도: 한 편이면 옅게, 가장 많은 나라가 진하게. 제곱근이라 적은 나라들 사이 차이가 보인다. */
  const pct = (n: number) => Math.round(22 + 78 * Math.sqrt((n - 1) / Math.max(1, maxN - 1)))

  const path = useMemo(() => {
    const projection = geoNaturalEarth1().fitExtent([[6, 6], [W - 6, H - 6]], { type: 'Sphere' })
    return geoPath(projection)
  }, [])

  const show = (e: React.MouseEvent, g: Group) => {
    const r = wrap.current?.getBoundingClientRect()
    if (!r) return
    let x = e.clientX - r.left + 16, y = e.clientY - r.top + 16
    if (x + 260 > r.width) x = e.clientX - r.left - 16 - 250
    if (y + 200 > r.height) y = e.clientY - r.top - 16 - 190
    setTip({ x, y, g })
  }
  const pick = (g: Group) => onSelect(selected === g.name ? '' : g.name)

  return (
    <div className="wmap" ref={wrap}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="나라별 작품 수를 칠한 세계 지도">
        <path className="wm-sphere" d={path({ type: 'Sphere' }) ?? undefined} />
        <path className="wm-grat" d={path(geoGraticule10()) ?? undefined} />
        <g>
          {features.map(f => {
            const g = groups[f.id]
            if (!g) return <path key={f.id} className="wm-c" d={path(f) ?? undefined} />
            const n = g.works.length
            return (
              <path key={f.id} d={path(f) ?? undefined}
                className={selected === g.name ? 'wm-c has on' : 'wm-c has'}
                style={{ fill: `color-mix(in oklab, var(--blue) ${pct(n)}%, var(--ash))` }}
                tabIndex={0} role="button" aria-pressed={selected === g.name}
                aria-label={`${g.name} ${n}편`}
                onMouseMove={e => show(e, g)} onMouseLeave={() => setTip(null)}
                onMouseDown={e => e.preventDefault()}  /* 마우스 클릭으로는 초점을 주지 않는다 — 검은 초점 사각형이 남는다(실측) */
                onClick={() => pick(g)}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(g) } }}
              />
            )
          })}
        </g>
        <g>
          {features.filter(f => (groups[f.id]?.works.length ?? 0) >= LABEL_MIN).map(f => {
            const [cx, cy] = path.centroid(f)
            const [dx, dy] = NUDGE[f.id] ?? [0, 0]
            const g = groups[f.id]
            return (
              <text key={f.id} className="wm-lbl" textAnchor="middle" transform={`translate(${cx + dx},${cy + dy})`}>
                {g.name} <tspan>{g.works.length}</tspan>
              </text>
            )
          })}
        </g>
      </svg>
      {!features.length && !failed && <div className="wm-load">지도를 펼치는 중…</div>}
      {failed && <div className="wm-load">지도를 불러오지 못했습니다. 아래 나라 칩으로 고를 수 있습니다.</div>}
      {tip && (
        <div className="wm-tip" style={{ left: tip.x, top: tip.y }} role="status">
          <h3>{tip.g.name}<em>{tip.g.works.length}편</em></h3>
          <ul>{tip.g.works.slice(0, 6).map(w => <li key={w.work}>{w.title}</li>)}</ul>
          {tip.g.works.length > 6 && <div className="more">외 {tip.g.works.length - 6}편 · 눌러서 모아 보기</div>}
        </div>
      )}
    </div>
  )
}
