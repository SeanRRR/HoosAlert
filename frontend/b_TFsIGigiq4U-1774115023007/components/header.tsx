"use client"

import { Home, Shield, BookOpen, User } from "lucide-react"
import { useRouter, usePathname } from "next/navigation"

const navItems = [
  { name: "Home", icon: Home, path: "/" },
  { name: "Resources", icon: BookOpen, path: "/resources" },
]

export function Header() {
  const router = useRouter()
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
            <button
              key={item.name}
              onClick={() => router.push(item.path)}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              }`}
            >
              <Icon className="w-4 h-4" />
              {item.name}
            </button>
          )
        })}

      </nav>

      {/* RIGHT: USER */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
          <User className="w-4 h-4 text-primary" />
        </div>
      </div>

    </header>
  )
}