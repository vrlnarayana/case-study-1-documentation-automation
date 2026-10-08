# Appointment Service Requirements

**Status:** Fictional Training Document  
**Version:** 1.1  
**Domain:** Healthcare Appointment Scheduling  
**Purpose:** Prototype specification for documentation automation training

---

## Overview

The Appointment Service manages patient scheduling, physician availability, and appointment lifecycle for the healthcare system.

## Functional Requirements

### AR-001: Appointment Scheduling
- Patients can be scheduled for appointments up to 90 days in advance
- Default appointment duration is 30 minutes
- Appointment types: consultation, follow-up, procedure, emergency

### AR-002: Appointment Lifecycle
- Appointments progress through: SCHEDULED → CONFIRMED → IN_PROGRESS → COMPLETED
- Alternative path: SCHEDULED → CANCELLED or NO_SHOW
- Status changes must be timestamped

### AR-003: Patient Check-in
- Patients can check in up to 15 minutes before scheduled time
- Early check-in (more than 15 min prior) should be rejected
- Late check-in policy TBD (requirement incomplete)

### AR-004: Cancellation
- Appointments can be cancelled with reason
- Cancellation reason is optional but encouraged
- Cancelled slots become available for rebooking

### AR-005: Physician Schedule View
- System shall display all appointments for a physician on a given date
- Appointments sorted by scheduled time
- Include patient name and appointment type

### AR-006: Patient History
- System shall display appointment history for a patient
- Include status, physician, and outcomes
- Filterable by date range

### AR-007: Appointment Reminders
- System shall send appointment reminders (requirement incomplete - mechanism TBD)
- Reminders should be sent 24 hours before appointment
- Patient notification preferences to be defined

---

## Non-Functional Requirements

### AR-NF-001: Performance
- Schedule query response time < 300ms
- Support concurrent scheduling for multiple physicians

### AR-NF-002: Data Retention
- Appointment history retained for 10 years
- Deleted/cancelled appointments retained for audit (7 years)

---

## Constraints

- Maximum 20 appointments per physician per day
- No double-booking of physician time slots
- Emergency appointments bypass standard scheduling constraints

---

## Open Questions

1. **Missing:** Late check-in policy not defined
2. **Missing:** Appointment reminder mechanism not specified (SMS, email, phone?)
3. **Missing:** Patient notification preferences schema
4. **Ambiguous:** "Emergency appointments bypass constraints" - define what constraints

---

**Note:** This is fictional training data for documentation automation system development.
