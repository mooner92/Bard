import { NextRequest, NextResponse } from 'next/server'

// 관리자 화면과 쓰기 API 를 잠근다 — 로그인 페이지 + 쿠키 방식.
//
// 브라우저 Basic 인증은 이 환경에서 두 번이나 ERR_TOO_MANY_RETRIES 를 냈다
// (크롬이 401 응답에 자동 재시도를 반복하다 스스로 끊는다). 인증 창 대신
// 우리가 그린 로그인 페이지에서 비밀번호를 받고, 맞으면 서명 쿠키를 심는다.
// 비밀번호는 admin/.env.local 에만 있다(저장소에 올라가지 않는다).
//
// 공개 페이지가 쓰는 읽기 API(GET)는 그대로 연다 — 잠그면 홈이 죽는다.

const WRITE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

async function expected(pass: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256',
    new TextEncoder().encode(`bard-admin:${pass}`))
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('')
}

export async function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname
  const isLogin = path === '/admin/login' || path === '/api/admin/login'
  // 조회수 기록은 방문자가 보내는 유일한 쓰기다 — 잠그면 통계가 안 쌓인다.
  const isPublicWrite = path === '/api/stats/view'
  const needsGuard =
    (path.startsWith('/admin') || WRITE.has(req.method)) && !isLogin && !isPublicWrite
  if (!needsGuard) return NextResponse.next()

  const pass = process.env.ADMIN_PASS
  if (!pass) {
    return new NextResponse('관리자 자격이 설정되지 않았습니다', { status: 403 })
  }
  const got = req.cookies.get('bard_admin')?.value
  if (got && got === await expected(pass)) return NextResponse.next()

  // API 쓰기는 401 로 끝내고, 화면 요청은 로그인 페이지로 보낸다
  if (path.startsWith('/api')) {
    return new NextResponse('로그인이 필요합니다', { status: 401 })
  }
  const url = req.nextUrl.clone()
  url.pathname = '/admin/login'
  url.search = ''
  return NextResponse.redirect(url)
}

export const config = { matcher: ['/admin/:path*', '/api/:path*'] }
