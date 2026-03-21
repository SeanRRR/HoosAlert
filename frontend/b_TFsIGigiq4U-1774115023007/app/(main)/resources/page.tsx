"use client"

import { Shield, Phone, AlertTriangle, Heart, Bus, BookOpen, ExternalLink } from "lucide-react"

export default function ResourcesPage() {
  return (
    <div className="h-full overflow-y-auto p-6 md:p-10">

      {/* TITLE */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Campus Resources</h1>
        <p className="text-muted-foreground mt-2">
          Quick access to UVA safety, health, transportation, and student support.
        </p>
      </div>

      {/* GRID */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">

        {/* EMERGENCY */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="text-red-500" />
            <h2 className="font-semibold">Emergency</h2>
          </div>

          <div className="space-y-2 text-sm">
            <p>
              🚨 Emergency:
              <a className="text-red-600 font-semibold ml-1" href="tel:911">
                911
              </a>
            </p>

            <p>
              👮 UVA Police:
              <a className="text-blue-600 ml-1" href="tel:+14349247166">
                (434) 924-7166
              </a>
            </p>

            <a
              href="https://uvaemergency.virginia.edu/"
              target="_blank"
              className="flex items-center gap-1 text-blue-600 mt-2 hover:underline"
            >
              UVA Emergency Info <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* SAFETY */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="text-blue-500" />
            <h2 className="font-semibold">Safety Services</h2>
          </div>

          <div className="space-y-2 text-sm">
            <a
              href="https://uvapolice.virginia.edu/safety-escort"
              target="_blank"
              className="flex items-center gap-1 text-blue-600 hover:underline"
            >
              Safety Escort Service <ExternalLink className="w-4 h-4" />
            </a>

            <a
              href="https://virginia.edu/livesafe"
              target="_blank"
              className="flex items-center gap-1 text-blue-600 hover:underline"
            >
              LiveSafe App <ExternalLink className="w-4 h-4" />
            </a>

            <a
              href="https://uvaemergency.virginia.edu/"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              Emergency Alerts System
            </a>
          </div>
        </div>

        {/* HEALTH */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Heart className="text-pink-500" />
            <h2 className="font-semibold">Health & Wellness</h2>
          </div>

          <div className="space-y-2 text-sm">
            <a
              href="https://www.studenthealth.virginia.edu/"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              Student Health Center
            </a>

            <a
              href="https://www.studenthealth.virginia.edu/caps"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              CAPS (Counseling & Psychological Services)
            </a>

            <a
              href="https://uvahealth.com/"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              UVA Medical Center
            </a>
          </div>
        </div>

        {/* TRANSPORT */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Bus className="text-green-500" />
            <h2 className="font-semibold">Transportation</h2>
          </div>

          <div className="space-y-2 text-sm">
            <a
              href="https://parking.virginia.edu/cat"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              UVA Bus System (CAT)
            </a>

            <a
              href="https://parking.virginia.edu/night-pilot"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              Night Pilot Safety Shuttle
            </a>

            <p>
              🚕 Uber / Lyft pickup zones available across Grounds
            </p>
          </div>
        </div>

        {/* ACADEMIC */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="text-purple-500" />
            <h2 className="font-semibold">Academic Support</h2>
          </div>

          <div className="space-y-2 text-sm">
            <a
              href="https://advising.virginia.edu/"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              Academic Advising
            </a>

            <a
              href="https://writingrhetoric.as.virginia.edu/writing-center"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              Writing Center
            </a>

            <a
              href="https://odos.virginia.edu/"
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              Dean of Students Office
            </a>
          </div>
        </div>

      </div>
    </div>
  )
}