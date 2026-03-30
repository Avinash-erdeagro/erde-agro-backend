# API Documentation

Base URL for local development:

```text
http://127.0.0.1:8000
```

All APIs return responses in this format:

```json
{
  "success": true,
  "message": "Success or failure message",
  "result": {}
}
```

For failures:

```json
{
  "success": false,
  "message": "Failure message",
  "result": {}
}
```

## 1. Register User

- URL: `POST /auth/register/`
- What it does: Creates a new app user and creates either an FPO profile or a Farmer profile based on the `role`.

Response format:

```json
{
  "success": true,
  "message": "User registered successfully.",
  "result": {
    "id": 1,
    "user_id": 5,
    "username": "fpo@example.com",
    "profile_id": 2,
    "profile_type": "fpo"
  }
}
```

Validation failure format:

```json
{
  "success": false,
  "message": "Validation failed.",
  "result": {
    "email": [
      "This field is required."
    ]
  }
}
```

## 2. Pincode Lookup

- URL: `GET /auth/pincode/<pin_code>/`
- What it does: Fetches district, state, and locality options for a given 6-digit PIN code.

Response format:

```json
{
  "success": true,
  "message": "Pincode details fetched successfully.",
  "result": {
    "pin_code": "481001",
    "district": "Balaghat",
    "state": "Madhya Pradesh",
    "localities": [
      {
        "village": "Balaghat",
        "taluka": "Balaghat"
      }
    ]
  }
}
```

Failure format:

```json
{
  "success": false,
  "message": "PIN code must contain exactly 6 digits.",
  "result": null
}
```

## 3. FPO Profile APIs

### 3.1 List FPO Profiles

- URL: `GET /auth/fpo-profiles/`
- What it does: Returns all FPO profiles.

Response format:

```json
{
  "success": true,
  "message": "FPO profiles fetched successfully.",
  "result": [
    {
      "id": 1,
      "fpo_name": "Green Agro Farmers Producer Company",
      "contact_person_name": "Ramesh Patil",
      "email": "fpo@example.com",
      "mobile": "9876543210",
      "gst_number": "27ABCDE1234F1Z5",
      "pan_number": "ABCDE1234F",
      "cin_number": "U01100PN2024PTC123456",
      "pan_file": null,
      "cin_file": null,
      "gst_file": null,
      "locality": {
        "id": 1,
        "pin_code": "411001",
        "village": "Shivajinagar",
        "taluka": "Haveli",
        "district": "Pune",
        "state": "Maharashtra"
      },
      "app_user": 1
    }
  ]
}
```

### 3.2 Retrieve FPO Profile

- URL: `GET /auth/fpo-profiles/<id>/`
- What it does: Returns one FPO profile by id.

Response format:

```json
{
  "success": true,
  "message": "FPO profile fetched successfully.",
  "result": {
    "id": 1,
    "fpo_name": "Green Agro Farmers Producer Company",
    "contact_person_name": "Ramesh Patil",
    "email": "fpo@example.com",
    "mobile": "9876543210",
    "gst_number": "27ABCDE1234F1Z5",
    "pan_number": "ABCDE1234F",
    "cin_number": "U01100PN2024PTC123456",
    "pan_file": null,
    "cin_file": null,
    "gst_file": null,
    "locality": {
      "id": 1,
      "pin_code": "411001",
      "village": "Shivajinagar",
      "taluka": "Haveli",
      "district": "Pune",
      "state": "Maharashtra"
    },
    "app_user": 1
  }
}
```

### 3.3 Create FPO Profile

- URL: `POST /auth/fpo-profiles/`
- What it does: Creates a new FPO profile.

Response format:

```json
{
  "success": true,
  "message": "FPO profile created successfully.",
  "result": {
    "id": 2,
    "fpo_name": "New FPO",
    "contact_person_name": "Contact Person",
    "email": "newfpo@example.com",
    "mobile": "9876543210",
    "gst_number": "27ABCDE1234F1Z5",
    "pan_number": "ABCDE1234F",
    "cin_number": "U01100PN2024PTC123456",
    "pan_file": null,
    "cin_file": null,
    "gst_file": null,
    "locality": {
      "id": 1,
      "pin_code": "411001",
      "village": "Shivajinagar",
      "taluka": "Haveli",
      "district": "Pune",
      "state": "Maharashtra"
    },
    "app_user": 2
  }
}
```

