# Hierarchy & Role Management API

Base URL: `http://localhost:8001`  
All authenticated requests require: `Authorization: Bearer <access_token>`

---

## URL Prefixes

| Prefix          | Purpose                                                                       |
| --------------- | ----------------------------------------------------------------------------- |
| `/auth/`        | Authentication, registration, and read-only hierarchy views                   |
| `/super-admin/` | SUPER_ADMIN-only management (orgs, hierarchy, stats, notifications, payments) |

---

## Roles

| Role          | Description                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| `SUPER_ADMIN` | Full access to everything. Creates orgs, levels, users.                     |
| `ORG_USER`    | Named hierarchy user (e.g. State Head, Area Officer). Sees data below them. |
| `FPO`         | FPO account. Cannot be impersonated.                                        |
| `FARMER`      | Farmer account. Cannot be impersonated.                                     |

---

## 1. Bootstrap (One-time Setup)

The very first `SUPER_ADMIN` must be created via the Django shell since there is no token yet.

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from authapp.models import AppUser

User = get_user_model()
user = User.objects.create_user(username="superadmin", password="yourpassword")
user.is_staff = True
user.save()
AppUser.objects.create(user=user, role=AppUser.Role.SUPER_ADMIN)
```

After this, use the webapp login endpoint to get a token.

---

## 2. Authentication

### Login (SUPER_ADMIN / ORG_USER)

```bash
curl -X POST http://localhost:8001/auth/webapp/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin",
    "password": "yourpassword"
  }'
```

**Response:**

```json
{
  "success": true,
  "message": "Login successful.",
  "result": {
    "access": "<access_token>",
    "refresh": "<refresh_token>",
    "user_name": "superadmin",
    "role": "SUPER_ADMIN"
  }
}
```

### Refresh Token

```bash
curl -X POST http://localhost:8001/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

---

## 3. SUPER_ADMIN — Organization Management

### Create Organization

```bash
curl -X POST http://localhost:8001/super-admin/organizations/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Erde Agro Corp"}'
```

**Response:**

```json
{
  "id": 1,
  "name": "Erde Agro Corp",
  "created_at": "2026-05-08T10:00:00Z"
}
```

### List Organizations

```bash
curl http://localhost:8001/super-admin/organizations/ \
  -H "Authorization: Bearer <super_admin_token>"
```

### Get / Update / Delete Organization

```bash
# GET
curl http://localhost:8001/super-admin/organizations/1/ \
  -H "Authorization: Bearer <super_admin_token>"

# PATCH
curl -X PATCH http://localhost:8001/super-admin/organizations/1/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Erde Agro Corp (Updated)"}'

# DELETE
curl -X DELETE http://localhost:8001/super-admin/organizations/1/ \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 4. SUPER_ADMIN — Hierarchy Level Management

Hierarchy levels define the _named role types_ for an organization.  
`level=1` is the highest. Use incrementing integers for lower levels.

**Example:**

```
level=1  →  "Corporate Admin"
level=2  →  "State Head"
level=3  →  "Area Officer"
```

### Create a Hierarchy Level

```bash
curl -X POST http://localhost:8001/super-admin/hierarchy-levels/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "organization": 1,
    "name": "State Head",
    "level": 2
  }'
```

**Response:**

```json
{
  "id": 2,
  "organization": 1,
  "name": "State Head",
  "level": 2
}
```

### List Hierarchy Levels (filter by org)

```bash
curl "http://localhost:8001/super-admin/hierarchy-levels/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

### Get / Update / Delete a Level

```bash
# PATCH — rename a level
curl -X PATCH http://localhost:8001/super-admin/hierarchy-levels/2/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Regional Head"}'

# DELETE
curl -X DELETE http://localhost:8001/super-admin/hierarchy-levels/2/ \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 5. SUPER_ADMIN — Org Unit (Node) Management

Org units are actual instances of nodes in the tree.  
Example: "Maharashtra Division" is an OrgUnit at the "State Head" level.

Multiple sibling units can share the same `hierarchy_level`.

### Create a Root Org Unit

```bash
curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "organization": 1,
    "hierarchy_level": 1,
    "name": "HQ",
    "parent": null
  }'
