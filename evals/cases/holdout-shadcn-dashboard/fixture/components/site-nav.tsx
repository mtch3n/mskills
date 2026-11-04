import { ChartBar, Gear, House } from "@phosphor-icons/react/dist/ssr"

const ITEMS = [
  { href: "/", label: "Home", icon: House },
  { href: "/reports", label: "Reports", icon: ChartBar },
  { href: "/settings", label: "Settings", icon: Gear },
]

export function SiteNav() {
  return (
    <nav className="w-52 border-r p-3">
      {ITEMS.map((item) => (
        <a key={item.href} href={item.href} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent">
          <item.icon className="size-4" />
          {item.label}
        </a>
      ))}
    </nav>
  )
}
