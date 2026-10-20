'use client'
import { useEffect, useMemo, useRef, useState } from 'react'
import { API, type OurBook } from './lib'

/* 책방 = 우리 영상이 있는 책만 다룬다(사용자 지시 09-10: "우리는 우리책만 취급하자").
   책마다 정보나루 지난달 전국 공공도서관 대출 순위(가장 많이 읽힌 판 기준)·대출 수, KEI 소장·
   청구기호·대출 상태, 우리 영상으로 가는 단추를 붙인다. 급상승·키워드·억지 '이어지는 고전'은
   뺐다 — 만화책 급상승과 끼워 맞춘 연결은 들어갈 이유가 못 됐다. */

type Dest = { work: string }

const SORTS = [{ id: 'rank', label: '인기순' }, { id: 'title', label: '제목순' }]
const FILTERS = [{ id: '', label: '전체' }, { id: 'kei', label: 'KEI 소장' }, { id: 'none', label: '미소장' }]
const HELD = ['paper', 'ebook', 'both']
/** ISO 시각 → 'YYMMDD(요일) HH:MM' — 페이지가 언제 기준인지 한눈에. */
function stampLabel(iso: string) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const p = (n: number) => String(n).padStart(2, '0')
  const day = '일월화수목금토'[d.getDay()]
  return `${String(d.getFullYear()).slice(2)}${p(d.getMonth() + 1)}${p(d.getDate())}(${day}) ${p(d.getHours())}:${p(d.getMinutes())}`
}
const PAGES = [20, 50, 0]   // 0 = 전체

function HoldPill({ b }: { b: OurBook }) {
  if (HELD.includes(b.holding)) {
    return (
      <span className="pill ok">
        {b.holding === 'ebook' ? 'KEI 전자책' : 'KEI 소장'}
        {b.callno && ` · ${b.callno}`}{b.status && ` · ${b.status}`}
      </span>
    )
  }
  if (b.holding === 'none') return <span className="pill no">KEI 미소장</span>
  return <span className="pill wait">소장 확인 중</span>
}

/** 지난달 대비 순위 변화 — 정보나루 12개월 이력에서 뽑는다(양수 = 올라감). */
function delta(b: OurBook): number | null {
  const h = b.history ?? []
  const cur = h[h.length - 1]?.rank, prev = h[h.length - 2]?.rank
  return cur && prev ? prev - cur : null
}

function Row<T extends Dest>({ b, no, dest, play }: { b: OurBook; no?: number; dest?: T; play: (it: T) => void }) {
  const [open, setOpen] = useState(false)
  const d = delta(b)
  return (
    <article className="ob-row">
      <div className="ob-cover">
        {b.cover
          ? <img src={b.cover} alt="" loading="lazy" referrerPolicy="no-referrer" />
          : <div className="bk-nocover">{b.title}</div>}
        {no && <span className="bk-rank">{no}</span>}
      </div>
      <div className="ob-body">
        <h3 className="ob-title">
          {b.title}
          {d != null && d !== 0 && (
            <em className={d > 0 ? 'up' : 'down'} title="지난달 대비 순위 변화">{d > 0 ? `▲${d.toLocaleString()}` : `▼${(-d).toLocaleString()}`}</em>
          )}
        </h3>
        <p className="bk-meta">
          {b.author}{b.publisher && ` · ${b.publisher}`}{b.year && ` ${b.year}`}
          {b.edition_kind && b.edition_kind !== '원작' && <span className="ob-kind"> · {b.edition_kind} 기준</span>}
        </p>
        {b.rank
          ? <p className="ob-rank">
              전국 <b>{b.rank.toLocaleString()}위</b>
              <span>지난달 대출 {b.month_loans.toLocaleString()}회 · 누적 {b.total_loans.toLocaleString()}회</span>
            </p>
          : <p className="ob-rank ob-norank">전국 순위 집계 없음<span>따로 나온 단행본이 없거나 지난달 대출 기록이 없습니다</span></p>}
        <HoldPill b={b} />
        {b.description && (
          <p className={open ? 'ob-desc open' : 'ob-desc'} onClick={() => setOpen(o => !o)} title={open ? '접기' : '더 보기'}>
            {b.description}
          </p>
        )}
        <div className="ob-actions">
          {dest && <button type="button" className="ob-play" onClick={() => play(dest)} aria-label={`${b.title} 영상 보기`}>▶ 영상 보기</button>}
        </div>
      </div>
    </article>
  )
}