```

**Response:**

```json
{
  "id": 1,
  "organization": 1,
  "hierarchy_level": 1,
  "hierarchy_level_name": "Corporate Admin",
  "level_number": 1,
  "name": "HQ",
  "parent": null,
  "path": "/1/",
  "created_at": "2026-05-08T10:05:00Z"
}
```

> `path` is computed automatically. Never send it in requests.

### Create a Child Org Unit

```bash
curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "organization": 1,
    "hierarchy_level": 2,
    "name": "Maharashtra Division",
    "parent": 1
  }'
```

```json
{
  "id": 2,
  "name": "Maharashtra Division",
  "hierarchy_level_name": "State Head",
  "path": "/1/2/",
  "parent": 1
}
```

### Create Sibling Org Unit (same level, different parent or same parent)

```bash
# Another State Head node under the same HQ
curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "organization": 1,
    "hierarchy_level": 2,
    "name": "Karnataka Division",
    "parent": 1
  }'
```

```json
{
  "id": 3,
  "name": "Karnataka Division",
  "hierarchy_level_name": "State Head",
  "path": "/1/3/",
  "parent": 1
}
```

### List Org Units (filter by org)

```bash
curl "http://localhost:8001/super-admin/org-units/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

### Get / Update / Delete Org Unit

```bash
# GET
curl http://localhost:8001/super-admin/org-units/2/ \
  -H "Authorization: Bearer <super_admin_token>"

# PATCH — re-parent a node (all descendant paths update automatically)
curl -X PATCH http://localhost:8001/super-admin/org-units/2/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"parent": 3}'

# DELETE
curl -X DELETE http://localhost:8001/super-admin/org-units/2/ \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 6. SUPER_ADMIN — User Creation

The public `/auth/register/` endpoint only accepts `FPO` and `FARMER`.  
`ORG_USER` and `SUPER_ADMIN` accounts are created here only.

### Create an ORG_USER (assign to an OrgUnit)

```bash
curl -X POST http://localhost:8001/super-admin/users/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "state_head_maharashtra",
    "password": "securepassword123",
    "role": "ORG_USER",
    "org_unit": 2
  }'
```

**Response:**

```json
{
  "success": true,
  "message": "ORG_USER account created successfully.",
  "result": {
    "id": 5,
    "created_username": "state_head_maharashtra",
    "org_unit_name": "Maharashtra Division"
  }
}
```

### Create Another SUPER_ADMIN

```bash
curl -X POST http://localhost:8001/super-admin/users/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin2",
    "password": "securepassword456",
    "role": "SUPER_ADMIN"
  }'
```

---

## 7. SUPER_ADMIN — OrgMembership Management

Memberships link an ORG_USER AppUser to an OrgUnit.  
Creating an ORG_USER via `POST /super-admin/users/` creates the membership automatically.  
Use these endpoints only if you need to reassign a user to a different unit.

### List Memberships (filter by org unit)

```bash
curl "http://localhost:8001/super-admin/memberships/?org_unit=2" \
  -H "Authorization: Bearer <super_admin_token>"
```

### Create a Membership manually

```bash
curl -X POST http://localhost:8001/super-admin/memberships/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "app_user": 5,
    "org_unit": 2
  }'
```

### Update / Delete a Membership

```bash
# PATCH — reassign user to a different unit
curl -X PATCH http://localhost:8001/super-admin/memberships/1/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"org_unit": 3}'

# DELETE — remove from hierarchy
curl -X DELETE http://localhost:8001/super-admin/memberships/1/ \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 8. SUPER_ADMIN — FPO ↔ OrgUnit Links

Links an existing FpoProfile into the hierarchy under an OrgUnit.

