"use client"

import { Shield, Phone, AlertTriangle, Heart, Bus, BookOpen } from "lucide-react"

export default function ResourcesPage() {
  return (
    <div className="min-h-screen bg-background p-10">

      {/* HEADER */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold">Campus Resources</h1>
        <p className="text-muted-foreground mt-2">
          Quick access to UVA safety, health, and student support services.
        </p>
      </div>

      {/* GRID */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">

        {/* EMERGENCY */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="text-red-500" />
            <h2 className="font-semibold">Emergency</h2>
          </div>
          <ul className="text-sm space-y-2">
            <li>🚨 Emergency: <a href="tel:911" className="hover:underline font-bold">911</a></li>
            <li>🚓 UVA Police: <a href="tel:+14349247166" className="hover:underline">(434) 924-7166</a></li>
            <li>
              🔵{" "}
              <a href="https://veoci.com/v/p/dashboard/pg9g6m" target="_blank" className="hover:underline">
                Blue Light Phones across Grounds
              </a>
            </li>
          </ul>
        </div>

        {/* SAFETY */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="text-blue-500" />
            <h2 className="font-semibold">Safety Services</h2>
          </div>
          <ul className="text-sm space-y-2">
            <li>
              🛡️{" "}
              <a href="https://ambassadors.uvapolice.virginia.edu/safe-walk-students" target="_blank" className="hover:underline">
                UVA Safety Escort Service
              </a>
            </li>
            <li>
              🚨{" "}
              <a href="https://uvaemergency.virginia.edu/uva-alerts" target="_blank" className="hover:underline">
                Emergency Alerts System
              </a>
            </li>
            <li>
              👮{" "}
              <a href="https://uvapolice.virginia.edu/" target="_blank" className="hover:underline">
                UVA Police Department
              </a>
            </li>
          </ul>
        </div>

        {/* HEALTH */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Heart className="text-pink-500" />
            <h2 className="font-semibold">Health & Wellness</h2>
          </div>
          <ul className="text-sm space-y-2">
            <li>
              🏥{" "}
              <a href="https://www.studenthealth.virginia.edu/" target="_blank" className="hover:underline">
                Student Health Center
              </a>
            </li>
            <li>
              🧠{" "}
              <a href="https://mentalhealthservices.studenthealth.virginia.edu/" target="_blank" className="hover:underline">
                CAPS (Counseling Services)
              </a>
            </li>
            <li>
              🏨{" "}
              <a href="https://www.medicalcenter.virginia.edu/" target="_blank" className="hover:underline">
                UVA Medical Center
              </a>
            </li>
            <li>
              💊{" "}
              <a href="https://www.uvahealth.com/find-care/services/pharmacy" target="_blank" className="hover:underline">
                Pharmacy Services
              </a>
            </li>
          </ul>
        </div>

        {/* TRANSPORT */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Bus className="text-green-500" />
            <h2 className="font-semibold">Transportation</h2>
          </div>
          <ul className="text-sm space-y-2">
            <li>
              🚌{" "}
              <a href="https://parking.virginia.edu/uts-serviceroutes" target="_blank" className="hover:underline">
                UVA Bus System
              </a>
            </li>
            <li>
              🌙{" "}
              <a href="https://parking.virginia.edu/uts-ondemand" target="_blank" className="hover:underline">
                Night Pilot Safety Shuttle
              </a>
            </li>
            <li>
              🧭{" "}
              <a href="https://uva.transloc.com/routes" target="_blank" className="hover:underline">
                UVA Transloc
              </a>
            </li>
          </ul>
        </div>

        {/* ACADEMIC */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="text-purple-500" />
            <h2 className="font-semibold">Academic Support</h2>
          </div>
          <ul className="text-sm space-y-2">
            <li>
              📚{" "}
              <a href="https://advising.virginia.edu/" target="_blank" className="hover:underline">
                Academic Advising
              </a>
            </li>
            <li>
              🏫{" "}
              <a href="https://studentaffairs.virginia.edu/staff" target="_blank" className="hover:underline">
                Dean of Students Office
              </a>
            </li>
            <li>
              📖{" "}
              <a href="https://writingrhetoric.as.virginia.edu/welcome-writing-center" target="_blank" className="hover:underline">
                Writing Center
              </a>
            </li>
            <li>
              💼{" "}
              <a href="https://career.virginia.edu/" target="_blank" className="hover:underline">
                UVA Career Center
              </a>
            </li>
          </ul>
        </div>

        {/* REPORTING */}
        <div className="bg-card border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <Phone className="text-orange-500" />
            <h2 className="font-semibold">Reporting & Help</h2>
          </div>
          <ul className="text-sm space-y-2">
            <li>
              🚨{" "}
              <a href="https://report.virginia.edu/" target="_blank" className="hover:underline">
                Anonymous UVA Reporting
              </a>
            </li>
            <li>
              👮{" "}
              <a href="https://uvapolice.virginia.edu/report-crime" target="_blank" className="hover:underline">
                Report to UVA Police
              </a>
            </li>
          </ul>
        </div>

      </div>
    </div>
  )
}