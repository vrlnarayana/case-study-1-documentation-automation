# API Documentation Style Guide - Example Document

**Status:** Fictional Training Document  
**Purpose:** Example of existing documentation style for automation training

---

## Document Structure

All API documentation in this project follows this standard structure:

1. **Overview** - Brief description of the service/module
2. **Authentication** - How to authenticate (if applicable)
3. **Endpoints** - List of available endpoints
4. **Request/Response Schema** - Detailed field descriptions
5. **Error Handling** - Common errors and their meanings
6. **Examples** - Real-world usage examples

---

## Example: Patient Service API

### Overview

The Patient Service manages patient demographic information and medical record associations.

### Authentication

All endpoints require a valid API token in the Authorization header:
```
Authorization: Bearer <token>
```

### Endpoints

#### POST /patients

Register a new patient in the system.

**Request Body:**
```json
{
  "patient_id": "string (required)",
  "name": "string (required)",
  "date_of_birth": "ISO 8601 datetime (required)",
  "medical_record_number": "string (required)",
  "insurance_provider": "string (optional)",
  "primary_physician_id": "string (optional)"
}
```

**Response:**
- `201 Created` - Patient registered successfully
- `409 Conflict` - Patient ID already exists
- `400 Bad Request` - Invalid input data

#### GET /patients/{patient_id}

Retrieve patient information by ID.

**Path Parameters:**
- `patient_id` (string, required) - Unique patient identifier

**Response:**
```json
{
  "patient_id": "P-12345",
  "name": "John Doe",
  "date_of_birth": "1985-03-15T00:00:00Z",
  "medical_record_number": "MRN-98765",
  "insurance_provider": "Blue Cross",
  "primary_physician_id": "PH-789"
}
```

#### PUT /patients/{patient_id}

Update patient information.

**Request Body:**
Partial update - only include fields to change.

```json
{
  "insurance_provider": "Aetna",
  "primary_physician_id": "PH-456"
}
```

**Response:**
- `200 OK` - Update successful
- `404 Not Found` - Patient not found

---

## Writing Conventions

### Field Descriptions
- Always include data type in parentheses
- Mark required vs optional explicitly
- Include validation constraints where applicable

### Code Examples
- Use real-world values, not placeholder text like "string"
- Include complete request/response pairs
- Show error cases, not just success paths

### Error Messages
- Use consistent format: `ERROR_CODE: Human-readable description`
- Include troubleshooting guidance for common errors

---

## Review Checklist

Before publishing documentation:

- [ ] All endpoints documented
- [ ] Request/response schemas complete
- [ ] Authentication requirements specified
- [ ] Error codes listed with descriptions
- [ ] Examples tested and verified
- [ ] Links to related documentation included
- [ ] Version information current

---

**Note:** This is fictional training data for documentation automation system development.
