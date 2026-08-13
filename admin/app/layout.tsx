export const metadata = { title: 'aivideo 관리자' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ margin: 0, background: '#f8f9fa' }}>{children}</body>
    </html>
  )
}
