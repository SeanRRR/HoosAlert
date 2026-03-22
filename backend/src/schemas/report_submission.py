from pydantic import BaseModel


class ReportSubmission(BaseModel):
    incidentType: str
    location: str
    computingId: str
    description: str | None = None
