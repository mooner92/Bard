'use client'

import { useEffect, useMemo, useState } from 'react'
import { API, Player, TopNav, Video, Work, fmtDate, vLabel, vOrder } from '../lib'

type Tab = 'script' | 'keyframes' | 'videos'

export default function Admin() {
  const [works, setWorks] = useState<Work[]>([])
  const [covers, setCovers] = useState<Record<string, string>>({})
  const [openWork, setOpenWork] = useState<string | null>(null)
  const [sel, setSel] = useState<Work | null>(null)
  const [draft, setDraft] = useState<string[]>([])
  const [videos, setVideos] = useState<Video[]>([])
  const [keyframes, setKeyframes] = useState<string[]>([])
  const [tab, setTab] = useState<Tab>('script')
  const [showScenes, setShowScenes] = useState(false)
  const [playing, setPlaying] = useState<Video | null>(null)
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
  }, [])

  // 작품별로 묶고 생성순 내림차순 — 맨 앞이 현행
  const byWork = useMemo(() => {
    const m = new Map<string, Work[]>()
    for (const w of works) m.set(w.work, [...(m.get(w.work) ?? []), w])
    return [...m.entries()].map(([k, v]) =>
      [k, v.sort((a, b) => vOrder(b.version) - vOrder(a.version))] as const)
  }, [works])

  const group = openWork ? byWork.find(([n]) => n === openWork)?.[1] ?? [] : []
  const [current, ...olds] = group

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
  const finals = videos.filter(v => v.kind === 'final')
  const scenes = videos.filter(v => v.kind === 'scene')

  const Row = ({ w, big }: { w: Work; big?: boolean }) => (
    <button className={`ver ${big ? 'big' : ''} ${sel?.version === w.version ? 'on' : ''}`} onClick={() => openVersion(w)}>
      <span className={w.passed ? 'dot ok' : 'dot no'} />
      <span className="vtext">
        <span className="vname">{vLabel(w.version)}</span>
        <span className="vmeta">{w.sentences.length}문장 · {fmtDate(w.updated)}</span>
      </span>
      <span className={w.passed ? 'pill ok' : 'pill no'}>{w.passed ? '통과' : `${w.issues.length}건`}</span>
    </button>
  )

  return (
    <>
      <TopNav
        tab="admin" onTab={() => {}}
        items={[{ id: 'admin', label: '관리자' }]}
        right={<a className="ghost" href="/">공개 페이지</a>}
      />

      {!openWork ? (
        <main className="wrap">
          <header className="phead">
            <h1>어떤 작품을 다듬을까요.</h1>
            <p>카드를 눌러 버전을 확인합니다.</p>
          </header>
          <div className="grid">
            {byWork.map(([name, items]) => (
              <button key={name} className="vcard" onClick={() => { setOpenWork(name); setSel(null) }}>
                <span className="thumb">
                  {covers[name]
                    ? <img src={`${API}/api/files/keyframe/${name}/${covers[name]}`} alt="" />
                    : <span className="ph" />}
                </span>
                <span className="vtitle">{items[0]?.title ?? name}</span>
                <span className="fine">{items.length}개 버전 · 검증통과 {items.filter(i => i.passed).length}</span>
              </button>
            ))}
          </div>
        </main>
      ) : (
        <div className="shell">
          <aside className="side">
            <button className="back" onClick={() => { setOpenWork(null); setSel(null) }}>← 작품 고르기</button>
            <p className="slabel2">현행</p>
            {current && <Row w={current} big />}
            {olds.length > 0 && (
              <>
                <p className="slabel2">Olds</p>
                {olds.map(w => <Row key={w.version} w={w} />)}
              </>
            )}
          </aside>

          <section className="work">
            {!sel ? (
              <div className="empty"><p className="fine">왼쪽에서 버전을 선택하세요.</p></div>
            ) : (
              <>
                <header className="head">
                  <div>
                    <h1 className="title">{sel.title}</h1>
                    <p className="sub">
                      {vLabel(sel.version)} · {chars}자 · 약 {(chars / 6.67).toFixed(1)}초 · {fmtDate(sel.updated)}
                      {sel.passed ? <em className="tag ok">검증 통과</em> : <em className="tag no">{sel.issues.length}건</em>}
                    </p>
                  </div>
                  <div className="hright">
                    <div className="tabs">
                      {(['script', 'keyframes', 'videos'] as Tab[]).map(t => (
                        <button key={t} className={tab === t ? 'tab on' : 'tab'} onClick={() => setTab(t)}>
                          {t === 'script' ? '대본'
                            : t === 'keyframes' ? `키프레임${keyframes.length ? ` ${keyframes.length}` : ''}`
                              : `완성본${finals.length ? ` ${finals.length}` : ''}`}
                        </button>
                      ))}
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
                        {draft.map((s, i) => (
                          <div key={i} className="line">
                            <span className="idx">{i + 1}</span>
                            <textarea value={s} rows={2}
                              onChange={e => setDraft(d => d.map((x, j) => (j === i ? e.target.value : x)))} />
                            <span className={`count ${s.length > 33 || s.length < 22 ? 'bad' : ''}`}>{s.length}</span>
                          </div>
                        ))}
                      </div>
                      <div className="panel">
                        <p className="plabel">검증</p>
                        {sel.issues?.length
                          ? <ul className="issues">{sel.issues.map((m, i) => <li key={i}>{m}</li>)}</ul>
                          : <p className="fine">위반 없음. 다음 단계로 진행할 수 있습니다.</p>}
                      </div>
                    </div>
                  )}

                  {tab === 'keyframes' && (keyframes.length ? (
                    <div className="gal">
                      {keyframes.map(n => (
                        <figure key={n}>
                          <img src={`${API}/api/files/keyframe/${sel.work}/${n}`} alt={n} />
                          <figcaption className="fine">{n}</figcaption>
                        </figure>
                      ))}
                    </div>
                  ) : <p className="fine">키프레임이 아직 없습니다.</p>)}

                  {tab === 'videos' && (
                    <>
                      <div className="gal">
                        {finals.map(v => (
                          <figure key={v.name}>
                            <button className="thumb vid" onClick={() => setPlaying(v)}>
                              <span className="ph dark" /><span className="play sm">▶</span>
                            </button>
                            <figcaption>
                              <span className="vname">{v.version}</span>
                              <span className="fine">{v.duration ?? '?'}초 · {(v.size / 1048576).toFixed(1)}MB</span>
                              <span className="fine">{fmtDate(v.updated)}</span>
                            </figcaption>
                          </figure>
                        ))}
                        {!finals.length && <p className="fine">완성본이 아직 없습니다.</p>}
                      </div>

                      {scenes.length > 0 && (
                        <>
                          <button className="ghost more" onClick={() => setShowScenes(s => !s)}>
                            {showScenes ? '장면 클립 접기' : `장면 클립 ${scenes.length}개 펼치기`}
                          </button>
                          {showScenes && (
                            <div className="gal">
                              {scenes.map(v => (
                                <figure key={v.name}>
                                  <button className="thumb vid" onClick={() => setPlaying(v)}>
                                    <span className="ph dark" /><span className="play sm">▶</span>
                                  </button>
                                  <figcaption>
                                    <span className="vname">{v.version}</span>
                                    <span className="fine">{v.duration ?? '?'}초</span>
                                  </figcaption>
                                </figure>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      )}

      {playing && sel && (
        <Player
          src={`${API}/api/files/video/${sel.work}/${playing.name}`}
          title={`${sel.title} · ${playing.version}`}
          meta={`${playing.duration ?? '?'}초 · ${fmtDate(playing.updated)}`}
          onClose={() => setPlaying(null)}
        />
      )}
    </>
  )
}
