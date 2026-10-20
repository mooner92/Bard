import { NextRequest, NextResponse } from 'next/server'
import { createRemoteJWKSet, jwtVerify } from 'jose'

// 두 호스트, 두 얼굴.
//
//  - 관리자 호스트(bard.excusa.uk): Access 이메일 허용목록 + 아래 비밀번호 쿠키.
//    /admin 과 쓰기 API 를 잠근다(기존 방식 그대로).
//  - 시청 호스트(WATCH_HOSTS, 기본 watch.bard.excusa.uk): Access 가 "아무 이메일이나
//    One-time PIN" 으로 들여보낸다. 여기서는 /admin·쓰기 API·관리자용 읽기 API 가
//    **존재하지 않는다**(404). 시청 호스트가 뚫려도 관리자 진입점이 없다.
//
// 신원: Access 가 origin 으로 넘기는 JWT(Cf-Access-Jwt-Assertion)를 검증해 이메일을
// 꺼내고, x-bard-viewer 헤더에 실어 백엔드로 넘긴다. 백엔드는 이 이메일로 영상 URL 에
// 서명하고(링크 공유 무효), 요청을 기록하고(폭주 시 특정), 이메일당 재생 횟수를 제한한다.
// 클라이언트가 보낸 x-bard-* 헤더는 언제나 버린다 — 여기서만 채운다.
//
// AUD 태그(CF_ACCESS_AUD_WATCH)가 없으면 JWT 를 검증할 수 없어 Access 가 얹어 준 이메일
// 헤더를 그대로 믿는다. 터널 뒤에서만 도달 가능한 동안은 안전하지만, 태그를 넣는 것이 맞다.
//
// 브라우저 Basic 인증은 이 환경에서 두 번이나 ERR_TOO_MANY_RETRIES 를 냈다
// (크롬이 401 응답에 자동 재시도를 반복하다 스스로 끊는다). 인증 창 대신
// 우리가 그린 로그인 페이지에서 비밀번호를 받고, 맞으면 서명 쿠키를 심는다.
// 비밀번호는 admin/.env.local 에만 있다(저장소에 올라가지 않는다).

const WRITE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const WATCH_HOSTS = (process.env.WATCH_HOSTS ?? 'watch.bard.excusa.uk')
  .split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
const TEAM = process.env.CF_ACCESS_TEAM ?? ''            // 예: aidt-kei
const AUD_WATCH = process.env.CF_ACCESS_AUD_WATCH ?? ''
const AUD_ADMIN = process.env.CF_ACCESS_AUD_ADMIN ?? ''
const JWKS = TEAM
  ? createRemoteJWKSet(new URL(`https://${TEAM}.cloudflareaccess.com/cdn-cgi/access/certs`))
  : null

// 시청 호스트에서 열어 두는 API. 나머지는 404 — 프롬프트·검수·작업 큐·도서 API 는 관리자용.
const WATCH_API = [
  /^\/api\/works$/,
  /^\/api\/works\/[^/]+\/(keyframes|videos)$/,
  /^\/api\/featured$/,
  /^\/api\/stats\/summary$/,
  /^\/api\/stats\/view$/,
  /^\/api\/files\/(keyframe|video)\/[^/]+\/[^/]+$/,
  /^\/api\/health$/,
]

async function expected(pass: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256',
    new TextEncoder().encode(`bard-admin:${pass}`))
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('')
}

/** Access 가 확인한 이메일. JWT 검증이 가능하면 검증하고, 아니면 헤더를 믿는다. */
async function accessEmail(req: NextRequest, aud: string): Promise<string> {
  if (JWKS && aud) {
    const jwt = req.headers.get('cf-access-jwt-assertion')
    if (!jwt) return ''
    try {
      const { payload } = await jwtVerify(jwt, JWKS, {
        audience: aud, issuer: `https://${TEAM}.cloudflareaccess.com`,
      })
      return String(payload.email ?? '').toLowerCase()
    } catch {
      return ''
    }
  }
  return (req.headers.get('cf-access-authenticated-user-email') ?? '').toLowerCase()
}

function notFound() {
  return new NextResponse('Not found', { status: 404 })
}

export async function middleware(req: NextRequest) {
  const host = (req.headers.get('host') ?? '').split(':')[0].toLowerCase()
  const path = req.nextUrl.pathname
  const watch = WATCH_HOSTS.includes(host)

  const h = new Headers(req.headers)
  h.delete('x-bard-viewer')
  h.set('x-bard-mode', watch ? 'watch' : 'admin')

  if (watch) {
    if (path.startsWith('/admin')) return notFound()
    if (path.startsWith('/api')) {
      if (!WATCH_API.some(r => r.test(path))) return notFound()
      if (WRITE.has(req.method) && path !== '/api/stats/view') return notFound()
      const email = await accessEmail(req, AUD_WATCH)
      if (!email) return new NextResponse('로그인이 필요합니다', { status: 403 })
      h.set('x-bard-viewer', email)
    }
    return NextResponse.next({ request: { headers: h } })
  }

  // ── 관리자 호스트 ──
  if (AUD_ADMIN && path.startsWith('/api')) {
    // Access 를 거치지 않은 요청(사내망 직접 접근)은 여기서 끝낸다.
    const email = await accessEmail(req, AUD_ADMIN)
    if (!email) return new NextResponse('Access 인증이 필요합니다', { status: 403 })
    h.set('x-bard-viewer', email)
  }
  const isLogin = path === '/admin/login' || path === '/api/admin/login'
  // 조회수 기록은 방문자가 보내는 유일한 쓰기다 — 잠그면 통계가 안 쌓인다.
  const isPublicWrite = path === '/api/stats/view'
  const needsGuard =
    (path.startsWith('/admin') || WRITE.has(req.method)) && !isLogin && !isPublicWrite
  if (!needsGuard) return NextResponse.next({ request: { headers: h } })

  const pass = process.env.ADMIN_PASS
  if (!pass) {
    return new NextResponse('관리자 자격이 설정되지 않았습니다', { status: 403 })
  }
  const got = req.cookies.get('bard_admin')?.value
  if (got && got === await expected(pass)) return NextResponse.next({ request: { headers: h } })

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
