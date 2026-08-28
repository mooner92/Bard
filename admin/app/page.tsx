'use client'

import { useEffect, useRef, useState } from 'react'
import { API, Book, PlayIcon, Player, TopNav, Video, Work, fmtDate } from './lib'

type Item = {
  work: string; title: string; cover?: string; video?: Video
  region: string; genre: string; blurb: string; mood: string
  season: string; seasonNote: string
}

/* 오늘 날짜로 계절을 정한다. 3~5월 봄, 6~8월 여름, 9~11월 가을, 나머지 겨울. */
const SEASONS = ['봄', '여름', '가을', '겨울'] as const
function currentSeason(): string {
  const m = new Date().getMonth() + 1
  return m >= 3 && m <= 5 ? '봄' : m >= 6 && m <= 8 ? '여름' : m >= 9 && m <= 11 ? '가을' : '겨울'
}
const SEASON_HEAD: Record<string, string> = {
  '봄': '봄바람 불 때 꺼내 읽는 소설.',
  '여름': '뜨거운 여름, 그때가 생각나는 소설.',
  '가을': '깊어가는 가을에 어울리는 소설.',
  '겨울': '긴 겨울밤에 읽기 좋은 소설.',
}

/** 전체보기 왼쪽 필터의 축. 값은 works/categories.json 이 정한다. */
type FacetKey = 'region' | 'genre'
const FACETS: { key: FacetKey; label: string }[] = [
  { key: 'region', label: '어디 이야기' },
  { key: 'genre', label: '어떤 이야기' },
]

/** 재생 1회 기록. 같은 세션의 반복 클릭은 세지 않는다 — 새로고침 연타로 부풀지 않게. */
function countView(work: string) {
  try {
    const k = `bard_v_${work}`
    if (sessionStorage.getItem(k)) return
    sessionStorage.setItem(k, '1')
  } catch {}
  fetch(`${API}/api/stats/view`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ work }),
  }).catch(() => {})
}

/** 스크롤로 화면에 들어올 때 한 번 떠오르는 틀. 지나치면 다시 접지 않는다. */
function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [on, setOn] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setOn(true); io.disconnect() }
    }, { threshold: 0.15 })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <div ref={ref} className={on ? 'reveal in' : 'reveal'}
      style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  )
}

/* 마우스를 따라 살짝 기우는 효과. ±5° 안쪽 — 난잡해지지 않게 마일드하게만. */
function tiltMove(e: React.MouseEvent<HTMLElement>) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  const x = (e.clientX - r.left) / r.width - 0.5
  const y = (e.clientY - r.top) / r.height - 0.5
  el.style.setProperty('--tx', `${(-y * 4).toFixed(2)}deg`)
  el.style.setProperty('--ty', `${(x * 5).toFixed(2)}deg`)
}
function tiltLeave(e: React.MouseEvent<HTMLElement>) {
  e.currentTarget.style.setProperty('--tx', '0deg')
  e.currentTarget.style.setProperty('--ty', '0deg')
}

/** KEI 도서관 소장 판정 → 뱃지. unknown 은 백그라운드 조회 중이라는 뜻. */
function HoldPill({ h }: { h: string }) {
  const label: Record<string, string> = {
    paper: 'KEI 종이책', ebook: 'KEI 전자책', both: 'KEI 종이책·전자책', none: '미소장',
  }
  if (!label[h]) return <span className="pill wait">확인 중</span>
  return <span className={h === 'none' ? 'pill no' : 'pill ok'}>{label[h]}</span>
}

/** 같은 책이 권별 ISBN 으로 여러 줄 나오는 것(흔한남매 9·10위 실측)을 제목으로 접는다 */
function dedupeBooks(books: Book[]): Book[] {
  const seen = new Set<string>()
  const out: Book[] = []
  for (const b of books) {
    const k = b.title.replace(/\s+/g, '')
    if (seen.has(k)) continue
    seen.add(k)
    out.push(b)
  }
  return out
}

