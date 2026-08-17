import { NextRequest, NextResponse } from 'next/server'

// 관리자 화면과 쓰기 API 를 잠근다.
//
// 경로만 / 와 /admin 으로 나뉘어 있었을 뿐 접근 제어는 없었다. 외부 도메인이 열려
// 있으므로 그대로 두면 승인·발행·featured 편집이 바깥에 그대로 노출된다.
// 공개 페이지와 **읽기** API 는 잠그지 않는다 — 그쪽은 열려 있어야 한다.
//
// 비밀번호는 admin/.env.local 의 ADMIN_USER / ADMIN_PASS 로만 준다.
// 값이 없으면 통과시킨다 — 개발 중에 자기 서버를 못 열면 곤란하다.

const WRITE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export function middleware(req: NextRequest) {
  const guard =
    req.nextUrl.pathname.startsWith('/admin') || WRITE.has(req.method)
  if (!guard) return NextResponse.next()

  const user = process.env.ADMIN_USER
  const pass = process.env.ADMIN_PASS
  if (!user || !pass) return NextResponse.next()   // 미설정 = 잠그지 않음

  const header = req.headers.get('authorization') ?? ''
  if (header.startsWith('Basic ')) {
    // 콜론은 비밀번호에 들어갈 수 있으므로 첫 콜론에서만 자른다.
    const raw = atob(header.slice(6))
    const i = raw.indexOf(':')
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
