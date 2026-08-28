'use client'

import { useState } from 'react'

/** 관리자 로그인. 브라우저 Basic 인증이 크롬에서 재시도 루프를 일으켜
 *  (ERR_TOO_MANY_RETRIES, 두 번 실측) 우리 화면으로 대신한다. */
export default function AdminLogin() {
  const [pw, setPw] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr('')
    const r = await fetch('/api/admin/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw }),
    }).catch(() => null)
    setBusy(false)
    if (r?.ok) { location.href = '/admin'; return }
    setErr('비밀번호가 맞지 않습니다.')
  }

  return (
    <main className="login">
      <form className="loginbox" onSubmit={submit}>
        <h1>관리자</h1>
        <p className="fine">계속하려면 비밀번호를 입력하세요.</p>
        <input
          type="password" value={pw} onChange={e => setPw(e.target.value)}
          placeholder="비밀번호" autoFocus aria-label="관리자 비밀번호"
        />
        {err && <p className="loginerr">{err}</p>}
        <button className="loginbtn" disabled={busy || !pw}>
          {busy ? '확인 중…' : '들어가기'}
        </button>
      </form>
    </main>
  )
}