function Card({ it, onPlay, views, note }: {
  it: Item; onPlay: () => void; views?: number; note?: string
}) {
  return (
    <button className="vcard" onClick={onPlay}>
      <span className="thumb shimmer">
        {it.cover
          ? <img src={`${API}/api/files/keyframe/${it.work}/${it.cover}`} alt=""
              onLoad={e => e.currentTarget.classList.add('ld')} />
          : <span className="ph" />}
        <span className="play sm"><PlayIcon size={18} /></span>
      </span>
      <span className="vtitle">{it.title}</span>
      {note && <span className="snote">{note}</span>}
      {it.blurb && <span className="blurb" data-mood={it.mood}>{it.blurb}</span>}
      <span className="fine">
        {it.video?.duration ?? '?'}초 · {fmtDate(it.video?.updated)}
        {views ? ` · 조회 ${views.toLocaleString()}` : ''}
      </span>
    </button>
  )
}

export default function Home() {
  const [items, setItems] = useState<Item[]>([])
  const [books, setBooks] = useState<Book[]>([])
  const [period, setPeriod] = useState('')
  const [tab, setTab] = useState('home')
  const [playing, setPlaying] = useState<Item | null>(null)
  const [slide, setSlide] = useState(0)
  const [featured, setFeatured] = useState<string[]>([])
  const [picks, setPicks] = useState<Record<FacetKey, string[]>>({ region: [], genre: [] })
  const [q, setQ] = useState('')
  const [stats, setStats] = useState<{ total: Record<string, number>; month: Record<string, number>;
    monthly_top: { work: string; views: number }[] } | null>(null)
  const [pageSize, setPageSize] = useState(30)
  const [page, setPage] = useState(0)
  const [season, setSeason] = useState(currentSeason())

  useEffect(() => {
    fetch(`${API}/api/works`).then(r => r.json()).then(async (d: { works: Work[] }) => {
      const names = [...new Set(d.works.map(w => w.work))]
      const rows = await Promise.all(names.map(async name => {
        const title = d.works.find(w => w.work === name)?.title ?? name
        const [kf, vid] = await Promise.all([
          fetch(`${API}/api/works/${name}/keyframes`).then(r => r.json()).catch(() => ({ images: [] })),
          fetch(`${API}/api/works/${name}/videos`).then(r => r.json()).catch(() => ({ videos: [] })),
        ])
        // 내부 미리보기: 승인본(final)과 야간 산출물(night)의 최신 하나씩. 압축본 제외.
        const finals = (vid.videos as Video[]).filter(
          v => (v.kind === 'final' || v.kind === 'night') && !v.name.includes('compressed'))
        const latest = finals.sort((a, b) => (a.updated < b.updated ? 1 : -1))[0]
        const row = d.works.find(w => w.work === name)
        return {
          work: name, title, cover: kf.images?.[0], video: latest,
          region: row?.region ?? '기타', genre: row?.genre ?? '기타',
          blurb: row?.blurb ?? '', mood: row?.mood ?? '',
          season: row?.season ?? '', seasonNote: row?.season_note ?? '',
        }
      }))
      setItems(rows.filter(r => r.video))
    }).catch(() => {})

    fetch(`${API}/api/featured`).then(r => r.json())
      .then(d => setFeatured(d.works ?? [])).catch(() => {})

    fetch(`${API}/api/stats/summary`).then(r => r.json())
      .then(setStats).catch(() => {})

    fetch(`${API}/api/books/popular?limit=30`).then(r => r.json())
      .then(d => {
        setBooks(dedupeBooks(d.books ?? []).slice(0, 20))
        setPeriod(`${d.period?.start} ~ ${d.period?.end}`)
      })
      .catch(() => {})
  }, [])

  const play = (it: Item) => { countView(it.work); setPlaying(it) }

  // 통상의 미디어 홈 구성: 인기 작품(히어로) → 신규 작품, 전체 목록은 상단 네비 별도 탭.
  // 인기 작품은 관리자가 정한 순서를 그대로 따른다. 비어 있으면 승인본, 그것도 없으면 최신순.
  const byNew = (a: Item, b: Item) => (a.video!.updated < b.video!.updated ? 1 : -1)
  const picked = featured
    .map(w => items.find(it => it.work === w))
    .filter((x): x is Item => !!x)
  const approved = items.filter(it => it.video?.kind === 'final')
  const hero = (picked.length ? picked
    : approved.length ? approved : items.slice().sort(byNew)).slice(0, 5)
  const heroSet = new Set(hero.map(h => h.work))
  const fresh = items.filter(it => !heroSet.has(it.work)).sort(byNew).slice(0, 8)

  // 전체보기 필터. 같은 축 안에서는 OR(한국이거나 영국), 축끼리는 AND(한국이면서 모험).
  const toggle = (k: FacetKey, name: string) => { setPage(0); setPicks(p => ({
    ...p,
    [k]: p[k].includes(name) ? p[k].filter(x => x !== name) : [...p[k], name],
  })) }
  const hit = (it: Item) =>
    FACETS.every(f => !picks[f.key].length || picks[f.key].includes(it[f.key]))
    && (!q.trim() || it.title.toLowerCase().includes(q.trim().toLowerCase()))
  const shown = items.filter(hit).sort(byNew)
  // 페이지는 조건이 바뀌면 처음으로 돌아간다. 남은 쪽수 밖에 서 있지 않게.
  const pages = Math.max(1, Math.ceil(shown.length / pageSize))
  const safePage = Math.min(page, pages - 1)
  const paged = shown.slice(safePage * pageSize, (safePage + 1) * pageSize)

  // 칸마다 몇 편인지. 고르기 전에 결과 크기를 보여 준다 — 0편짜리를 누르는 헛수고를 막는다.
  // 자기 축의 선택은 빼고 센다(한국을 고른 상태에서도 영국이 몇 편인지 보여야 한다).
  const counts = Object.fromEntries(FACETS.map(f => {
    const others = (it: Item) =>
      FACETS.every(g => g.key === f.key || !picks[g.key].length || picks[g.key].includes(it[g.key]))
      && (!q.trim() || it.title.toLowerCase().includes(q.trim().toLowerCase()))
    const m = new Map<string, number>()
    for (const it of items.filter(others)) m.set(it[f.key], (m.get(it[f.key]) ?? 0) + 1)
    return [f.key, [...m.entries()].sort((a, b) => b[1] - a[1])]
  })) as Record<FacetKey, [string, number][]>

  // 캐러셀 자동 회전 — 재생 중에는 멈춘다
  useEffect(() => {
    if (playing || hero.length < 2) return
    const t = setInterval(() => setSlide(s => (s + 1) % hero.length), 5000)
    return () => clearInterval(t)
  }, [playing, hero.length])
  const cur = hero.length ? slide % hero.length : 0

  return (
    <>
      <TopNav
        tab={tab} onTab={setTab}
        items={[
          { id: 'home', label: '홈' },
          { id: 'all', label: '모든 작품' },
          { id: 'season', label: '계절 추천' },
          { id: 'books', label: '인기대출도서' },
        ]}
        right={<a className="ghost" href="/admin">관리자</a>}
      />

      {tab === 'home' && (
        <main className="homefit">
          <p className="tagline">책 속 세계를, 1분 안에 — 문학을 짧은 영상으로 다시 읽습니다.</p>

          <section className="hero">
              <h2 className="sec hero-sec">인기 작품</h2>
              {/* 커버플로우: 가운데 큰 셀 + 양옆이 바깥으로 기운 작은 셀.
                  옆 셀을 누르면 그쪽으로 한 칸 돌고, 가운데를 누르면 재생한다. */}
              <div className="cflow">
                {hero.length === 0 && [-1, 0, 1].map(o => (
                  /* 데이터가 오기 전의 자리 지킴 — 반짝 쓸림으로 로딩 중임을 보인다 */
                  <div key={o} className="cell shimmer" data-off={o} aria-hidden />
                ))}
                {hero.map((it, i) => {
                  const n = hero.length
                  let off = i - cur
                  if (off > n / 2) off -= n
                  if (off < -n / 2) off += n
                  const o = Math.max(-2, Math.min(2, off))
                  return (
                    <button key={it.work} className="cell shimmer" data-off={o}
                      tabIndex={o === 0 ? 0 : -1}
                      aria-label={o === 0 ? `${it.title} 재생` : `${it.title}(으)로 이동`}
                      onClick={() => o === 0 ? play(it) : setSlide((cur + o + n) % n)}>
                      {it.cover
                        ? <img src={`${API}/api/files/keyframe/${it.work}/${it.cover}`} alt=""
                            onLoad={e => e.currentTarget.classList.add('ld')} />
                        : <span className="ph" />}
                      <span className="scrim" />
                      <span className="slabel">
                        <strong>{it.title}</strong>
                        {it.blurb && <small className="hblurb" data-mood={it.mood}>{it.blurb}</small>}
                      </span>
                      <span className="play"><PlayIcon size={26} /></span>
                    </button>
                  )
                })}
              </div>
              <div className="dots">
                {hero.map((_, i) => (
                  <button key={i} className={i === cur ? 'dot on' : 'dot'}
                    onClick={() => setSlide(i)} aria-label={`${i + 1}번 슬라이드`} />
                ))}
                {hero.length === 0 && <span className="dot" aria-hidden />}
              </div>
            </section>

          {/* 사이트 소개 — 캐러셀 아래에 이 서비스가 무엇인지 한 호흡으로. */}
          <section className="intro">
            <Reveal>
              <p className="intro-lead">
                밤마다 서가에서 한 편씩.<br />
                고전문학을 <em>1분 남짓한 세로 영상</em>으로 다시 읽습니다.
              </p>
            </Reveal>
            <div className="intro-cards">
              {[
                ['문턱까지만', '열네 장면의 짜임새로 이야기의 가장 궁금한 자리까지 데려다 드립니다. 결말은 책에 있습니다.'],
                ['밤사이 만들어집니다', '대본과 그림, 낭독과 영상이 연구원 서버에서 매일 밤 자동으로 지어집니다.'],
                ['서가로 잇습니다', '지금 많이 빌려 읽는 책에서 닿아 있는 고전을 골라, KEI 서가의 청구기호까지 안내합니다.'],
              ].map(([h, b], i) => (
                <Reveal key={h} delay={i * 120}>
                  <div className="icard" onMouseMove={tiltMove} onMouseLeave={tiltLeave}>
                    <h3>{h}</h3>
                    <p>{b}</p>
                  </div>
                </Reveal>
              ))}
            </div>
            <Reveal delay={160}>
              <div className="intro-nums">
                <span><strong>{items.length || '–'}</strong>편의 고전</span>
                <span><strong>6</strong>가지 분위기</span>
                <span><strong>1</strong>분 남짓</span>
              </div>
            </Reveal>
          </section>

          {/* 이달의 인기작 — 달력 기준 이번 달 조회수 순. 아직 조회가 없으면 숨긴다. */}
          {(stats?.monthly_top?.length ?? 0) > 0 && (
            <Reveal>
              <h2 className="sec">이달의 인기작</h2>
              <div className="grid4">
                {stats!.monthly_top
                  .map(t => ({ t, it: items.find(x => x.work === t.work) }))
                  .filter((x): x is { t: { work: string; views: number }; it: Item } => !!x.it)
                  .slice(0, 6)
                  .map(({ t, it }) => (
                    <Card key={it.work} it={it} views={t.views} onPlay={() => play(it)} />
                  ))}
              </div>
            </Reveal>
          )}
        </main>
      )}

      {tab === 'all' && (
        <main className="wrap">
          <header className="phead">
            <h1>모든 작품.</h1>
            <p>
              {shown.length}편
              {shown.length !== items.length && ` (전체 ${items.length}편)`} · 최신순
            </p>
          </header>
          <div className="browse">
            <aside className="facets">
              <div className="facethead">
                <h2>분류</h2>
                {(picks.region.length > 0 || picks.genre.length > 0 || q) && (
                  <button className="ghost" onClick={() => {
                    setPicks({ region: [], genre: [] }); setQ('')
                  }}>초기화</button>
                )}
              </div>
              <input
                className="facetq" value={q} onChange={e => setQ(e.target.value)}
                placeholder="제목 검색" aria-label="작품 제목 검색"
              />
              {FACETS.map(f => (
                <section key={f.key} className="facet">
                  <h3>{f.label}</h3>
                  {counts[f.key].map(([name, n]) => (
                    <label key={name} className="facetrow">
                      <input
                        type="checkbox"
                        checked={picks[f.key].includes(name)}
                        onChange={() => toggle(f.key, name)}
                      />
                      <span>{name}</span>
                      <em>{n}</em>
                    </label>
                  ))}
                </section>
              ))}
            </aside>
            <div className="browsemain">
              <div className="pagebar">
                <span className="fine">{shown.length}편 중 {shown.length ? safePage * pageSize + 1 : 0}–{Math.min((safePage + 1) * pageSize, shown.length)}</span>
                <span className="pagesizes">
                  {[10, 30, 50].map(n => (
                    <button key={n} className={pageSize === n ? 'psz on' : 'psz'}
                      onClick={() => { setPageSize(n); setPage(0) }}>{n}개씩</button>
                  ))}
                </span>
                <span className="pagenav">
                  <button className="ghost" disabled={safePage === 0}
                    onClick={() => setPage(safePage - 1)} aria-label="이전 페이지">‹</button>
                  <span className="fine">{safePage + 1} / {pages}</span>
                  <button className="ghost" disabled={safePage >= pages - 1}
                    onClick={() => setPage(safePage + 1)} aria-label="다음 페이지">›</button>
                </span>
              </div>
              <div className="grid browsegrid">
                {paged.map(it => (
                  <Card key={it.work} it={it} views={stats?.total?.[it.work]} onPlay={() => play(it)} />
                ))}
                {!items.length && <p className="fine">아직 공개된 영상이 없습니다.</p>}
                {!!items.length && !shown.length &&
                  <p className="fine">고른 조건에 맞는 작품이 없습니다.</p>}
              </div>
            </div>
          </div>
        </main>
      )}

      {tab === 'season' && (
        <main className="wrap">
          <header className="phead">
            <h1>{SEASON_HEAD[season]}</h1>
            <p>
              오늘 기준 {currentSeason()}의 서가입니다 · 책 속 계절이 지금과 닿아 있는 작품을 골랐습니다
            </p>
          </header>
          <div className="seasonchips">
            {SEASONS.map(sn => (
              <button key={sn} className={season === sn ? 'psz on' : 'psz'}
                onClick={() => setSeason(sn)}>
                {sn}{sn === currentSeason() ? ' · 지금' : ''}
              </button>
            ))}
          </div>
          <div className="grid browsegrid">
            {items.filter(it => it.season === season).map(it => (
              <Card key={it.work} it={it} note={it.seasonNote}
                views={stats?.total?.[it.work]} onPlay={() => play(it)} />
            ))}
            {!items.filter(it => it.season === season).length &&
              <p className="fine">이 계절에 배정된 작품이 아직 없습니다.</p>}
          </div>
        </main>
      )}

      {tab === 'books' && (
        <main className="wrap">
          <header className="phead">
            <h1>지금 많이 읽는 책, 이어지는 고전.</h1>
            <p>
              전국 도서관 대출 순위에서 출발해 닿아 있는 우리 고전 영상까지 —
              KEI 소장 여부와 청구기호를 함께 안내합니다. ({period || '불러오는 중'})
            </p>
          </header>
          <ol className="books">
            {books.map(b => {
              // 이어지는 고전에 영상이 있으면 눌러서 바로 볼 수 있게 한다.
              const dest = b.bridge ? items.find(it => it.work === b.bridge!.work) : undefined
              return (
                <li key={b.isbn || b.rank}>
                  <span className="rank">{b.rank}</span>
                  <span className="btext">
                    <span className="btitle">
                      {b.title}
                      {b.delta != null && b.delta !== 0 && (
                        <em className={b.delta > 0 ? 'up' : 'down'}>
                          {b.delta > 0 ? `▲${b.delta}` : `▼${-b.delta}`}
                        </em>
                      )}
                      {b.delta === null && <em className="new">NEW</em>}
                    </span>
                    <span className="fine">
                      {b.author} · 대출 {b.loans.toLocaleString()}
                      {b.callno && ` · 청구기호 ${b.callno}`}
                      {b.status && ` · ${b.status}`}
                    </span>
                    {b.bridge && (
                      <span className="bridge">
                        이 책을 읽으셨다면{' '}
                        {dest
                          ? <button className="blink" onClick={() => play(dest)}>
                              {b.bridge.title}
                            </button>
                          : <strong>{b.bridge.title}</strong>}
                        <small>{b.bridge.why}</small>
                      </span>
                    )}
                  </span>
                  {dest?.cover && (
                    <button className="bjump" onClick={() => play(dest)}
                      aria-label={`${b.bridge!.title} 영상 재생`}>
                      <img alt="" src={`${API}/api/files/keyframe/${dest.work}/${dest.cover}`} />
                      <span className="bplay"><PlayIcon size={13} /></span>
                    </button>
                  )}
                  <HoldPill h={b.holding} />
                </li>
              )
            })}
            {!books.length && <p className="fine">도서 정보를 불러오지 못했습니다.</p>}
          </ol>
        </main>
      )}

      {playing?.video && (
        <Player
          src={`${API}/api/files/video/${playing.work}/${playing.video.name}`}
          title={playing.title}
          meta={`${playing.video.duration ?? '?'}초 · ${fmtDate(playing.video.updated)}`}
          onClose={() => setPlaying(null)}
        />
      )}
    </>
  )
}
