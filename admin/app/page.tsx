'use client'
import BooksTab from './Books'

import { useEffect, useRef, useState } from 'react'
import { API, PlayIcon, Player, TopNav, Video, Work, fmtDate } from './lib'
import { WorldMap } from './WorldMap'

type Item = {
  work: string; title: string; cover?: string; video?: Video
  region: string; genre: string; blurb: string; mood: string
  season: string; seasonNote: string
  country: string; countryCode: string; countryNum: string
  era: string; kei: boolean
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

/** 추천작품의 하위 탭. 상단 드롭다운과 같은 목록 — 터치 화면에는 드롭다운이 없어 본문에도 둔다. */
const PICKS = [
  { id: 'season', label: '계절 추천' },
  { id: 'world', label: '세계 문학 전집' },
  { id: 'modern', label: '현대소설' },
]
function SubNav({ tab, onTab }: { tab: string; onTab: (id: string) => void }) {
  return (
    <div className="subnav" role="tablist" aria-label="추천작품">
      {PICKS.map(p => (
        <button key={p.id} role="tab" aria-selected={tab === p.id}
          className={tab === p.id ? 'psz on' : 'psz'} onClick={() => onTab(p.id)}>
          {p.label}
        </button>
      ))}
    </div>
  )
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
  const [tab, setTab] = useState('home')
  // 시청 호스트(watch.…)에서는 관리자 진입점을 그리지 않는다. 미들웨어가 /admin 을 404 로
  // 막지만, 링크가 보이는 것 자체가 "여기 관리자가 있다"는 안내가 된다.
  const [watchHost, setWatchHost] = useState(false)
  useEffect(() => {
    const hosts = (process.env.NEXT_PUBLIC_WATCH_HOSTS ?? 'watch.bard.excusa.uk')
      .split(',').map(x => x.trim().toLowerCase())
    setWatchHost(hosts.includes(window.location.hostname.toLowerCase()))
  }, [])
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
  const [country, setCountry] = useState('')

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
          country: row?.country ?? '', countryCode: row?.country_code ?? '',
          countryNum: row?.country_num ?? '',
          era: row?.era ?? '고전', kei: !!row?.kei,
        }
      }))
      setItems(rows.filter(r => r.video))
    }).catch(() => {})

    fetch(`${API}/api/featured`).then(r => r.json())
      .then(d => setFeatured(d.works ?? [])).catch(() => {})

    fetch(`${API}/api/stats/summary`).then(r => r.json())
      .then(setStats).catch(() => {})

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

  // 세계 문학 전집 — 한국 밖에서 태어난 작품을 나라별로. 나라는 works/countries.json 이 정한다.
  const worldItems = items.filter(it => it.country && it.country !== '한국')
  const worldCountries = [...worldItems.reduce(
    (m, it) => m.set(it.country, (m.get(it.country) ?? 0) + 1), new Map<string, number>())]
    .sort((a, b) => b[1] - a[1])
  // 지도에서 한국을 누르면 우리 작품도 같은 자리에서 본다 — 한국은 전집 밖이지만 지도 위에는 있다.
  const koreanItems = items.filter(it => it.country === '한국')
  // 현대소설 — 저작권이 살아 있는 요즘 소설. 줄거리 대신 책이 던지는 질문까지만 담았다.
  const modernItems = items.filter(it => it.era === '현대').sort(byNew)
  const classicCount = items.length - modernItems.length

  const worldShown = (country === '한국' ? koreanItems
    : worldItems.filter(it => !country || it.country === country)).sort(byNew)

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
          { id: 'picks', label: '추천작품', children: PICKS },
          { id: 'books', label: '인기대출도서' },
        ]}
        right={watchHost ? null : <a className="ghost" href="/admin">관리자</a>}
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
                <span><strong>{classicCount || '–'}</strong>편의 고전</span>
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
          <SubNav tab={tab} onTab={setTab} />
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

      {tab === 'world' && (
        <main className="wrap">
          <SubNav tab={tab} onTab={setTab} />
          <header className="phead">
            <h1>세계 문학 전집.</h1>
            <p>
              나라별로 꽂아 둔 세계 고전 {worldItems.length}편 · {worldCountries.length}개 나라 ·
              지도의 나라나 아래 칩을 누르면 그 나라의 작품이 모아 보입니다
            </p>
          </header>
          <WorldMap
            works={items.filter(it => it.countryNum).map(it => ({
              work: it.work, title: it.title, country: it.country, countryNum: it.countryNum }))}
            selected={country} onSelect={setCountry}
          />
          <div className="countrychips">
            <button className={country === '' ? 'psz on' : 'psz'} onClick={() => setCountry('')}>
              전체<em>{worldItems.length}</em>
            </button>
            {worldCountries.map(([name, n]) => (
              <button key={name} className={country === name ? 'psz on' : 'psz'}
                onClick={() => setCountry(name)}>
                {name}<em>{n}</em>
              </button>
            ))}
            {koreanItems.length > 0 && (
              <button className={country === '한국' ? 'psz on kr' : 'psz kr'} onClick={() => setCountry('한국')}>
                한국<em>{koreanItems.length}</em>
              </button>
            )}
          </div>
          <div className="grid browsegrid">
            {worldShown.map(it => (
              <Card key={it.work} it={it} note={it.country}
                views={stats?.total?.[it.work]} onPlay={() => play(it)} />
            ))}
            {!worldShown.length && <p className="fine">이 나라에 꽂힌 작품이 아직 없습니다.</p>}
          </div>
        </main>
      )}

      {tab === 'modern' && (
        <main className="wrap">
          <SubNav tab={tab} onTab={setTab} />
          <header className="phead">
            <h1>현대소설.</h1>
            <p>
              요즘 많이 읽히는 소설 {modernItems.length}편 · 결말은 남겨 두고 책이 던지는 질문까지만 담았습니다 ·
              KEI 도서관에 있는 책은 표시해 두었습니다
            </p>
          </header>
          <div className="grid browsegrid">
            {modernItems.map(it => (
              <Card key={it.work} it={it} note={it.kei ? 'KEI 도서관 소장' : undefined}
                views={stats?.total?.[it.work]} onPlay={() => play(it)} />
            ))}
            {!modernItems.length && <p className="fine">아직 공개된 현대소설이 없습니다.</p>}
          </div>
        </main>
      )}

      {tab === 'books' && <BooksTab items={items} play={play} />}

      {playing?.video && (
        <Player
          src={playing.video.url ?? `${API}/api/files/video/${playing.work}/${playing.video.name}`}
          title={playing.title}
          meta={`${playing.video.duration ?? '?'}초 · ${fmtDate(playing.video.updated)}`}
          onClose={() => setPlaying(null)}
        />
      )}
    </>
  )
}