### Link an FPO to an OrgUnit

```bash
curl -X POST http://localhost:8001/super-admin/fpo-links/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "fpo_profile": 10,
    "org_unit": 4
  }'
```

**Response:**

```json
{
  "id": 1,
  "fpo_profile": 10,
  "fpo_name": "Pune Farmers Co-op",
  "org_unit": 4,
  "org_unit_name": "Pune Area Office"
}
```

### List FPO Links (filter by org unit)

```bash
curl "http://localhost:8001/super-admin/fpo-links/?org_unit=4" \
  -H "Authorization: Bearer <super_admin_token>"
```

### Update / Delete an FPO Link

```bash
# PATCH — move FPO to a different unit
curl -X PATCH http://localhost:8001/super-admin/fpo-links/1/ \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"org_unit": 5}'

# DELETE
curl -X DELETE http://localhost:8001/super-admin/fpo-links/1/ \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 9. Hierarchy Read Endpoints (SUPER_ADMIN + ORG_USER)

These endpoints remain under `/auth/` and are accessible to both `SUPER_ADMIN` and `ORG_USER`.

### List Accessible Org Units

Returns all OrgUnit nodes at or below the caller's position.  
SUPER_ADMIN gets all units across all organizations.

```bash
curl http://localhost:8001/auth/hierarchy/units/ \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "success": true,
  "result": [
    {
      "id": 2,
      "name": "Maharashtra Division",
      "hierarchy_level_name": "State Head",
      "parent": 1,
      "path": "/1/2/"
    },
    {
      "id": 4,
      "name": "Pune Area Office",
      "hierarchy_level_name": "Area Officer",
      "parent": 2,
      "path": "/1/2/4/"
    },
    {
      "id": 5,
      "name": "Nashik Area Office",
      "hierarchy_level_name": "Area Officer",
      "parent": 2,
      "path": "/1/2/5/"
    }
  ]
}
```

### Get Full Subtree Under a Specific Node

```bash
curl http://localhost:8001/auth/hierarchy/units/2/subtree/ \
  -H "Authorization: Bearer <token>"
```

### List Hierarchy Levels (for your org)

```bash
# ORG_USER — automatically scoped to their org
curl http://localhost:8001/auth/hierarchy/levels/ \
  -H "Authorization: Bearer <org_user_token>"

# SUPER_ADMIN — optionally filter by org
curl "http://localhost:8001/auth/hierarchy/levels/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 10. Impersonation

Allows a SUPER_ADMIN or ORG_USER to log in as a user below them.  
**FPO and FARMER accounts cannot be impersonated.**

The response is a standard JWT token pair for the target user.  
The `impersonated_by` claim is embedded in the JWT payload for traceability.

```bash
curl -X POST http://localhost:8001/auth/hierarchy/impersonate/7/ \
  -H "Authorization: Bearer <super_admin_or_org_user_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Impersonation token issued.",
  "result": {
    "access": "<access_token_for_target_user>",
    "refresh": "<refresh_token_for_target_user>",
    "impersonated_user_id": 7,
    "impersonated_username": "area_officer_pune"
  }
}
```

Use the returned `access` token as the `Authorization` header in subsequent requests to act as that user.

**Error cases:**

| Scenario                     | Status | Message                                                    |
| ---------------------------- | ------ | ---------------------------------------------------------- |
| Target is FPO or FARMER      | 403    | Impersonation is restricted to ORG_USER accounts.          |
| Target is a peer or superior | 403    | You can only impersonate users below you in the hierarchy. |
| Target is in a different org | 403    | Cannot impersonate users outside your organization.        |
| Target not found             | 404    | Target user not found.                                     |
| Requester has no membership  | 403    | Both requester and target must have an OrgMembership.      |

---

## 11. SUPER_ADMIN — Stats

All stats endpoints support an optional `?organization=<id>` query parameter to scope results to a single organization.

