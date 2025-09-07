
# Laptop Repair AI Backend API

Backend service for **AI-powered laptop repair troubleshooting and engineer booking system**, built with **FastAPI** and **PostgreSQL**, hosted on Render.

Base URL: `https://ent-project.onrender.com`

---

## Features
- User authentication with JWT
- AI-powered troubleshooting steps
- Interactive step-by-step troubleshooting
- Engineer discovery by location
- Booking management (with engineer/admin confirmation)
- Role-based access control

---

## Setup

### Requirements
- Python 3.10+
- PostgreSQL database

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run locally
```bash
uvicorn app.main:app --reload
```

### Database migrations
```bash
alembic upgrade head
```

### Environment variables (`.env`)
```
DATABASE_URL=postgresql://<user>:<password>@<host>/<db>
JWT_SECRET_KEY=supersecretkey
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Authentication

### Register User
`POST /auth/register`
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "123456",
  "role": "USER"
}
```

### Login
`POST /auth/login`
```json
{
  "email": "john@example.com",
  "password": "123456"
}
```
Response contains `access_token` for authorization.

All protected routes require:
```
Authorization: Bearer <token>
```

---

## Troubleshooting Flow

### 1. Create Problem (Get Steps)
`POST /troubleshoot/`
```json
{
  "laptop_brand": "Dell",
  "laptop_model": "XPS 15",
  "description": "My laptop won't turn on"
}
```
Response:
```json
{
  "id": 1,
  "laptop_brand": "Dell",
  "laptop_model": "XPS 15",
  "description": "My laptop won't turn on",
  "steps": [
    {"id": 1, "step_number": 1, "instruction": "Check power cable", "completed": false},
    {"id": 2, "step_number": 2, "instruction": "Remove battery and retry", "completed": false}
  ]
}
```

### 2. Interactive Step-by-Step
Frontend logic:
1. Show `step 1` → Ask user: "Done?"
2. If yes → call:
`PATCH /troubleshoot/{problem_id}/step/{step_id}`  
```json
{ "message": "Step marked as completed" }
```
3. Fetch next step with `GET /troubleshoot/problems/{problem_id}`  
4. Continue until last step → Ask:  
   - ✅ "Did it work?" → Mark problem solved  
   - ❌ "Still not working?" → Offer engineer booking

---

## Engineer Discovery

### Get Nearby Engineers
`POST /troubleshoot/engineers/nearby`
```json
{
  "latitude": 6.5244,
  "longitude": 3.3792
}
```
Response:
```json
[
  {"id": 2, "name": "Engineer Mike", "email": "mike@fix.com", "distance_km": 5.32}
]
```

---

## Bookings

### Create Booking
`POST /troubleshoot/bookings`
```json
{
  "problem_id": 1,
  "engineer_id": 2,
  "scheduled_time": "2025-09-01T10:00:00"
}
```

### Confirm Booking (Engineer/Admin only)
`PATCH /troubleshoot/bookings/{booking_id}/confirm`
```json
{
  "confirmed": true
}
```
- Engineers can only confirm their own bookings.
- Admin can confirm any booking.

---

## Example Frontend Integration

### JS Example: Troubleshooting Flow
```javascript
async function troubleshootProblem(problem) {
  // 1. Create problem
  let res = await fetch("/troubleshoot/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(problem)
  });
  let data = await res.json();

  let steps = data.steps;
  for (let step of steps) {
    alert("Try this: " + step.instruction);
    let done = confirm("Did you complete this step?");
    if (done) {
      await fetch(`/troubleshoot/${data.id}/step/${step.id}`, { method: "PATCH" });
    } else {
      break;
    }
  }

  let worked = confirm("Did it work?");
  if (!worked) {
    alert("Let's book you an engineer.");
  }
}
```

---

## Roles
- **USER**: can troubleshoot and book engineers
- **ENGINEER**: can confirm bookings assigned to them
- **ADMIN**: full access

---

## Deployment
- Backend hosted on Render at:  
  `https://ent-project.onrender.com`
- PostgreSQL DB hosted on Render

---

## Next Steps
- Add email notifications
- Improve AI troubleshooting prompts
- Payment integration for bookings

---

## License
MIT License
