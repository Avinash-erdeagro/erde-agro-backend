# Org Data API — Hierarchy-Scoped FPO & Farmer Endpoints

## Overview

These endpoints return FPO and Farmer data **scoped to the caller's position in the org hierarchy**. No extra parameters are needed to apply the scope — it is applied automatically based on the authenticated user's role and org unit assignment.

| Role | What they see |
|------|---------------|
| `SUPER_ADMIN` | All FPOs and farmers across the entire platform |
| `ORG_USER` | Only FPOs linked to org units **at or below** their assigned node (via materialized path), and only the farmers registered under those FPOs |
| `FPO`, `FARMER` | **403 Forbidden** — these endpoints are not available to them |

**Base URL:** `https://your-domain.com`  
**Auth:** All requests require `Authorization: Bearer <access_token>` (JWT from login).

---

## Authentication

Obtain a JWT token first (ORG_USER / SUPER_ADMIN login):

```bash
curl -X POST https://your-domain.com/auth/login/web/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "area_officer_01",
    "password": "yourpassword"
  }'
```

```json
{
  "success": true,
  "message": "Login successful.",
  "result": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

Use the `access` token as `Bearer <access>` in all subsequent requests.

---

## Endpoints

### 1. `GET /super-admin/org-data/fpos/` — List FPOs

Returns all FPO profiles visible to the authenticated user.

**Query Parameters (all optional):**

| Param | Type | Description |
|-------|------|-------------|
| `org_unit` | integer | Filter FPOs to a specific org unit ID. Must be within your accessible subtree. |

**cURL — All FPOs in scope:**
```bash
curl -X GET https://your-domain.com/super-admin/org-data/fpos/ \
  -H "Authorization: Bearer <access_token>"
```

**cURL — FPOs under a specific org unit:**
```bash
curl -X GET "https://your-domain.com/super-admin/org-data/fpos/?org_unit=3" \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "2 FPO(s) found.",
  "result": [
    {
      "id": 1,
      "fpo_name": "Green Fields FPO",
      "contact_person_name": "Ramesh Kumar",
      "email": "ramesh@greenfields.org",
      "mobile": "+919876543210",
      "locality": {
        "district": "Pune",
        "state": "Maharashtra"
      },
      "org_unit_id": 3,
      "org_unit_name": "Pune Area",
      "farmer_count": 42
    },
    {
      "id": 2,
      "fpo_name": "Kisan Collective",
      "contact_person_name": "Suresh Patil",
      "email": "suresh@kisan.org",
      "mobile": "+917654321098",
      "locality": {
        "district": "Nashik",
        "state": "Maharashtra"
      },
      "org_unit_id": 4,
      "org_unit_name": "Nashik Area",
      "farmer_count": 18
    }
  ]
}
```

**Response fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | FPO profile ID |
| `fpo_name` | string | Registered name of the FPO |
| `contact_person_name` | string | Primary contact |
| `email` | string | |
| `mobile` | string | Format: `+91XXXXXXXXXX` |
| `locality.district` | string \| null | |
| `locality.state` | string \| null | |
| `org_unit_id` | integer \| null | Which org unit this FPO is assigned to. `null` if not yet linked |
| `org_unit_name` | string \| null | Human-readable name of that org unit |
| `farmer_count` | integer | Total farmers registered under this FPO |

---

### 2. `GET /super-admin/org-data/fpos/<id>/` — FPO Detail

Returns full details of a single FPO. Returns `404` if the FPO doesn't exist **or** is outside your hierarchy scope (intentionally indistinguishable).

**cURL:**
```bash
curl -X GET https://your-domain.com/super-admin/org-data/fpos/1/ \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "FPO details fetched.",
  "result": {
    "id": 1,
    "fpo_name": "Green Fields FPO",
    "contact_person_name": "Ramesh Kumar",
    "email": "ramesh@greenfields.org",
    "mobile": "+919876543210",
    "gst_number": "27AABCG1234A1Z5",
    "pan_number": "AABCG1234A",
    "cin_number": "U01100MH2020NPL123456",
    "locality": {
      "district": "Pune",
      "state": "Maharashtra",
      "pin_code": "411001"
    },
    "org_unit_id": 3,
    "org_unit_name": "Pune Area",
    "farmer_count": 42
  }
}
```

**Extra fields vs. list:**

| Field | Type | Notes |
|-------|------|-------|
| `gst_number` | string | |
| `pan_number` | string | |
| `cin_number` | string | |
| `locality.pin_code` | string \| null | Present only in detail response |

---

### 3. `GET /super-admin/org-data/farmers/` — List Farmers

Returns all farmers visible to the authenticated user.

**Query Parameters (all optional, combinable):**

| Param | Type | Description |
|-------|------|-------------|
| `fpo` | integer | Filter to farmers under a specific FPO ID. Must be accessible to you. |
| `org_unit` | integer | Filter to farmers under all FPOs in a specific org unit ID. Must be in your subtree. |

**cURL — All farmers in scope:**
```bash
curl -X GET https://your-domain.com/super-admin/org-data/farmers/ \
  -H "Authorization: Bearer <access_token>"
