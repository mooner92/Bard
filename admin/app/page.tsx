'use client'

import { useEffect, useMemo, useState } from 'react'

// 브라우저가 접속한 호스트를 그대로 쓴다. 127.0.0.1 로 고정하면
// 원격에서 열었을 때 브라우저가 자기 자신을 가리켜 fetch 가 실패한다.
const API =
  process.env.NEXT_PUBLIC_API ??
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8010`
    : 'http://127.0.0.1:8010')

type Work = {
  work: string
  version: string
  title: string
  sentences: string[]
  passed: boolean | null
  issues: string[]
}
type Video = { name: string; size: number; duration: number | null }
type Book = { rank: number; title: string; author: string; isbn: string; loans: number; holding: string }
type Tab = 'script' | 'keyframes' | 'videos'

const label = (v: string) => v.replace(/^narration_?/, '') || '초판'
// 버전 문자열에서 숫자를 뽑아 생성순으로 세운다 (v2 < v3 < v3_1 < v4)
const order = (v: string) => (v.match(/\d+/g) ?? ['0']).map(Number).reduce((a, b) => a * 100 + b, 0)

export default function Page() {
  const [works, setWorks] = useState<Work[]>([])
  const [covers, setCovers] = useState<Record<string, string>>({})
  const [books, setBooks] = useState<Book[]>([])
  const [period, setPeriod] = useState('')
  const [openWork, setOpenWork] = useState<string | null>(null)
  const [sel, setSel] = useState<Work | null>(null)
  const [draft, setDraft] = useState<string[]>([])
  const [videos, setVideos] = useState<Video[]>([])
  const [keyframes, setKeyframes] = useState<string[]>([])
  const [tab, setTab] = useState<Tab>('script')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/works`).then(r => r.json()).then((d: { works: Work[] }) => {
      setWorks(d.works)
      for (const name of new Set(d.works.map(w => w.work))) {
        fetch(`${API}/api/works/${name}/keyframes`).then(r => r.json())
          .then(k => k.images?.[0] && setCovers(c => ({ ...c, [name]: k.images[0] })))
          .catch(() => {})
      }
    }).catch(() => {})
    fetch(`${API}/api/books/popular?limit=10`).then(r => r.json())
      .then(d => { setBooks(d.books ?? []); setPeriod(`${d.period?.start} ~ ${d.period?.end}`) })
      .catch(() => {})
  }, [])

  // 작품별로 묶고, 각 그룹을 생성순 내림차순으로 정렬해 맨 앞을 현행으로 삼는다
  const byWork = useMemo(() => {
    const m = new Map<string, Work[]>()
    for (const w of works) m.set(w.work, [...(m.get(w.work) ?? []), w])
    return [...m.entries()].map(([k, v]) => [k, v.sort((a, b) => order(b.version) - order(a.version))] as const)
  }, [works])

  const group = openWork ? byWork.find(([n]) => n === openWork)?.[1] ?? [] : []
  const current = group[0]
  const olds = group.slice(1)

  function openVersion(w: Work) {
    setSel(w); setDraft([...w.sentences]); setTab('script')
    setVideos([]); setKeyframes([])
    fetch(`${API}/api/works/${w.work}/videos`).then(r => r.json()).then(d => setVideos(d.videos)).catch(() => {})
    fetch(`${API}/api/works/${w.work}/keyframes`).then(r => r.json()).then(d => setKeyframes(d.images)).catch(() => {})
  }

  // 저장하면 서버가 하네스 검증기를 그대로 재실행해 issues 를 돌려준다
  async function save() {
    if (!sel) return
    setSaving(true)
    const res = await fetch(`${API}/api/works/${sel.work}/${sel.version}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sentences: draft }),
    })
    const up = await res.json()
    setSel({ ...sel, ...up })
    setWorks(ws => ws.map(w => (w.work === sel.work && w.version === sel.version ? { ...w, ...up } : w)))
    setSaving(false)
  }

  const chars = draft.reduce((a, s) => a + s.length, 0)
  const dirty = !!sel && draft.join('') !== sel.sentences.join('')

  function VersionRow({ w, big }: { w: Work; big?: boolean }) {
    return (
      <button className={`ver ${big ? 'ver-big' : ''} ${sel?.version === w.version ? 'on' : ''}`} onClick={() => openVersion(w)}>
        <span className={w.passed ? 'dot ok' : 'dot no'} />
        <span className="ver-text">
          <span className="ver-name">{label(w.version)}</span>
          <span className="ver-meta">{w.sentences.length}문장 · {w.sentences.reduce((a, s) => a + s.length, 0)}자</span>
        </span>
        <span className={w.passed ? 'pill pill-ok' : 'pill pill-no'}>{w.passed ? '통과' : `${w.issues.length}건`}</span>
      </button>
    )
  }

  return (
    <>
      <nav className="gnav">
        <button className="brand" onClick={() => { setSel(null); setOpenWork(null) }}>aivideo</button>
        {openWork && <span className="crumb">{group[0]?.title ?? openWork}{sel && ` · ${label(sel.version)}`}</span>}
      </nav>

      {/* ── 로비: 작품 카드 + 인기도서 모니터 ── */}
      {!openWork && (
        <main className="lobby">
          <header className="lobby-head">
            <h1>어떤 작품을 다듬을까요.</h1>
            <p>카드를 눌러 버전을 확인합니다.</p>
          </header>

          <div className="cards">
            {byWork.map(([name, items]) => (
              <article key={name} className="card">
                <button className="card-face" onClick={() => { setOpenWork(name); setSel(null) }}>
                  {covers[name]
                    ? <img src={`${API}/api/files/keyframe/${name}/${covers[name]}`} alt="" />
                    : <span className="ph" />}
                  <span className="scrim" />
                  <span className="card-label">
                    <strong>{items[0]?.title ?? name}</strong>
                    <small>{items.length}개 버전 · 검증통과 {items.filter(i => i.passed).length}</small>
                  </span>
                </button>
              </article>
            ))}
          </div>

          <section className="books">
            <div className="books-head">
              <h2>인기대출도서</h2>
              <span className="fine">{period || '불러오는 중'} · 전국 도서관</span>
            </div>
            {books.length ? (
              <ol className="book-list">
                {books.map(b => (
                  <li key={b.isbn || b.rank}>
                    <span className="rank">{b.rank}</span>
                    <span className="book-text">
                      <span className="book-title">{b.title}</span>
                      <span className="fine">{b.author} · 대출 {b.loans.toLocaleString()}</span>
                    </span>
                    <span className={`pill pill-${b.holding === 'unknown' ? 'wait' : 'ok'}`}>
                      {b.holding === 'unknown' ? '소장 미확인' : b.holding}
                    </span>
                  </li>
                ))}
              </ol>
            ) : <p className="fine">도서 정보를 불러오지 못했습니다.</p>}
          </section>
        </main>
      )}

      {/* ── 작품 상세: 현행 / Olds 분리 ── */}
      {openWork && (
        <div className="shell">
          <aside className="side">
            <button className="back" onClick={() => { setOpenWork(null); setSel(null) }}>← 작품 고르기</button>

            <p className="side-label">현행</p>
            {current && <VersionRow w={current} big />}

            {olds.length > 0 && (
              <>
                <p className="side-label">Olds</p>
                {olds.map(w => <VersionRow key={w.version} w={w} />)}
              </>
            )}
          </aside>

          <section className="work">
            {!sel ? (
              <div className="empty"><p className="lead">왼쪽에서 버전을 선택하세요.</p></div>
            ) : (
              <>
                <header className="head">
                  <div>
                    <h1 className="title">{sel.title}</h1>
                    <p className="sub">
                      {label(sel.version)} · {chars}자 · 약 {(chars / 6.67).toFixed(1)}초
                      {sel.passed ? <em className="tag ok-tag">검증 통과</em> : <em className="tag no-tag">{sel.issues.length}건 미해결</em>}
                    </p>
                  </div>
                  <div className="head-right">
                    <div className="tabs">
                      <button className={tab === 'script' ? 'tab on' : 'tab'} onClick={() => setTab('script')}>대본</button>
                      <button className={tab === 'keyframes' ? 'tab on' : 'tab'} onClick={() => setTab('keyframes')}>키프레임{keyframes.length ? ` ${keyframes.length}` : ''}</button>
                      <button className={tab === 'videos' ? 'tab on' : 'tab'} onClick={() => setTab('videos')}>완성본{videos.length ? ` ${videos.length}` : ''}</button>
                    </div>
                    {tab === 'script' && (
                      <button className="btn" onClick={save} disabled={saving || !dirty}>
                        {saving ? '검증 중' : dirty ? '저장하고 재검증' : '변경 없음'}
                      </button>
                    )}
                  </div>
                </header>

                <div className="pane">
                  {tab === 'script' && (
                    <div className="cols">
                      <div>
                        {draft.map((s, i) => {
                          const bad = s.length > 33 || s.length < 22
                          return (
                            <div key={i} className="line">
                              <span className="idx">{i + 1}</span>
                              <textarea value={s} rows={2}
                                onChange={e => setDraft(d => d.map((x, j) => (j === i ? e.target.value : x)))} />
                              <span className={`count ${bad ? 'bad' : ''}`}>{s.length}</span>
                            </div>
                          )
                        })}
                      </div>
                      <div className="panel">
                        <p className="panel-label">검증</p>
                        {sel.issues?.length
                          ? <ul className="issues">{sel.issues.map((m, i) => <li key={i}>{m}</li>)}</ul>
                          : <p className="fine">위반 없음. 다음 단계로 진행할 수 있습니다.</p>}
                      </div>
                    </div>
                  )}

                  {tab === 'keyframes' && (keyframes.length ? (
                    <div className="gallery">
                      {keyframes.map(n => (
                        <figure key={n}>
                          <img src={`${API}/api/files/keyframe/${sel.work}/${n}`} alt={n} />
                          <figcaption className="fine">{n}</figcaption>
                        </figure>
                      ))}
                    </div>
                  ) : <p className="fine">키프레임이 아직 없습니다.</p>)}

                  {tab === 'videos' && (videos.length ? (
                    <div className="gallery">
                      {videos.map(v => (
                        <figure key={v.name}>
                          <video controls preload="none" src={`${API}/api/files/video/${sel.work}/${v.name}`} />
                          <figcaption>
                            <span className="strong">{v.name}</span>
                            <span className="fine">{v.duration ?? '?'}초 · {(v.size / 1048576).toFixed(1)}MB</span>
                          </figcaption>
                        </figure>
                      ))}
                    </div>
                  ) : <p className="fine">완성본이 아직 없습니다.</p>)}
                </div>
              </>
            )}
          </section>
        </div>
      )}

      <style jsx global>{`
        :root {
          --blue: #3e6ae1; --ink: #171a20; --graphite: #393c41; --pewter: #5c5e62;
          --silver: #8e8e8e; --line: #eeeeee; --ash: #f7f7f8; --canvas: #ffffff;
          --r-md: 16px; --r-lg: 22px; --ease: 0.28s cubic-bezier(0.4, 0, 0.2, 1);
        }
        * { box-sizing: border-box; }
        html, body { margin: 0; height: 100%; }
        body {
          font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
          font-size: 15px; line-height: 1.6; color: var(--graphite); background: var(--canvas);
          -webkit-font-smoothing: antialiased;
        }
        button { font-family: inherit; cursor: pointer; border: 0; background: none; color: inherit; }
        button:focus-visible { outline: 2px solid var(--blue); outline-offset: 3px; border-radius: 10px; }

        .gnav { height: 56px; display: flex; align-items: center; gap: 14px; padding: 0 28px; border-bottom: 1px solid var(--line); }
        .brand { font-size: 16px; font-weight: 600; color: var(--ink); }
        .crumb { font-size: 14px; color: var(--pewter); }

        .lobby { max-width: 1100px; margin: 0 auto; padding: 52px 28px 80px; }
        .lobby-head h1 { font-size: 32px; font-weight: 600; color: var(--ink); margin: 0 0 6px; line-height: 1.3; }
        .lobby-head p { font-size: 16px; color: var(--pewter); margin: 0 0 36px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 22px; }
        .card-face {
          position: relative; display: block; width: 100%; aspect-ratio: 16 / 10;
          border-radius: var(--r-lg); overflow: hidden; background: var(--ash); transition: transform var(--ease);
        }
        .card-face:active { transform: scale(0.985); }
        .card-face img { width: 100%; height: 100%; object-fit: cover; display: block; }
        .ph { display: block; width: 100%; height: 100%; background: var(--ash); }
        .scrim { position: absolute; inset: 0; background: linear-gradient(to top, rgba(23,26,32,0.62), rgba(23,26,32,0) 55%); }
        .card-label { position: absolute; left: 20px; right: 20px; bottom: 18px; display: flex; flex-direction: column; text-align: left; color: #fff; }
        .card-label strong { font-size: 19px; font-weight: 600; }
        .card-label small { font-size: 13px; opacity: 0.85; }

        /* 인기도서 모니터 */
        .books { margin-top: 56px; }
        .books-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 14px; }
        .books-head h2 { font-size: 20px; font-weight: 600; color: var(--ink); margin: 0; }
        .book-list { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--line); }
        .book-list li { display: flex; align-items: center; gap: 14px; padding: 13px 4px; border-bottom: 1px solid var(--line); }
        .rank { width: 22px; text-align: right; font-size: 13px; color: var(--silver); flex: none; }
        .book-text { display: flex; flex-direction: column; line-height: 1.4; min-width: 0; }
        .book-title { font-size: 15px; color: var(--ink); font-weight: 500; }

        .pill { font-size: 12px; padding: 3px 10px; border-radius: 9999px; margin-left: auto; flex: none; }
        .pill-ok { background: rgba(62,106,225,0.1); color: var(--blue); }
        .pill-no { background: var(--ash); color: var(--pewter); }
        .pill-wait { background: var(--ash); color: var(--silver); }

        .shell { display: grid; grid-template-columns: 268px 1fr; height: calc(100vh - 56px); }
        .side { background: var(--ash); padding: 18px 12px; overflow-y: auto; }
        .back { font-size: 14px; color: var(--pewter); padding: 8px 12px; border-radius: var(--r-md); }
        .back:hover { background: #ececee; }
        .side-label { font-size: 12px; font-weight: 600; color: var(--silver); letter-spacing: 0.04em; margin: 20px 0 8px 12px; }
        .ver {
          width: 100%; display: flex; align-items: center; gap: 10px; padding: 10px 12px;
          border-radius: var(--r-md); text-align: left; transition: background var(--ease);
        }
        .ver:hover { background: #ececee; }
        .ver.on { background: var(--canvas); }
        .ver-big { background: var(--canvas); padding: 14px 12px; }
        .ver-text { display: flex; flex-direction: column; line-height: 1.35; min-width: 0; }
        .ver-name { font-size: 14px; color: var(--ink); font-weight: 500; }
        .ver-meta { font-size: 12px; color: var(--silver); }
        .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
        .dot.ok { background: var(--blue); }
        .dot.no { background: #dcdcde; }

        .work { display: flex; flex-direction: column; min-width: 0; }
        .empty { display: grid; place-items: center; height: 100%; }
        .lead { font-size: 19px; color: var(--silver); }
        .head { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 22px 28px; border-bottom: 1px solid var(--line); flex: none; }
        .title { font-size: 26px; font-weight: 600; color: var(--ink); margin: 0; line-height: 1.25; }
        .sub { font-size: 14px; color: var(--pewter); margin: 4px 0 0; }
        .tag { font-style: normal; margin-left: 10px; font-weight: 600; }
        .ok-tag { color: var(--blue); }
        .no-tag { color: var(--graphite); }
        .head-right { display: flex; align-items: center; gap: 12px; flex: none; }
        .tabs { display: flex; gap: 2px; background: var(--ash); border-radius: 9999px; padding: 4px; }
        .tab { border-radius: 9999px; padding: 8px 16px; font-size: 14px; color: var(--pewter); transition: background var(--ease), color var(--ease); }
        .tab.on { background: var(--canvas); color: var(--ink); font-weight: 600; }
        .btn { background: var(--blue); color: #fff; border-radius: 9999px; padding: 10px 20px; font-size: 14px; font-weight: 500; transition: background var(--ease); }
        .btn:disabled { background: var(--ash); color: var(--silver); cursor: default; }

        .pane { flex: 1; overflow-y: auto; padding: 26px 28px 40px; min-height: 0; }
        .cols { display: grid; grid-template-columns: 1fr 300px; gap: 26px; align-items: start; }
        .panel { background: var(--ash); border-radius: var(--r-lg); padding: 20px; position: sticky; top: 0; }
        .panel-label { font-size: 13px; font-weight: 600; color: var(--silver); margin: 0 0 10px; }
        .issues { margin: 0; padding-left: 18px; font-size: 13px; color: var(--graphite); }
        .issues li { margin-bottom: 8px; line-height: 1.5; }
        .line { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
        .idx { width: 18px; text-align: right; color: var(--silver); font-size: 13px; padding-top: 13px; flex: none; }
        .line textarea {
          flex: 1; min-width: 0; font-family: inherit; font-size: 15px; line-height: 1.6; color: var(--ink);
          background: var(--ash); border: 1px solid transparent; border-radius: var(--r-md);
          padding: 11px 15px; resize: vertical; transition: background var(--ease), border-color var(--ease);
        }
        .line textarea:focus { outline: none; background: var(--canvas); border-color: var(--blue); }
        .count { width: 28px; text-align: right; font-size: 12px; color: var(--silver); padding-top: 15px; flex: none; }
        .count.bad { color: var(--blue); font-weight: 600; }

        .gallery { display: flex; flex-wrap: wrap; gap: 26px; }
        .gallery figure { margin: 0; }
        .gallery img, .gallery video { border-radius: var(--r-md); display: block; }
        .gallery img { width: 150px; }
        .gallery video { width: 240px; }
        .gallery figcaption { display: flex; flex-direction: column; gap: 2px; margin-top: 10px; }
        .strong { font-size: 14px; font-weight: 500; color: var(--ink); }
        .fine { font-size: 13px; color: var(--silver); margin: 0; }

        @media (max-width: 900px) {
          .shell { grid-template-columns: 210px 1fr; }
          .cols { grid-template-columns: 1fr; }
          .panel { position: static; }
        }
      `}</style>
    </>
  )
}
