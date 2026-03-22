"use client"

import type { ReactNode } from "react"
import { Header } from "@/components/header"

export default function MainLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <div className="min-h-screen flex flex-col">

      {/* HEADER ONLY FOR MAIN AREA */}
      <div className="h-[80px] sticky top-0 z-40">
        <Header />
      </div>

      {/* PAGE CONTENT */}
      <main className="flex-1">
        {children}
      </main>

    </div>
  )
}
