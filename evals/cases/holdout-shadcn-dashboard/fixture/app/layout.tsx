import "./globals.css"
import { SiteNav } from "@/components/site-nav"

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen">
        <SiteNav />
        <div className="flex-1">{children}</div>
      </body>
    </html>
  )
}
