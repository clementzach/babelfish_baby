# API Reference - BabelFish Baby

Quick reference for all API endpoints.

## Base URL
```
http://localhost:8000
```

## Authentication

All API endpoints (except auth endpoints) require authentication via session cookie.

### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "string",
  "password": "string",
  "email": "string" (optional)
}
```

**Response** (200 OK):
```json
{
  "user_id": 1,
  "username": "john_doe"
}
```

**Sets**: Session cookie (httponly, secure)

**Errors**:
- 400: Username already exists
- 422: Invalid input (username too short, password too weak)

---

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):
```json
{
  "user_id": 1,
  "username": "john_doe"
}
```

**Sets**: Session cookie

**Errors**:
- 401: Invalid credentials
- 429: Too many login attempts

---

### Logout
```http
POST /auth/logout
```

**Response** (200 OK):
```json
{
  "success": true
}
```

**Clears**: Session cookie

---

## Cry Management

### Record New Cry
```http
POST /api/cries/record
Content-Type: multipart/form-data
Cookie: session=...

audio_file: <WAV file>
recorded_at: "2026-01-10T14:30:00Z"
```

**Response** (200 OK):
```json
{
  "cry_id": 42,
  "status": "processing"
}
```

**Background**: Triggers AI prediction pipeline asynchronously

**Errors**:
- 401: Not authenticated
- 413: File too large (> 10MB)
- 422: Invalid audio format or duration > 60 seconds

---

### Get Cry History
```http
GET /api/cries/history?limit=50&offset=0
Cookie: session=...
```

**Response** (200 OK):
```json
[
  {
    "cry_id": 42,
    "recorded_at": "2026-01-10T14:30:00Z",
    "recorded_at_relative": "2 hours ago",
    "reason": "Tired",
    "reason_source": "ai",
    "solution": "Rocked to sleep",
    "solution_source": "ai",
    "notes": "Evening fussiness pattern detected",
    "validation_status": null,
    "needs_labeling": false,
    "has_audio": true,
    "chat_message_count": 0
  },
  {
    "cry_id": 41,
    "recorded_at": "2026-01-10T12:15:00Z",
    "recorded_at_relative": "4 hours ago",
    "reason": "Hungry",
    "reason_source": "user",
    "solution": "Fed bottle",
    "solution_source": "user",
    "notes": "2 hours after last feeding",
    "validation_status": true,
    "needs_labeling": false,
    "has_audio": true,
    "chat_message_count": 3
  }
]
```

**Query Parameters**:
- `limit`: Max results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)

**Errors**:
- 401: Not authenticated

---

### Get Cry Details
```http
GET /api/cries/{cry_id}
Cookie: session=...
```

**Response** (200 OK):
```json
{
  "cry_id": 42,
  "user_id": 1,
  "audio_file_path": "./audio_files/user_1/20260110_143000_cry_42.wav",
  "recorded_at": "2026-01-10T14:30:00Z",
  "recorded_at_formatted": "January 10, 2026 at 2:30 PM",
  "reason": "Tired",
  "reason_source": "ai",
  "solution": "Rocked to sleep",
  "solution_source": "ai",
  "notes": "Evening fussiness pattern detected",
  "validation_status": null,
  "created_at": "2026-01-10T14:30:05Z"
}
```

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Cry not found

---

### Get Cry Audio
```http
GET /api/cries/{cry_id}/audio
Cookie: session=...
```

**Response** (200 OK):
- Content-Type: `audio/wav`
- Body: Audio file binary data

**Use case**: Audio playback in browser

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Audio file not found

---

### Get Processing Status
```http
GET /api/cries/{cry_id}/status
Cookie: session=...
```

**Response** (200 OK):
```json
{
  "status": "processing"
}
```

OR if complete:
```json
{
  "status": "ready",
  "needs_labeling": false,
  "prediction": {
    "reason": "Tired",
    "solution": "Try rocking to sleep",
    "notes": "Evening fussiness pattern detected",
    "confidence": "normal"
  }
}
```

**Possible status values**:
- `processing`: AI prediction in progress
- `ready`: Prediction complete (or user has < 3 validated, needs manual labeling)
- `failed`: Processing error occurred

**Use case**: Poll this endpoint after upload to know when prediction is ready

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Cry not found

---

### Update Cry Details
```http
PUT /api/cries/{cry_id}/update
Content-Type: application/json
Cookie: session=...

{
  "validation": true
}
```

**To confirm AI prediction:**
```json
{
  "validation": true
}
```

**To update reason, solution, and notes:**
```json
{
  "validation": false,
  "reason": "Pain or discomfort",
  "solution": "Gave gas drops",
  "notes": "Actually was in pain, not tired"
}
```

**All fields are optional** - only include fields you want to update:
```json
{
  "reason": "Hungry",
  "solution": "Fed bottle"
}
```

**Response** (200 OK):
```json
{
  "cry_id": 42,
  "reason": "Pain or discomfort",
  "reason_source": "user",
  "solution": "Gave gas drops",
  "solution_source": "user",
  "notes": "Actually was in pain, not tired",
  "validation_status": false
}
```

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Cry not found
- 422: Notes too long (> 500 chars)

---

### Update Notes
```http
PUT /api/cries/{cry_id}/notes
Content-Type: application/json
Cookie: session=...

