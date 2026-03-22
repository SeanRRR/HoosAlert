let reports: any[] = []

// GET all reports
export async function GET() {
  return Response.json(reports)
}

// POST a new report
export async function POST(req: Request) {
  const body = await req.json()

  const newReport = {
    id: Date.now(),
    incidentType: body.incidentType,
    location: body.location,
    latitude: body.latitude ?? null,
    longitude: body.longitude ?? null,
    computingId: body.computingId,
    createdAt: new Date().toISOString(),
  }

  reports.push(newReport)

  return Response.json(newReport)
}