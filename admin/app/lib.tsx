'use client'

import { useEffect } from 'react'

// 브라우저가 접속한 호스트를 그대로 쓴다. 127.0.0.1 로 고정하면
// 원격에서 열었을 때 브라우저가 자기 자신을 가리켜 fetch 가 실패한다.
// 빈 문자열 = 같은 출처. next.config.js 의 rewrites 가 /api 를 :8010 으로 넘긴다.
// 호스트를 직접 조립하면 터널 도메인에서 포트가 없어 전부 실패한다(실측).
export const API = process.env.NEXT_PUBLIC_API ?? ''

export type Work = {
  work: string; version: string; title: string
  sentences: string[]; passed: boolean | null; issues: string[]; updated?: string
  region?: string   // 어디 이야기 — works/categories.json 이 정한다
  genre?: string    // 어떤 이야기
  blurb?: string    // 카드에 얹는 한 줄 미끼 — works/blurbs.json
  mood?: string     // 폰트 묶음(동양·서정 등 여섯)
  season?: string        // 계절 추천관 — works/seasons.json
  season_note?: string   // 왜 이 계절인가 한 줄
  country?: string       // 작품이 태어난 나라 — works/countries.json (세계 문학 전집·지도)
  country_code?: string  // ISO 3166-1 alpha-3
  country_num?: string   // world-atlas 숫자 id
  era?: string           // '고전' | '현대' — 사실파일이 소개형이면 현대소설
  kei?: boolean          // KEI 도서관 소장 여부(사실파일 [소장] 줄)
}
/** 이전 판 — output/<work>/prev/<stamp>/ (scripts/archive_prev.py). 새 판과 나란히 비교하는 용도. */
export type Prev = {
  stamp: string; when: string; final: string | null; duration: number | null; size: number
  frames: string[]; keyframes: string[]; clips: number; sentences: string[] | null; title: string | null
  has_treatment: boolean; has_prompts: boolean
}
export type Video = {
  name: string; size: number; duration: number | null
  kind: 'final' | 'night' | 'scene' | 'other'; version: string; updated: string
  url?: string           // 시청 호스트: 이메일에 묶인 서명 URL(백엔드가 채움)
}
export type Book = {
  rank: number; title: string; author: string; isbn: string; loans: number; holding: string
  publisher?: string; year?: string; cover?: string; cls?: string   // 정보나루 서지·표지·대주제
  difference?: number; base_rank?: number; past_rank?: number       // 급상승(최근 7일 순위 상승폭)
  callno?: string        // KEI 청구기호 — 서가에서 찾을 때 쓴다
  status?: string        // 대출 상태
  delta?: number | null  // 지난달 대비 순위 변화. null = 지난달에 없던 책
  bridge?: { work: string; title: string; why: string }   // 이어지는 우리 고전
}

/** 책방 한 권 = 우리 영상이 있는 책. 순위는 정보나루 지난달 전국 대출 순위(가장 많이 읽힌 판 기준). */
export type OurBook = {
  work: string; title: string; author: string; isbn: string
  edition_title: string; edition_author: string; publisher: string; year: string
  cover: string; description: string
  rank: number | null; rank_month: string; month_loans: number; total_loans: number
  history: { month: string; loans: number; rank: number | null }[]; editions: number
  edition_kind: string   // 원작 | 청소년판 | 어린이판 | 그림책·만화판 — 순위·표지의 기준이 된 판
  holding: string   // paper | ebook | both | none | unknown(확인 중)
  callno: string; status: string
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

export type NavItem = { id: string; label: string; children?: { id: string; label: string }[] }

/** 상단 네비 — 공개/관리자 공용. children 이 있으면 마우스를 얹거나 초점이 들어올 때
 *  드롭다운으로 펼친다(추천작품 ▸ 계절 추천 · 세계 문학 전집). 부모를 누르면 하위 첫
 *  항목으로 간다 — 터치 화면에는 hover 가 없기 때문. */
export function TopNav({ items, tab, onTab, right }: {
  items: NavItem[]
  tab: string
  onTab: (id: string) => void
  right?: React.ReactNode
}) {
  return (
    <nav className="gnav">
      <a className="brand" href="/">
        {/* 좁은 화면(≤640px)에서는 글자 없는 마크만 남겨 메뉴 자리를 내준다(globals.css) */}
        <img className="brand-lockup" src="/brand/bard-lockup.svg" alt="Bard" />
        <img className="brand-icon" src="/brand/bard-icon-sm.svg" alt="Bard" />
      </a>
      <div className="gmenu">
        {items.map(it => {
          const kids = it.children ?? []
          const on = tab === it.id || kids.some(k => k.id === tab)
          if (!kids.length) {
            return (
              <button key={it.id} className={on ? 'gm on' : 'gm'} onClick={() => onTab(it.id)}>
                {it.label}
              </button>
            )
          }
          return (
            <div key={it.id} className="gmwrap">
              <button className={on ? 'gm on' : 'gm'} aria-haspopup="true" aria-expanded={on}
                onClick={() => onTab(kids.some(k => k.id === tab) ? tab : kids[0].id)}>
                {it.label}<span className="gcaret" aria-hidden>▾</span>
              </button>
              <div className="gsub" role="menu">
                {kids.map(k => (
                  <button key={k.id} role="menuitem" className={tab === k.id ? 'gs on' : 'gs'}
                    onClick={() => onTab(k.id)}>
                    {k.label}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
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
        {/* 다운로드 버튼·우클릭 저장·PiP 를 막는다. 화면 녹화까지는 못 막는다 — 억제가 목적. */}
        <video src={src} controls autoPlay playsInline preload="metadata"
          controlsList="nodownload noremoteplayback" disablePictureInPicture
          onContextMenu={e => e.preventDefault()} />
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
