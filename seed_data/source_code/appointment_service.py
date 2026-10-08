"""
Fictional Training Data - Appointment Service Module
This is a prototype service for healthcare documentation automation training.
NOT FOR PRODUCTION USE.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(BaseModel):
    appointment_id: str
    patient_id: str
    physician_id: str
    scheduled_time: datetime
    duration_minutes: int
    status: AppointmentStatus
    appointment_type: str  # e.g., "consultation", "follow-up", "procedure"
    notes: Optional[str] = None
    # REMOVED: reminder_sent field - requirement not yet implemented
    created_at: datetime


class AppointmentService:
    """Service for managing patient appointments and scheduling."""

    DEFAULT_DURATION = 30  # minutes
    MAX_ADVANCE_DAYS = 90  # Book up to 90 days in advance

    def __init__(self):
        self._appointments: dict[str, Appointment] = {}

    def schedule_appointment(
        self,
        patient_id: str,
        physician_id: str,
        scheduled_time: datetime,
        appointment_type: str = "consultation",
        duration_minutes: int = DEFAULT_DURATION,
        notes: Optional[str] = None
    ) -> Appointment:
        """Schedule a new appointment."""
        # Validate scheduling window
        max_date = datetime.now() + timedelta(days=self.MAX_ADVANCE_DAYS)
        if scheduled_time > max_date:
            raise ValueError(
                f"Cannot schedule appointments more than {self.MAX_ADVANCE_DAYS} days in advance"
            )

        appointment = Appointment(
            appointment_id=f"APT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            patient_id=patient_id,
            physician_id=physician_id,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.SCHEDULED,
            appointment_type=appointment_type,
            notes=notes,
            created_at=datetime.now()
        )
        self._appointments[appointment.appointment_id] = appointment
        return appointment

    def confirm_appointment(self, appointment_id: str) -> Appointment:
        """Mark appointment as confirmed."""
        if appointment_id not in self._appointments:
            raise ValueError(f"Appointment {appointment_id} not found")

        appointment = self._appointments[appointment_id]
        appointment.status = AppointmentStatus.CONFIRMED
        return appointment

    def complete_appointment(self, appointment_id: str) -> Appointment:
        """Mark appointment as completed."""
        if appointment_id not in self._appointments:
            raise ValueError(f"Appointment {appointment_id} not found")

        appointment = self._appointments[appointment_id]
        appointment.status = AppointmentStatus.COMPLETED
        return appointment

    def cancel_appointment(
        self,
        appointment_id: str,
        reason: Optional[str] = None
    ) -> Appointment:
        """Cancel an appointment."""
        if appointment_id not in self._appointments:
            raise ValueError(f"Appointment {appointment_id} not found")

        appointment = self._appointments[appointment_id]
        appointment.status = AppointmentStatus.CANCELLED
        if reason:
            appointment.notes = f"Cancelled: {reason}"
        return appointment

    def get_appointments_for_physician(
        self,
        physician_id: str,
        date: Optional[datetime] = None
    ) -> List[Appointment]:
        """Get appointments for a physician, optionally filtered by date."""
        appointments = [
            a for a in self._appointments.values()
            if a.physician_id == physician_id
        ]

        if date:
            start_of_day = date.replace(hour=0, minute=0, second=0)
            end_of_day = date.replace(hour=23, minute=59, second=59)
            appointments = [
                a for a in appointments
                if start_of_day <= a.scheduled_time <= end_of_day
            ]

        return appointments

    def get_appointments_for_patient(self, patient_id: str) -> List[Appointment]:
        """Get all appointments for a patient."""
        return [
            a for a in self._appointments.values()
            if a.patient_id == patient_id
        ]

    def check_in_patient(self, appointment_id: str) -> Appointment:
        """Mark patient as checked in for appointment."""
        if appointment_id not in self._appointments:
            raise ValueError(f"Appointment {appointment_id} not found")

        appointment = self._appointments[appointment_id]

        # Per spec v1.2: Check-in allowed up to 15 minutes before scheduled time
        # This rule is currently hardcoded but should be configurable per clinic
        time_until = appointment.scheduled_time - datetime.now()
        if time_until > timedelta(minutes=15):
            raise ValueError("Cannot check in more than 15 minutes before appointment")

        appointment.status = AppointmentStatus.IN_PROGRESS
        return appointment


# TODO: Implement appointment reminders via patient notification preferences
# Referenced in requirements but not yet implemented
# def send_appointment_reminder(self, appointment_id: str) -> bool:
#     pass
