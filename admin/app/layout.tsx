import './globals.css'

export const metadata = {
  title: 'Bard',
  description: '고전을 짧은 영상으로 다시 읽는 파이프라인',
  icons: { icon: '/brand/bard-icon-sm.svg' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>
}