### Platform Overview

```bash
curl http://localhost:8001/super-admin/stats/overview/ \
  -H "Authorization: Bearer <super_admin_token>"

# Scoped to one org
curl "http://localhost:8001/super-admin/stats/overview/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Platform overview stats.",
  "result": {
    "users": {
      "super_admin": 2,
      "org_users": 5,
      "fpo": 12,
      "farmer": 340
    },
    "fpo": {
      "total": 12,
      "linked_to_hierarchy": 10,
      "unlinked": 2
    },
    "farmers": {
      "total": 340,
      "with_fpo": 320,
      "without_fpo": 20
    },
    "farms": {
      "total": 780
    },
    "satellite_subscriptions": {
      "PAID": 5,
      "SUBMITTED": 12,
      "SYNCING": 40,
      "COMPLETED": 200,
      "FAILED": 3
    },
    "hierarchy": {
      "organizations": 1,
      "org_units": 4,
      "org_users_assigned": 3
    }
  }
}
```

### Per-FPO Stats

```bash
curl http://localhost:8001/super-admin/stats/fpos/ \
  -H "Authorization: Bearer <super_admin_token>"

# Scoped to one org
curl "http://localhost:8001/super-admin/stats/fpos/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "FPO stats.",
  "result": [
    {
      "fpo_id": 10,
      "fpo_name": "Pune Farmers Co-op",
      "farmer_count": 85,
      "farm_count": 120,
      "active_subscription_count": 45
    }
  ]
}
```

---

## 12. SUPER_ADMIN — Notifications

### Device Token Coverage

Summary of registered push notification tokens by platform.

```bash
curl http://localhost:8001/super-admin/notifications/device-tokens/ \
  -H "Authorization: Bearer <super_admin_token>"

# Scoped to one org
curl "http://localhost:8001/super-admin/notifications/device-tokens/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Device token stats.",
  "result": {
    "total_tokens": 280,
    "by_platform": {
      "android": 190,
      "ios": 90
    }
  }
}
```

### Users Without a Device Token

Lists users who have no registered push token (delivery gap diagnosis).

```bash
curl http://localhost:8001/super-admin/notifications/coverage/ \
  -H "Authorization: Bearer <super_admin_token>"

# Scoped to one org
curl "http://localhost:8001/super-admin/notifications/coverage/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Users without a registered device token.",
  "result": {
    "count": 3,
    "users": [
      { "user_id": 12, "username": "area_officer_nashik", "role": "ORG_USER" }
    ]
  }
}
```

---

## 13. SUPER_ADMIN — Payments

### List Active Satellite Plans

```bash
curl http://localhost:8001/super-admin/payments/plans/ \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Active satellite plans.",
  "result": [
    {
      "id": 1,
      "name": "3 Month Plan",
      "duration_days": 90,
      "duration_months": 3,
      "base_price_per_acre": "250.00",
      "gst_percent": "18.00",
      "total_price_per_acre": "295.00",
      "commission_percent": "10.00",
      "commission_amount_per_acre": "25.00",
      "commission_gst_per_acre": "4.50",
      "total_commission_per_acre": "29.50"
    }
  ]
}
```

### Subscription Summary

Overall status breakdown across the platform (or a single org).

```bash
curl http://localhost:8001/super-admin/payments/subscriptions/summary/ \
  -H "Authorization: Bearer <super_admin_token>"

# Scoped to one org
curl "http://localhost:8001/super-admin/payments/subscriptions/summary/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Subscription summary.",
  "result": {
    "by_status": {
      "PAID": 5,
      "SUBMITTED": 12,
      "SYNCING": 40,
      "COMPLETED": 200,
      "FAILED": 3
    },
    "completed_total_farm_area_acres": 4820.5
  }
}
```

### Per-FPO Subscription Detail

