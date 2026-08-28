import { NextRequest, NextResponse } from 'next/server'

// 관리자 화면과 쓰기 API 를 잠근다 — 사내망 포함 어디서든 비밀번호를 요구한다.
//
// 한동안 사내망은 무인증으로 열어 두었는데, 터널이 공개 도메인으로 뚫려 있고
// 관리자에는 발행·승인이 있다. "비밀번호도 없이 노출되어 있다"는 지적대로
// 예외를 없앤다. 자격은 admin/.env.local 에만 둔다(저장소에 올라가지 않는다).
//
// 공개 페이지가 쓰는 읽기 API(GET)는 그대로 연다 — 잠그면 홈이 죽는다.

const WRITE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export function middleware(req: NextRequest) {
  const needsGuard =
    req.nextUrl.pathname.startsWith('/admin') || WRITE.has(req.method)
  if (!needsGuard) return NextResponse.next()

  const user = process.env.ADMIN_USER
  const pass = process.env.ADMIN_PASS
  if (!user || !pass) {
    // 외부인데 자격이 설정돼 있지 않다 — 열어 둘 수는 없으므로 막는다.
    return new NextResponse('관리자 자격이 설정되지 않았습니다', { status: 403 })
  }

  const header = req.headers.get('authorization') ?? ''
  if (header.startsWith('Basic ')) {
    const raw = atob(header.slice(6))
    const i = raw.indexOf(':')                        // 비밀번호에 콜론이 있을 수 있다
    if (i > 0 && raw.slice(0, i) === user && raw.slice(i + 1) === pass) {
      return NextResponse.next()
    }
  }
  return new NextResponse('관리자 인증이 필요합니다', {
    status: 401,
    headers: { 'WWW-Authenticate': 'Basic realm="Bard admin", charset="UTF-8"' },
  })
}

export const config = { matcher: ['/admin/:path*', '/api/:path*'] }
