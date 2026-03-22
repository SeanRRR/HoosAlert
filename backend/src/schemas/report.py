from pydantic import BaseModel

class ReportSubmission(BaseModel):
    incident_type: str
    location: str
    computingID: str
    timestamp: str  
    # Add other fields from the schema as needed
    # Example:
    # location: str
    # timestamp: str