```bash
curl http://localhost:8001/super-admin/payments/subscriptions/by-fpo/ \
  -H "Authorization: Bearer <super_admin_token>"

# Scoped to one org
curl "http://localhost:8001/super-admin/payments/subscriptions/by-fpo/?organization=1" \
  -H "Authorization: Bearer <super_admin_token>"
```

**Response:**

```json
{
  "success": true,
  "message": "Per-FPO subscription details.",
  "result": [
    {
      "fpo_id": 10,
      "fpo_name": "Pune Farmers Co-op",
      "active_subscriptions": 45,
      "pending_subscriptions": 3,
      "expired_subscriptions": 1
    }
  ]
}
```

---

## 14. Full Setup Walkthrough (Example)

This example builds the hierarchy:

```
Corporate Admin (HQ)
  └── State Head (Maharashtra Division)
        ├── Area Officer (Pune Area Office)  →  FPO: Pune Farmers Co-op
        └── Area Officer (Nashik Area Office) → FPO: Nashik Agro FPO
```

```bash
TOKEN="<super_admin_access_token>"

# Step 1 — Create org
curl -X POST http://localhost:8001/super-admin/organizations/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Erde Agro Corp"}'
# → org id=1

# Step 2 — Create hierarchy levels
curl -X POST http://localhost:8001/super-admin/hierarchy-levels/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "name": "Corporate Admin", "level": 1}'
# → level id=1

curl -X POST http://localhost:8001/super-admin/hierarchy-levels/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "name": "State Head", "level": 2}'
# → level id=2

curl -X POST http://localhost:8001/super-admin/hierarchy-levels/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "name": "Area Officer", "level": 3}'
# → level id=3

# Step 3 — Create OrgUnit tree
curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "hierarchy_level": 1, "name": "HQ", "parent": null}'
# → unit id=1, path="/1/"

curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "hierarchy_level": 2, "name": "Maharashtra Division", "parent": 1}'
# → unit id=2, path="/1/2/"

curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "hierarchy_level": 3, "name": "Pune Area Office", "parent": 2}'
# → unit id=3, path="/1/2/3/"

curl -X POST http://localhost:8001/super-admin/org-units/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"organization": 1, "hierarchy_level": 3, "name": "Nashik Area Office", "parent": 2}'
# → unit id=4, path="/1/2/4/"

# Step 4 — Create ORG_USER accounts
curl -X POST http://localhost:8001/super-admin/users/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username": "state_head_mh", "password": "pass1234", "role": "ORG_USER", "org_unit": 2}'

curl -X POST http://localhost:8001/super-admin/users/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username": "area_officer_pune", "password": "pass1234", "role": "ORG_USER", "org_unit": 3}'

curl -X POST http://localhost:8001/super-admin/users/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"username": "area_officer_nashik", "password": "pass1234", "role": "ORG_USER", "org_unit": 4}'

# Step 5 — Link existing FPOs into the hierarchy
# (fpo_profile IDs come from GET /auth/fpo-list/)
curl -X POST http://localhost:8001/super-admin/fpo-links/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"fpo_profile": 10, "org_unit": 3}'

curl -X POST http://localhost:8001/super-admin/fpo-links/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"fpo_profile": 11, "org_unit": 4}'
```

---

## 15. What Each Role Sees

| Role                           | `GET /auth/hierarchy/units/` | `GET` farmer/FPO data    |
| ------------------------------ | ---------------------------- | ------------------------ |
| `SUPER_ADMIN`                  | All units across all orgs    | All FPOs + all Farmers   |
| `ORG_USER` (State Head MH)     | MH + Pune + Nashik units     | FPOs under Pune + Nashik |
| `ORG_USER` (Area Officer Pune) | Pune unit only               | FPOs under Pune only     |
| `FPO`                          | N/A (no access)              | Own farmers only         |
| `FARMER`                       | N/A (no access)              | Own profile only         |

---

## 16. Complete API Reference

### `/auth/` endpoints

