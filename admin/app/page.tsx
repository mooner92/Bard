'use client'

import { useEffect, useState } from 'react'
import { API, Book, PlayIcon, Player, TopNav, Video, Work, fmtDate } from './lib'

type Item = { work: string; title: string; cover?: string; video?: Video }

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

function Card({ it, onPlay }: { it: Item; onPlay: () => void }) {
  return (
    <button className="vcard" onClick={onPlay}>
      <span className="thumb">
        {it.cover
          ? <img src={`${API}/api/files/keyframe/${it.work}/${it.cover}`} alt="" />
          : <span className="ph" />}
        <span className="play sm"><PlayIcon size={18} /></span>
      </span>
      <span className="vtitle">{it.title}</span>
      <span className="fine">{it.video?.duration ?? '?'}초 · {fmtDate(it.video?.updated)}</span>
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
        return { work: name, title, cover: kf.images?.[0], video: latest }
      }))
      setItems(rows.filter(r => r.video))
    }).catch(() => {})

    fetch(`${API}/api/books/popular?limit=30`).then(r => r.json())
      .then(d => {
        setBooks(dedupeBooks(d.books ?? []).slice(0, 20))
        setPeriod(`${d.period?.start} ~ ${d.period?.end}`)
      })
      .catch(() => {})
  }, [])

  // 통상의 미디어 홈 구성: 히어로(대표작) → 신규 섹션, 전체 목록은 상단 네비 별도 탭.
  // 대표 = 사람이 승인한 완성본(kind final). 없으면 최신작으로 채운다.
  const byNew = (a: Item, b: Item) => (a.video!.updated < b.video!.updated ? 1 : -1)
  const featured = items.filter(it => it.video?.kind === 'final')
  const hero = (featured.length ? featured : items.slice().sort(byNew)).slice(0, 5)
  const heroSet = new Set(hero.map(h => h.work))
  const fresh = items.filter(it => !heroSet.has(it.work)).sort(byNew).slice(0, 4)

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
          { id: 'books', label: '인기대출도서' },
        ]}
        right={<a className="ghost" href="/admin">관리자</a>}
      />

      {tab === 'home' && (
        <main className="wrap">
          <header className="phead">
            <h1>책 속 세계를, 1분 안에.</h1>
            <p>문학 작품을 짧은 세로 영상으로 다시 읽습니다.</p>
          </header>

          {hero.length > 0 && (
            <section className="hero">
              <div className="viewport">
                <div className="track" style={{ transform: `translateX(-${cur * 100}%)` }}>
                  {hero.map(it => (
                    <button key={it.work} className="slide" onClick={() => setPlaying(it)}>
                      {it.cover
                        ? <img src={`${API}/api/files/keyframe/${it.work}/${it.cover}`} alt="" />
                        : <span className="ph" />}
                      <span className="scrim" />
                      <span className="slabel">
                        <strong>{it.title}</strong>
                        <small>{it.video?.duration ?? '?'}초</small>
                      </span>
                      <span className="play"><PlayIcon size={26} /></span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="dots">
                {hero.map((_, i) => (
                  <button key={i} className={i === cur ? 'dot on' : 'dot'}
                    onClick={() => setSlide(i)} aria-label={`${i + 1}번 슬라이드`} />
                ))}
              </div>
            </section>
          )}

          {fresh.length > 0 && (
            <>
              <h2 className="sec">신규 작품</h2>
              <div className="grid4">
                {fresh.map(it => <Card key={it.work} it={it} onPlay={() => setPlaying(it)} />)}
              </div>
            </>
          )}
        </main>
      )}

      {tab === 'all' && (
        <main className="wrap">
          <header className="phead">
            <h1>모든 작품.</h1>
            <p>{items.length}편 · 최신순</p>
          </header>
          <div className="grid">
            {items.slice().sort(byNew).map(it => (
              <Card key={it.work} it={it} onPlay={() => setPlaying(it)} />
            ))}
            {!items.length && <p className="fine">아직 공개된 영상이 없습니다.</p>}
          </div>
        </main>
      )}

      {tab === 'books' && (
        <main className="wrap">
          <header className="phead">
            <h1>지금 많이 읽는 책.</h1>
            <p>{period || '불러오는 중'} · 전국 도서관 대출 기준 · 같은 책의 권별 중복은 접었습니다</p>
          </header>
          <ol className="books">
            {books.map(b => (
              <li key={b.isbn || b.rank}>
                <span className="rank">{b.rank}</span>
                <span className="btext">
                  <span className="btitle">{b.title}</span>
                  <span className="fine">{b.author} · 대출 {b.loans.toLocaleString()}</span>
                </span>
                <HoldPill h={b.holding} />
              </li>
            ))}
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
