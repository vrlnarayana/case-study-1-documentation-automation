"""
Fictional Training Data - Patient Service Module
This is a prototype service for healthcare documentation automation training.
NOT FOR PRODUCTION USE.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class Patient(BaseModel):
    patient_id: str
    name: str
    date_of_birth: datetime
    medical_record_number: str
    insurance_provider: Optional[str] = None
    primary_physician_id: Optional[str] = None


class PatientService:
    """Service for managing patient records and basic information."""

    def __init__(self):
        self._patients: dict[str, Patient] = {}

    def register_patient(self, patient: Patient) -> Patient:
        """Register a new patient in the system."""
        if patient.patient_id in self._patients:
            raise ValueError(f"Patient {patient.patient_id} already exists")
        self._patients[patient.patient_id] = patient
        return patient

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """Retrieve patient by ID."""
        return self._patients.get(patient_id)

    def update_patient(self, patient_id: str, updates: dict) -> Patient:
        """Update patient information."""
        if patient_id not in self._patients:
            raise ValueError(f"Patient {patient_id} not found")
        current = self._patients[patient_id]
        # Apply updates (simplified for prototype)
        for field, value in updates.items():
            if hasattr(current, field):
                setattr(current, field, value)
        return current

    def list_patients_by_physician(self, physician_id: str) -> List[Patient]:
        """Get all patients assigned to a specific physician."""
        return [
            p for p in self._patients.values()
            if p.primary_physician_id == physician_id
        ]


# TODO: Add patient consent tracking (referenced in meeting notes but not implemented)
# def record_consent(self, patient_id: str, consent_type: str, granted: bool):
#     pass
