/** @type {import('next').NextConfig} */
// /api 를 백엔드(:8010)로 프록시한다. 프런트가 API 주소를 스스로 조립하면
// 외부 도메인(터널)에서 <도메인>:8010 을 찾다 실패한다(실측: bard.excusa.uk 빈 화면).
// 같은 출처로 넘기면 로컬·사설망·터널 어디서든 그대로 동작하고 CORS 도 필요 없다.
module.exports = {
  reactStrictMode: true,
  devIndicators: false,
  async rewrites() {
    return [{ source: '/api/:path*', destination: 'http://127.0.0.1:8010/api/:path*' }]
  },
}
