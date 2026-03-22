"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Select from "react-select"
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import L from "leaflet"

delete (L.Icon.Default.prototype as any)._getIconUrl

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
})

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

function LocationPicker({ setPosition }: any) {
  useMapEvents({
    click(e) {
      setPosition([e.latlng.lat, e.latlng.lng])
    },
  })
  return null
}

export default function ReportPage() {
  const router = useRouter()

  const [incidentType, setIncidentType] = useState<any>(null)
  const [location, setLocation] = useState<any>(null)

  const [customIncident, setCustomIncident] = useState("")
  const [computingId, setComputingId] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  // 📍 MAP STATE
  const [selectedPosition, setSelectedPosition] = useState<[number, number] | null>(null)

  // 🔥 INCIDENT TYPES
  const incidentOptions = [
    { value: "theft", label: "Theft" },
    { value: "shooter", label: "Shooter" },
    { value: "suspicious", label: "Suspicious Activity" },
    { value: "medical", label: "Medical Emergency" },
    { value: "fire", label: "Fire / Hazard" },
    { value: "harassment", label: "Harassment" },
    { value: "noise", label: "Noise Complaint" },
    { value: "other", label: "Other (type custom incident)" },
  ]

 const locationOptions = [
  // 📚 LIBRARIES
  {
    label: "📚 Libraries",
    options: [
      { value: "alderman-library", label: "Alderman Library" },
      { value: "clemons-library", label: "Clemons Library" },
      { value: "shannon-library", label: "Shannon Library" },
      { value: "law-library", label: "Arthur J. Morris Law Library" },
      { value: "music-library", label: "Music Library" },
      { value: "health-sciences-library", label: "Health Sciences Library" },
    ],
  },


  // 🏫 ACADEMIC BUILDINGS
  {
    label: "🏫 Academic Buildings",
    options: [
      { value: "rice-hall", label: "Rice Hall (Computer Science)" },
      { value: "olsson-hall", label: "Olsson Hall (Engineering)" },
      { value: "thornton-hall", label: "Thornton Hall" },
      { value: "chemistry-building", label: "Chemistry Building" },
      { value: "physics-building", label: "Physics Building" },
      { value: "astronomy-building", label: "Astronomy Building" },
      { value: "biology-pavillion", label: "Biology Pavilion" },
      { value: "gilmer-hall", label: "Gilmer Hall" },
      { value: "cavalier-hall", label: "Cavalier Hall" },
      { value: "brooks-hall", label: "Brooks Hall" },
      { value: "ruxton-building", label: "Ruxton Room / Rotating Classrooms" },
    ],
  },


  // 🏛️ CENTRAL GROUNDS
  {
    label: "🏛️ Central Grounds",
    options: [
      { value: "rotunda", label: "The Rotunda" },
      { value: "lawn", label: "The Lawn" },
      { value: "range", label: "The Range" },
      { value: "cabell-hall", label: "Cabell Hall" },
      { value: "newcomb-hall", label: "Newcomb Hall (Student Center)" },
      { value: "madison-hall", label: "Madison Hall" },
      { value: "minor-hall", label: "Minor Hall" },
      { value: "bavaro-hall", label: "Bavaro Hall" },
    ],
  },


  {
  label: "🏠 Upperclass Housing (Houses & Apartments)",
  options: [
    { value: "emmet-house", label: "Emmet House" },
    { value: "dabney-house", label: "Dabney House" },
    { value: "brown-college", label: "Brown College" },
    { value: "watson-webb", label: "Watson-Webb House" },
    { value: "gibson-house", label: "Gibson House" },
    { value: "gildersleeve-house", label: "Gildersleeve House" },
    { value: "coffin-house", label: "Coffin House" },
    { value: "lewis-house", label: "Lewis House" },
    { value: "tucker-house", label: "Tucker House" },
    { value: "dawson-house", label: "Dawson House" },
    { value: "bice-house", label: "Bice House" },
    { value: "weedon-house", label: "Weedon House" },
    { value: "bond-house", label: "Bond House" },
    { value: "page-house", label: "Page House" },
    { value: "crawford-house", label: "Crawford House" },
  ],
},
{
  label: "🏠 First-Year Dorms (McCormick & Alderman Area)",
  options: [
    { value: "mccormick-aldeman-area", label: "McCormick / Alderman Road Area" },


    // McCormick Road Dorms
    { value: "humphreys-house", label: "Humphreys House" },
    { value: "tuttle-dixon", label: "Tuttle-Dixon" },
    { value: "bray-hall", label: "Bray Hall" },
    { value: "cauthen-house", label: "Cauthen House" },
    { value: "dillard-dorms", label: "Dillard Residence Area" },


    // Alderman Road Dorms
    { value: "dunglison-hall", label: "Dunglison Hall" },
    { value: "dulaney-house", label: "Dulaney House" },
    { value: "fitzhugh-house", label: "Fitzhugh House" },
    { value: "gibson-hall-dorm", label: "Gibson Hall (Dorm)" },
    { value: "lile-maupin", label: "Lile-Maupin Hall" },
  ],
},
{
  label: "🏠 Language Houses / Special Interest",
  options: [
    { value: "french-house", label: "French House" },
    { value: "spanish-house", label: "Spanish House" },
    { value: "german-house", label: "German House" },
    { value: "russian-house", label: "Russian House" },
    { value: "international-residence", label: "International Residential College (IRC)" },
    { value: "brown-college-program", label: "Brown College (Leadership Program House)" },
  ],
},
  // 🍽️ DINING
  {
    label: "🍽️ Dining Halls",
    options: [
      { value: "newcomb-dining", label: "Newcomb Dining Hall" },
      { value: "o-hill", label: "O’Hill Dining Hall" },
      { value: "runk-dining", label: "Runk Dining Hall" },
      { value: "fresh-food-company", label: "Fresh Food Company" },
      { value: "burrito-bowl", label: "Crossroads / Student Food Areas" },
    ],
  },


  // 🏥 HEALTH & SAFETY
  {
    label: "🏥 Health & Safety",
    options: [
      { value: "uva-medical-center", label: "UVA Medical Center" },
      { value: "emergency-department", label: "UVA Emergency Department" },
      { value: "student-health", label: "Student Health & Wellness Center" },
      { value: "counseling-center", label: "UVA Counseling & Psychological Services (CAPS)" },
    ],
  },


  // 🏟️ ATHLETICS
  {
    label: "🏟️ Athletics & Recreation",
    options: [
      { value: "scott-stadium", label: "Scott Stadium" },
      { value: "jpja", label: "John Paul Jones Arena" },
      { value: "aq-center", label: "Aquatic & Fitness Center (AFC)" },
      { value: "annex-gym", label: "Slaughter Recreation Center" },
      { value: "gym-runk", label: "Memorial Gymnasium" },
      { value: "football-practice", label: "Football Practice Fields" },
    ],
  },


  // 🌳 CAMPUS HOTSPOTS / COMMON AREAS
  {
    label: "🌳 Campus Hotspots",
    options: [
      { value: "the-grass", label: "The Grass" },
      { value: "mad-bowl", label: "Madison Bowl" },
      { value: "the-steps", label: "The Steps (Amphitheater area)" },
      { value: "pavilion-gardens", label: "Pavilion Gardens" },
      { value: "hospital-bridge", label: "Hospital Bridge" },
      { value: "emory-garden", label: "Emmet Ivy Corridor / Gardens" },
    ],
  },
  { value: "other", label: "Other (pin on map)" },
  ]

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const finalIncident =
      incidentType?.value === "other"
        ? customIncident
        : incidentType?.label

    const finalLocation =
      location?.value === "other"
        ? selectedPosition
          ? `Lat: ${selectedPosition[0]}, Lng: ${selectedPosition[1]}`
          : ""
        : location?.label

    const payload = {
    incidentType: finalIncident,
    location: finalLocation,

    latitude: selectedPosition?.[0] || null,
    longitude: selectedPosition?.[1] || null,

    computingId: computingId.trim(),
    }

    if (!payload.incidentType || !payload.location || !payload.computingId) {
      alert("Please complete all required fields.")
      return
    }

    setIsSubmitting(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error("Failed to submit")

      alert("Report submitted successfully!")
      router.push("/")
    } catch (err) {
      alert("Error submitting report")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">

      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg bg-white rounded-2xl shadow-lg p-8 space-y-6"
      >
        <h1 className="text-2xl font-bold">Report Incident</h1>

        {/* INCIDENT TYPE */}
        <div>
          <label className="block mb-2 font-medium">Incident Type</label>

          <Select
            options={incidentOptions}
            value={incidentType}
            onChange={(value) => setIncidentType(value)}
            placeholder="Search incident type..."
          />

          {incidentType?.value === "other" && (
            <input
              type="text"
              value={customIncident}
              onChange={(e) => setCustomIncident(e.target.value)}
              placeholder="Type custom incident..."
              className="w-full mt-3 border p-3 rounded-lg"
              required
            />
          )}
        </div>

        {/* LOCATION */}
        <div>
          <label className="block mb-2 font-medium">Location</label>

          <Select
            options={locationOptions}
            value={location}
            onChange={(value) => {
              setLocation(value)
              setSelectedPosition(null)
            }}
            placeholder="Search UVA location..."
          />

          {/* 📍 MAP APPEARS HERE */}
          {location?.value === "other" && (
            <div className="mt-4">
              <div className="h-[300px] rounded-xl overflow-hidden border">
                <MapContainer
  center={[38.0336, -78.5080]}
  zoom={15}
  minZoom={14}
  maxZoom={19}
  maxBounds={[
    [38.00, -78.55],  // southwest
    [38.07, -78.45],  // northeast
  ]}
  maxBoundsViscosity={1.0}
  scrollWheelZoom={true}
  className="h-full w-full"
>
                  <TileLayer
                    attribution='&copy; OpenStreetMap'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  <LocationPicker setPosition={setSelectedPosition} />

                  {selectedPosition && (
                    <Marker position={selectedPosition} />
                  )}
                </MapContainer>
              </div>

              {selectedPosition && (
                <p className="text-sm text-gray-600 mt-2">
                  📍 Selected: {selectedPosition[0].toFixed(5)},{" "}
                  {selectedPosition[1].toFixed(5)}
                </p>
              )}
            </div>
          )}
        </div>

        {/* COMPUTING ID */}
        <div>
          <label className="block mb-2 font-medium">Computing ID</label>
          <input
            type="text"
            value={computingId}
            onChange={(e) => setComputingId(e.target.value)}
            placeholder="e.g. abc123"
            className="w-full border p-3 rounded-lg"
            required
          />
        </div>

        {/* BUTTONS */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => router.push("/")}
            className="flex-1 py-3 rounded-xl border"
          >
            Cancel
          </button>

          <button
            type="submit"
            disabled={isSubmitting}
            className="flex-1 py-3 rounded-xl bg-red-600 text-white font-semibold hover:bg-red-700"
          >
            {isSubmitting ? "Submitting..." : "Submit Report"}
          </button>
        </div>

      </form>
    </div>
  )
}