export default function BooksTab<T extends Dest>({ items, play }: { items: T[]; play: (it: T) => void }) {
  const [books, setBooks] = useState<OurBook[]>([])
  const [month, setMonth] = useState('')
  const [updated, setUpdated] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [sort, setSort] = useState('rank')
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(20)      // N개씩 보기
  const [shownN, setShownN] = useState(20)  // 지금 펼친 개수
  const gen = useRef(0)

  // KEI 소장은 백엔드가 뒤에서 채운다 — '확인 중'이 남아 있으면 잠시 뒤 다시 받는다.
  const load = (tries = 0) => {
    const my = ++gen.current
    fetch(`${API}/api/books/ours`)
      .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json() })
      .then(d => {
        if (my !== gen.current) return
        const list: OurBook[] = d.books ?? []
        setBooks(list); setMonth(d.month ?? ''); setUpdated(d.updated ?? ''); setLoading(false); setError('')
        if (tries < 12 && list.some(b => b.holding === 'unknown')) setTimeout(() => load(tries + 1), 8000)
      })
      .catch(() => { setLoading(false); setError('도서 정보를 불러오지 못했습니다. 잠시 뒤 다시 열어 주세요.') })
  }
  useEffect(() => { load() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  // 영상이 있는 책만 — "우리 영상에 없는 책은 취급 안 한다". 원고만 있고 영상이 없는 작품은 뺀다.
  const ours = useMemo(() => books.filter(b => items.some(it => it.work === b.work)), [books, items])

  const shown = useMemo(() => {
    const w = q.trim().toLowerCase()
    let list = ours.filter(b => !w || [b.title, b.author, b.edition_author, b.publisher].some(x => (x ?? '').toLowerCase().includes(w)))
    if (filter === 'kei') list = list.filter(b => HELD.includes(b.holding))
    if (filter === 'none') list = list.filter(b => b.holding === 'none')
    if (sort === 'title') list = list.slice().sort((a, b) => a.title.localeCompare(b.title, 'ko'))
    return list
  }, [ours, q, sort, filter])
  useEffect(() => { setShownN(page || Infinity) }, [page, q, sort, filter])
  const visible = page ? shown.slice(0, shownN) : shown

  const ranked = ours.filter(b => b.rank).length
  const held = ours.filter(b => HELD.includes(b.holding)).length
  const top = ours.find(b => b.rank)

  return (
    <main className="wrap bk">
      <header className="phead">
        <h1>책방 — 우리 영상 속 책들</h1>
        <p>
          영상으로 만든 {ours.length || ''}권이 전국 공공도서관에서 얼마나 읽히는지, KEI 도서관에 있는지 한눈에 봅니다.
          순위는 정보나루가 집계한 {month || '지난달'} 전국 대출 순위이고, 어린이·만화판은 빼고 원작(완역) 판 가운데 가장 많이 읽힌 판을 기준으로 합니다.
        </p>
      </header>
      {ours.length > 0 && (
        <div className="ob-stats">
          <span><b>{ranked}</b>권 순위 집계</span>
          <span><b>{held}</b>권 KEI 소장</span>
          {top && <span>가장 많이 읽힌 책 <b>{top.title}</b> 전국 {top.rank!.toLocaleString()}위</span>}
          {updated && <span className="ob-stamp">{stampLabel(updated)} 기준 · 매일 09:00 갱신</span>}
        </div>
      )}

      <div className="bk-search">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="제목이나 지은이로 찾기 — 예: 카프카, 김유정" aria-label="책 찾기" />
        {q && <button type="button" className="bk-clear" onClick={() => setQ('')}>지우기</button>}
      </div>
      <div className="chips" role="tablist" aria-label="정렬">
        {SORTS.map(s => (
          <button key={s.id} type="button" className={s.id === sort ? 'chip on' : 'chip'} onClick={() => setSort(s.id)}>{s.label}</button>
        ))}
        <span className="ob-sep" aria-hidden="true" />
        {FILTERS.map(f => (
          <button key={f.id} type="button" className={f.id === filter ? 'chip on' : 'chip'} onClick={() => setFilter(f.id)}>{f.label}</button>
        ))}
        <span className="ob-sep" aria-hidden="true" />
        {PAGES.map(n => (
          <button key={n} type="button" className={n === page ? 'chip on' : 'chip'} onClick={() => setPage(n)}>{n ? `${n}개씩` : '전체'}</button>
        ))}
      </div>

      {error && !books.length && <p className="bk-empty">{error}</p>}
      {loading && !ours.length && <p className="bk-empty">불러오는 중</p>}
      {ours.length > 0 && (shown.length
        ? <div className="ob-list">
            {visible.map((b, i) => (
              <Row key={b.work} b={b} no={sort === 'rank' ? i + 1 : undefined}
                dest={items.find(it => it.work === b.work)} play={play} />
            ))}
          </div>
        : <p className="bk-empty">맞는 책이 없습니다.</p>)}
      {page > 0 && shownN < shown.length && (
        <button type="button" className="bk-more" onClick={() => setShownN(n => n + page)}>
          더 보기 <small>({Math.min(shownN, shown.length)} / {shown.length})</small>
        </button>
      )}
      <p className="ob-src">순위·대출 수: 도서관 정보나루(data4library.kr) 전국 공공도서관 대출 통계 · 소장·청구기호·대출 상태: KEI 도서관</p>
    </main>
  )
}