### 3.4 Update FPO Profile

- URL: `PUT /auth/fpo-profiles/<id>/`
- What it does: Fully updates an existing FPO profile.

Response format:

```json
{
  "success": true,
  "message": "FPO profile updated successfully.",
  "result": {
    "id": 1
  }
}
```

### 3.5 Partial Update FPO Profile

- URL: `PATCH /auth/fpo-profiles/<id>/`
- What it does: Partially updates an existing FPO profile.

Response format:

```json
{
  "success": true,
  "message": "FPO profile updated successfully.",
  "result": {
    "id": 1
  }
}
```

### 3.6 Delete FPO Profile

- URL: `DELETE /auth/fpo-profiles/<id>/`
- What it does: Deletes an FPO profile.

Response format:

```json
{
  "success": true,
  "message": "FPO profile deleted successfully.",
  "result": null
}
```

## 4. Farmer Profile APIs

### 4.1 List Farmer Profiles

- URL: `GET /auth/farmer-profiles/`
- What it does: Returns all Farmer profiles.

Response format:

```json
{
  "success": true,
  "message": "Farmer profiles fetched successfully.",
  "result": [
    {
      "id": 1,
      "farmer_name": "Suresh Patil",
      "contact_number": "9876543211",
      "email": "suresh@example.com",
      "registered_with_fpo": 1,
      "aadhaar_number": "123412341234",
      "aadhaar_file": null,
      "locality": {
        "id": 1,
        "pin_code": "411001",
        "village": "Shivajinagar",
        "taluka": "Haveli",
        "district": "Pune",
        "state": "Maharashtra"
      },
      "app_user": 3
    }
  ]
}
```

### 4.2 Retrieve Farmer Profile

- URL: `GET /auth/farmer-profiles/<id>/`
- What it does: Returns one Farmer profile by id.

Response format:

```json
{
  "success": true,
  "message": "Farmer profile fetched successfully.",
  "result": {
    "id": 1,
    "farmer_name": "Suresh Patil",
    "contact_number": "9876543211",
    "email": "suresh@example.com",
    "registered_with_fpo": 1,
    "aadhaar_number": "123412341234",
    "aadhaar_file": null,
    "locality": {
      "id": 1,
      "pin_code": "411001",
      "village": "Shivajinagar",
      "taluka": "Haveli",
      "district": "Pune",
      "state": "Maharashtra"
    },
    "app_user": 3
  }
}
```

### 4.3 Create Farmer Profile

- URL: `POST /auth/farmer-profiles/`
- What it does: Creates a new Farmer profile.

Response format:

```json
{
  "success": true,
  "message": "Farmer profile created successfully.",
  "result": {
    "id": 2,
    "farmer_name": "New Farmer",
    "contact_number": "9876543212",
    "email": "newfarmer@example.com",
    "registered_with_fpo": 1,
    "aadhaar_number": "123412341235",
    "aadhaar_file": null,
    "locality": {
      "id": 1,
      "pin_code": "411001",
      "village": "Shivajinagar",
      "taluka": "Haveli",
      "district": "Pune",
      "state": "Maharashtra"
    },
    "app_user": 4
  }
}
```

### 4.4 Update Farmer Profile

- URL: `PUT /auth/farmer-profiles/<id>/`
- What it does: Fully updates an existing Farmer profile.

Response format:

```json
{
  "success": true,
  "message": "Farmer profile updated successfully.",
  "result": {
    "id": 1
  }
}
```

### 4.5 Partial Update Farmer Profile

- URL: `PATCH /auth/farmer-profiles/<id>/`
- What it does: Partially updates an existing Farmer profile.

Response format:

```json
{
  "success": true,
  "message": "Farmer profile updated successfully.",
  "result": {
    "id": 1
  }
}
```

### 4.6 Delete Farmer Profile

- URL: `DELETE /auth/farmer-profiles/<id>/`
- What it does: Deletes a Farmer profile.

Response format:

```json
{
  "success": true,
  "message": "Farmer profile deleted successfully.",
  "result": null
}
```
