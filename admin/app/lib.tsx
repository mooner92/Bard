'use client'

import { useEffect } from 'react'

// 브라우저가 접속한 호스트를 그대로 쓴다. 127.0.0.1 로 고정하면
// 원격에서 열었을 때 브라우저가 자기 자신을 가리켜 fetch 가 실패한다.
export const API =
  process.env.NEXT_PUBLIC_API ??
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8010`
    : 'http://127.0.0.1:8010')

export type Work = {
  work: string; version: string; title: string
  sentences: string[]; passed: boolean | null; issues: string[]; updated?: string
}
export type Video = {
  name: string; size: number; duration: number | null
  kind: 'final' | 'scene' | 'other'; version: string; updated: string
}
export type Book = {
  rank: number; title: string; author: string; isbn: string; loans: number; holding: string
}

/** ISO 8601 UTC -> 'MM/DD HH:mm' (로컬) */
export function fmtDate(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}/${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 버전 문자열의 숫자를 뽑아 생성순으로 세운다 (v2 < v3 < v3_1 < v4) */
export const vOrder = (v: string) =>
  (v.match(/\d+/g) ?? ['0']).map(Number).reduce((a, b) => a * 100 + b, 0)

export const vLabel = (v: string) => v.replace(/^narration_?/, '') || '초판'

/** 상단 네비 — 공개/관리자 공용 */
export function TopNav({ items, tab, onTab, right }: {
  items: { id: string; label: string }[]
  tab: string
  onTab: (id: string) => void
  right?: React.ReactNode
}) {
  return (
    <nav className="gnav">
      <a className="brand" href="/">aivideo</a>
      <div className="gmenu">
        {items.map(it => (
          <button key={it.id} className={tab === it.id ? 'gm on' : 'gm'} onClick={() => onTab(it.id)}>
            {it.label}
          </button>
        ))}
      </div>
      <div className="gright">{right}</div>
    </nav>
  )
}

/** 모달 팝업 플레이어 — ESC/바깥 클릭 닫기 */
export function Player({ src, title, meta, onClose }: {
  src: string; title: string; meta?: string; onClose: () => void
}) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', k)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', k); document.body.style.overflow = '' }
  }, [onClose])

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <video src={src} controls autoPlay playsInline preload="metadata" />
        <div className="modal-meta">
          <span className="modal-title">{title}</span>
          {meta && <span className="fine">{meta}</span>}
        </div>
        <button className="modal-x" onClick={onClose} aria-label="닫기">✕</button>
      </div>
    </div>
  )
}

export function PlayIcon({ size = 22 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden>
      <path d="M8 5.5v13l11-6.5z" />
    </svg>
  )
}