{
  "notes": "Updated notes about this cry"
}
```

**Response** (200 OK):
```json
{
  "cry_id": 42,
  "notes": "Updated notes about this cry"
}
```

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Cry not found
- 422: Notes too long (> 500 chars)

---

## Chat

### Send Chat Message
```http
POST /api/chat/{cry_id}/message
Content-Type: application/json
Cookie: session=...

{
  "message": "How do I get them to sleep?"
}
```

**Response** (200 OK):
```json
{
  "bot_response": "For a tired baby, try establishing a calming bedtime routine. Swaddling, white noise, and gentle rocking can help. Ensure the room is dark and quiet. If fussiness persists, consult your pediatrician.",
  "timestamp": "2026-01-10T14:35:22Z"
}
```

**Context used by AI**:
- Cry reason and solution
- Time of recording
- Parent's notes
- Previous chat messages in this conversation

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Cry not found
- 422: Message too long (> 1000 chars)
- 429: Rate limit exceeded (30 messages/hour)

---

### Get Chat History
```http
GET /api/chat/{cry_id}/history
Cookie: session=...
```

**Response** (200 OK):
```json
[
  {
    "message_id": 1,
    "sender": "user",
    "message_text": "How do I get them to sleep?",
    "timestamp": "2026-01-10T14:35:15Z"
  },
  {
    "message_id": 2,
    "sender": "bot",
    "message_text": "For a tired baby, try establishing a calming bedtime routine...",
    "timestamp": "2026-01-10T14:35:22Z"
  },
  {
    "message_id": 3,
    "sender": "user",
    "message_text": "Should I swaddle them?",
    "timestamp": "2026-01-10T14:36:00Z"
  }
]
```

**Errors**:
- 401: Not authenticated
- 403: Cry belongs to different user
- 404: Cry not found

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Not logged in or session expired |
| 403 | Forbidden | Logged in but not allowed (e.g., accessing other user's data) |
| 404 | Not Found | Resource doesn't exist |
| 413 | Payload Too Large | File upload exceeds size limit |
| 422 | Unprocessable Entity | Validation error (Pydantic) |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | External API (OpenAI/HuggingFace) is down |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /auth/login | 5 attempts | 15 minutes |
| POST /api/cries/record | 10 uploads | 1 hour |
| POST /api/chat/{cry_id}/message | 30 messages | 1 hour |

---

## Request/Response Examples

### Complete Workflow: New User Records First Cry

#### 1. Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "jane", "password": "secure123"}'
```

#### 2. Record Cry
```bash
curl -X POST http://localhost:8000/api/cries/record \
  -H "Cookie: session=abc123..." \
  -F "audio_file=@baby_cry.wav" \
  -F "recorded_at=2026-01-10T14:30:00Z"

# Response:
# {"cry_id": 1, "status": "processing"}
```

#### 3. Check Status (poll every 2 seconds)
```bash
curl http://localhost:8000/api/cries/1/status \
  -H "Cookie: session=abc123..."

# First response (processing):
# {"status": "processing"}

# After ~5 seconds (ready, but needs labeling since first cry):
# {"status": "ready", "needs_labeling": true}
```

#### 4. Manually Label (since first cry)
```bash
curl -X PUT http://localhost:8000/api/cries/1/update \
  -H "Cookie: session=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"reason": "Hungry", "solution": "Fed bottle", "notes": "3 hours since last feeding"}'
```

#### 5. Record 2nd and 3rd Cry (same manual labeling flow)

#### 6. Record 4th Cry (AI prediction now available!)
```bash
curl -X POST http://localhost:8000/api/cries/record \
  -H "Cookie: session=abc123..." \
  -F "audio_file=@cry_4.wav" \
  -F "recorded_at=2026-01-10T18:30:00Z"

# Poll status...
# {"status": "ready", "prediction": {"reason": "Tired", "solution": "Try rocking to sleep", "notes": "Evening fussiness..."}}
```

#### 7. Validate AI Prediction
```bash
curl -X PUT http://localhost:8000/api/cries/4/update \
  -H "Cookie: session=abc123..." \
  -H "Content-Type": application/json" \
  -d '{"validation": true}'
```

#### 8. Ask for Advice
```bash
curl -X POST http://localhost:8000/api/chat/4/message \
  -H "Cookie: session=abc123..." \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I get them to sleep?"}'

# Response:
# {
#   "bot_response": "For a tired baby in the evening, try...",
#   "timestamp": "2026-01-10T18:35:00Z"
# }
```

---

## WebSocket Endpoints (Future)

Not implemented in MVP, but planned for Phase 3:

```
WS /api/chat/{cry_id}/stream
```

For real-time streaming chat responses.

---

## Frontend Routes (HTML Pages)

These are **not API endpoints**, but HTML pages served by FastAPI:

| Route | Page | Auth Required |
|-------|------|---------------|
| GET / | Login/Register page | No |
| GET /history | Cry history dashboard | Yes |
| GET /record | Audio recording interface | Yes |
| GET /chat/{cry_id} | Chat interface for specific cry | Yes |

---

## Data Models

### User
```typescript
{
  id: number
  username: string
  email: string | null
  created_at: string (ISO 8601)
}
```

### CryInstance
```typescript
{
  cry_id: number
  user_id: number
  audio_file_path: string
  recorded_at: string (ISO 8601)
  reason: string | null  // Free-text reason (e.g., "Hungry", "Tired", "Dirty diaper")
  reason_source: "user" | "ai" | null
  solution: string | null  // Free-text solution (e.g., "Fed bottle", "Rocked to sleep")
  solution_source: "user" | "ai" | null
  notes: string | null
  validation_status: boolean | null  // null=not reviewed, true=confirmed, false=rejected
  created_at: string (ISO 8601)
}
```

### ChatMessage
```typescript
{
  message_id: number
  cry_instance_id: number
  sender: "user" | "bot"
  message_text: string
  timestamp: string (ISO 8601)
}
```

---

## Testing Endpoints

### Using cURL

```bash
# Set session cookie in variable (after login)
SESSION="session=abc123..."

# Get history
curl http://localhost:8000/api/cries/history \
  -H "Cookie: $SESSION"

# Upload audio
curl -X POST http://localhost:8000/api/cries/record \
  -H "Cookie: $SESSION" \
  -F "audio_file=@test.wav" \
  -F "recorded_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Get audio
curl http://localhost:8000/api/cries/1/audio \
  -H "Cookie: $SESSION" \
  -o downloaded.wav
```

### Using Python `requests`

```python
import requests

BASE_URL = "http://localhost:8000"
session = requests.Session()

# Login
response = session.post(f"{BASE_URL}/auth/login", json={
    "username": "jane",
    "password": "secure123"
})

# Upload audio
with open("baby_cry.wav", "rb") as f:
    response = session.post(
        f"{BASE_URL}/api/cries/record",
        files={"audio_file": f},
        data={"recorded_at": "2026-01-10T14:30:00Z"}
    )
    cry_id = response.json()["cry_id"]

# Get history
response = session.get(f"{BASE_URL}/api/cries/history")
cries = response.json()

# Chat
response = session.post(
    f"{BASE_URL}/api/chat/{cry_id}/message",
    json={"message": "How do I soothe the baby?"}
)
print(response.json()["bot_response"])
```

### Using FastAPI Test Client

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Register and login
client.post("/auth/register", json={"username": "test", "password": "test123"})
client.post("/auth/login", json={"username": "test", "password": "test123"})

# Upload (session automatically handled by TestClient)
with open("test.wav", "rb") as f:
    response = client.post("/api/cries/record", files={"audio_file": f})
    assert response.status_code == 200
```

---

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use these for:
- Exploring available endpoints
- Testing requests interactively
- Viewing request/response schemas
- Understanding parameter requirements

---

## API Versioning (Future)

Not implemented in MVP. If needed later:

```
/api/v1/cries/record
/api/v2/cries/record
```

For now, all endpoints are unversioned and considered v1.

---

## CORS Configuration (if needed)

If you later build a separate frontend (React/Vue app on different port):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Not needed for MVP since FastAPI serves templates directly.

---

## Pagination

For endpoints that return lists (e.g., `/api/cries/history`):

**Query parameters**:
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Number to skip (default: 0)

**Example**:
```
GET /api/cries/history?limit=20&offset=40
```

Gets cries 41-60.

**Future enhancement**: Return pagination metadata:
```json
{
  "items": [...],
  "total": 150,
  "limit": 20,
  "offset": 40,
  "has_more": true
}
```

---

## Filtering & Sorting (Future)

Not implemented in MVP, but possible enhancements:

```
GET /api/cries/history?reason=tired&sort=recorded_at:desc
GET /api/cries/history?date_from=2026-01-01&date_to=2026-01-31
GET /api/cries/history?validated=true
GET /api/cries/history?needs_labeling=true
```

---

## Webhook Events (Future)

Not in MVP. Possible future feature:

- `cry.predicted`: AI prediction completed
- `cry.validated`: User validated a prediction
- `chat.message`: New chat message

Users could configure webhook URLs to receive these events.

---

## API Key Authentication (Future)

For mobile app or third-party integrations:

```http
GET /api/cries/history
Authorization: Bearer <api_key>
```

Not needed for MVP (using session cookies).

---

## Rate Limit Headers

When rate limits are implemented, responses include:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1736521200
```

---

## Deprecation Notice Format (Future)

If an endpoint is deprecated:

```
Deprecation: true
Sunset: Sat, 1 Jun 2026 00:00:00 GMT
Link: </api/v2/cries/record>; rel="successor-version"
```

---

This API reference covers all endpoints for the MVP. For implementation details, see TECHNICAL_SPEC_REVISED.md and IMPLEMENTATION_PLAN.md.