| Method | URL                                   | Role                 | Description                      |
| ------ | ------------------------------------- | -------------------- | -------------------------------- |
| POST   | `/auth/register/`                     | Public               | Register FPO or FARMER account   |
| POST   | `/auth/webapp/login/`                 | Public               | Login for SUPER_ADMIN / ORG_USER |
| POST   | `/auth/fpo/login/`                    | Public               | Login for FPO                    |
| POST   | `/auth/firebase-login/`               | Public               | Firebase phone login for FARMER  |
| POST   | `/auth/farmer/check-otp/`             | Public               | Farmer OTP verification          |
| POST   | `/auth/token/refresh/`                | Public               | Refresh JWT token                |
| GET    | `/auth/farmer/my-profile/`            | FARMER               | Own farmer profile               |
| GET    | `/auth/fpo/my-profile/`               | FPO                  | Own FPO profile                  |
| GET    | `/auth/fpo-list/`                     | Authenticated        | List all FPO profiles            |
| GET    | `/auth/hierarchy/units/`              | SUPER_ADMIN/ORG_USER | Accessible org units             |
| GET    | `/auth/hierarchy/units/<id>/subtree/` | SUPER_ADMIN/ORG_USER | Full subtree under a node        |
| GET    | `/auth/hierarchy/levels/`             | SUPER_ADMIN/ORG_USER | Hierarchy levels                 |
| POST   | `/auth/hierarchy/impersonate/<id>/`   | SUPER_ADMIN/ORG_USER | Impersonate a user below you     |

### `/super-admin/` endpoints

| Method           | URL                                            | Description                                 |
| ---------------- | ---------------------------------------------- | ------------------------------------------- |
| GET/POST         | `/super-admin/organizations/`                  | List / create organizations                 |
| GET/PATCH/DELETE | `/super-admin/organizations/<id>/`             | Retrieve / update / delete org              |
| GET/POST         | `/super-admin/hierarchy-levels/`               | List / create hierarchy levels              |
| GET/PATCH/DELETE | `/super-admin/hierarchy-levels/<id>/`          | Retrieve / update / delete level            |
| GET/POST         | `/super-admin/org-units/`                      | List / create org units                     |
| GET/PATCH/DELETE | `/super-admin/org-units/<id>/`                 | Retrieve / update / delete unit (re-parent) |
| GET/POST         | `/super-admin/memberships/`                    | List / create memberships                   |
| GET/PATCH/DELETE | `/super-admin/memberships/<id>/`               | Retrieve / update / delete membership       |
| GET/POST         | `/super-admin/fpo-links/`                      | List / create FPO ↔ OrgUnit links           |
| GET/PATCH/DELETE | `/super-admin/fpo-links/<id>/`                 | Retrieve / update / delete FPO link         |
| POST             | `/super-admin/users/`                          | Create ORG_USER or SUPER_ADMIN account      |
| GET              | `/super-admin/stats/overview/`                 | Platform-wide counts and summary            |
| GET              | `/super-admin/stats/fpos/`                     | Per-FPO farmer / farm / subscription counts |
| GET              | `/super-admin/notifications/device-tokens/`    | Device token counts by platform             |
| GET              | `/super-admin/notifications/coverage/`         | Users with no registered device token       |
| GET              | `/super-admin/payments/plans/`                 | Active satellite subscription plans         |
| GET              | `/super-admin/payments/subscriptions/summary/` | Subscription status breakdown               |
| GET              | `/super-admin/payments/subscriptions/by-fpo/`  | Per-FPO subscription counts                 |

---

## 17. Standard Response Format

All endpoints return:

```json
{
  "success": true | false,
  "message": "Human readable message",
  "result": { ... } | [ ... ] | null
}
```

Common HTTP status codes:

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 200  | Success                                            |
| 201  | Created                                            |
| 400  | Validation error (check `result` for field errors) |
| 401  | Missing or expired token                           |
| 403  | Insufficient role / permission denied              |
| 404  | Resource not found                                 |