```

**cURL — Farmers under a specific FPO:**
```bash
curl -X GET "https://your-domain.com/super-admin/org-data/farmers/?fpo=1" \
  -H "Authorization: Bearer <access_token>"
```

**cURL — All farmers under a specific org unit:**
```bash
curl -X GET "https://your-domain.com/super-admin/org-data/farmers/?org_unit=3" \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "3 farmer(s) found.",
  "result": [
    {
      "id": 10,
      "farmer_name": "Vijay Shinde",
      "contact_number": "+919123456780",
      "locality": {
        "district": "Pune",
        "state": "Maharashtra"
      },
      "fpo_id": 1,
      "fpo_name": "Green Fields FPO"
    },
    {
      "id": 11,
      "farmer_name": "Anita Mane",
      "contact_number": "+918765432190",
      "locality": {
        "district": "Pune",
        "state": "Maharashtra"
      },
      "fpo_id": 1,
      "fpo_name": "Green Fields FPO"
    },
    {
      "id": 12,
      "farmer_name": "Prakash Jadhav",
      "contact_number": "+919988776655",
      "locality": null,
      "fpo_id": null,
      "fpo_name": null
    }
  ]
}
```

**Response fields:**

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | Farmer profile ID |
| `farmer_name` | string | |
| `contact_number` | string | Format: `+91XXXXXXXXXX` |
| `locality.district` | string \| null | |
| `locality.state` | string \| null | |
| `fpo_id` | integer \| null | FPO this farmer is registered under. `null` if not linked |
| `fpo_name` | string \| null | |

---

### 4. `GET /super-admin/org-data/farmers/<id>/` — Farmer Detail

Returns full details of a single farmer. Returns `404` if not found or outside your hierarchy scope.

**cURL:**
```bash
curl -X GET https://your-domain.com/super-admin/org-data/farmers/10/ \
  -H "Authorization: Bearer <access_token>"
```

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Farmer details fetched.",
  "result": {
    "id": 10,
    "farmer_name": "Vijay Shinde",
    "contact_number": "+919123456780",
    "aadhaar_number": "XXXX-XXXX-1234",
    "locality": {
      "district": "Pune",
      "state": "Maharashtra",
      "pin_code": "411001"
    },
    "fpo_id": 1,
    "fpo_name": "Green Fields FPO"
  }
}
```

**Extra fields vs. list:**

| Field | Type | Notes |
|-------|------|-------|
| `aadhaar_number` | string \| null | Only in detail |
| `locality.pin_code` | string \| null | Only in detail |

---

## Error Responses

All errors follow the same envelope format:

```json
{
  "success": false,
  "message": "<reason>",
  "result": null
}
```

| HTTP Status | Scenario |
|-------------|----------|
| `401 Unauthorized` | Missing, malformed, or expired JWT token |
| `403 Forbidden` | Authenticated but role is not `SUPER_ADMIN` or `ORG_USER`; or `?fpo` / `?org_unit` filter points to a resource outside your scope |
| `404 Not Found` | Detail endpoint — ID not found **or** outside your hierarchy scope |

---

## Common Frontend Patterns

### Check if result is empty
```js
if (response.result.length === 0) {
  // Show "No FPOs found" message
}
```

### Handle scope-based 403 on filter
```js
// If user passes ?org_unit= that isn't theirs
if (!response.success && httpStatus === 403) {
  showError(response.message); // "Org unit not found or not accessible."
}
```

### Pagination
These endpoints return **all records** in scope (no pagination currently). For large datasets, use the `?org_unit=` or `?fpo=` filters to narrow results on the frontend before displaying.

### Typical data flow for displaying hierarchy → FPOs → Farmers

```
1. GET /auth/hierarchy/units/           → fetch accessible org units (for a dropdown/tree)
2. GET /super-admin/org-data/fpos/?org_unit=<selected_id>   → FPOs in that unit
3. GET /super-admin/org-data/farmers/?fpo=<selected_fpo_id> → Farmers in that FPO
```

---

## Related Endpoints

| Purpose | Endpoint |
|---------|----------|
| Get accessible org unit tree | `GET /auth/hierarchy/units/` |
| Get subtree of a specific unit | `GET /auth/hierarchy/units/<id>/subtree/` |
| Hierarchy levels (names) | `GET /auth/hierarchy/levels/` |
| Platform stats (counts) | `GET /super-admin/stats/overview/` |
| Per-FPO stats | `GET /super-admin/stats/fpos/` |
