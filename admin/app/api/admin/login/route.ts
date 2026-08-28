import { createHash } from 'crypto'
import { NextResponse } from 'next/server'

// 비밀번호가 맞으면 서명 쿠키를 심는다. 쿠키 값은 비밀번호의 해시라
// 쿠키가 새어도 비밀번호 자체는 드러나지 않는다.
export async function POST(req: Request) {
  const { password } = await req.json().catch(() => ({ password: '' }))
  const pass = process.env.ADMIN_PASS
  if (!pass || password !== pass) {
    return NextResponse.json({ ok: false }, { status: 401 })
  }
  const token = createHash('sha256').update(`bard-admin:${pass}`).digest('hex')
  const res = NextResponse.json({ ok: true })
  res.cookies.set('bard_admin', token, {
    httpOnly: true, sameSite: 'lax', path: '/', maxAge: 60 * 60 * 24 * 30,
  })
  return res
}
