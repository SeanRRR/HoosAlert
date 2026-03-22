"use client"

import { Home, Shield, BookOpen } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

const navItems = [
  { name: "Home", icon: Home, path: "/" },
  { name: "Resources", icon: BookOpen, path: "/resources" },
]

export function Header() {
  const pathname = usePathname()

  return (
    <header className="h-full flex items-center justify-between px-8 bg-card border-b border-border">
      
      {/* LEFT: BRAND */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary">
          <Shield className="w-5 h-5 text-primary-foreground" />
        </div>

        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          HoosAlert
        </h1>
      </div>

      {/* CENTER: NAV */}
      <nav className="flex items-center gap-1 bg-secondary rounded-xl p-1.5">

        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.path

          return (
            <Link
              key={item.name}
              href={item.path}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.name}
            </Link>
          )
        })}

      </nav>

      {/* RIGHT: SPACER (keeps nav visually centered) */}
      <div className="w-9 h-9" aria-hidden />

    </header>
  )
}
