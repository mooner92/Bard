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

export default function Home() {
  const [items, setItems] = useState<Item[]>([])
  const [books, setBooks] = useState<Book[]>([])
  const [period, setPeriod] = useState('')
  const [tab, setTab] = useState('videos')
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
        // 공개 페이지에는 최신 완성본 하나만 노출한다 (압축본 제외)
        const finals = (vid.videos as Video[]).filter(v => v.kind === 'final' && !v.name.includes('compressed'))
        const latest = finals.sort((a, b) => (a.updated < b.updated ? 1 : -1))[0]
        return { work: name, title, cover: kf.images?.[0], video: latest }
      }))
      setItems(rows.filter(r => r.video))
    }).catch(() => {})

    fetch(`${API}/api/books/popular?limit=10`).then(r => r.json())
      .then(d => { setBooks(d.books ?? []); setPeriod(`${d.period?.start} ~ ${d.period?.end}`) })
      .catch(() => {})
  }, [])

  // 캐러셀 자동 회전 — 재생 중에는 멈춘다
  useEffect(() => {
    if (playing || items.length < 2) return
    const t = setInterval(() => setSlide(s => (s + 1) % items.length), 5000)
    return () => clearInterval(t)
  }, [playing, items.length])

  return (
    <>
      <TopNav
        tab={tab} onTab={setTab}
        items={[{ id: 'videos', label: '영상' }, { id: 'books', label: '인기대출도서' }]}
        right={<a className="ghost" href="/admin">관리자</a>}
      />

      {tab === 'videos' ? (
        <main className="wrap">
          <header className="phead">
            <h1>고전을, 30초로.</h1>
            <p>퍼블릭 도메인 문학을 짧은 영상으로 다시 읽습니다.</p>
          </header>

          {items.length > 0 && (
            <section className="hero">
              <div className="viewport">
                <div className="track" style={{ transform: `translateX(-${slide * 100}%)` }}>
                  {items.map(it => (
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
                {items.map((_, i) => (
                  <button key={i} className={i === slide ? 'dot on' : 'dot'}
                    onClick={() => setSlide(i)} aria-label={`${i + 1}번 슬라이드`} />
                ))}
              </div>
            </section>
          )}

          <h2 className="sec">모든 작품</h2>
          <div className="grid">
            {items.map(it => (
              <button key={it.work} className="vcard" onClick={() => setPlaying(it)}>
                <span className="thumb">
                  {it.cover
                    ? <img src={`${API}/api/files/keyframe/${it.work}/${it.cover}`} alt="" />
                    : <span className="ph" />}
                  <span className="play sm"><PlayIcon size={18} /></span>
                </span>
                <span className="vtitle">{it.title}</span>
                <span className="fine">{it.video?.duration ?? '?'}초 · {fmtDate(it.video?.updated)}</span>
              </button>
            ))}
            {!items.length && <p className="fine">아직 공개된 영상이 없습니다.</p>}
          </div>
        </main>
      ) : (
        <main className="wrap">
          <header className="phead">
            <h1>지금 많이 읽는 책.</h1>
            <p>{period || '불러오는 중'} · 전국 도서관 대출 기준</p>
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
