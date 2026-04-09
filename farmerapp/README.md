# Farmer App Satellite Subscription Flow

This document describes the planned satellite subscription flow for farms in the main DRF backend and how it interacts with the separate `satellite-service`.

## Main Idea

- The main app owns the business state:
  - farm creation
  - payment completion
  - subscription duration
  - subscription lifecycle shown to users
- The `satellite-service` owns the ingestion state:
  - order storage
  - order field storage
  - satellite result storage
  - background synchronization from IrriWatch

## Main App Model

The main app tracks per-farm subscription state using `FarmSatelliteSubscription`.

### Statuses

- `PAID`
  - Payment is done.
  - The farm has not yet been sent to IrriWatch / `satellite-service`.
- `SUBMITTED`
  - The farm has been sent for satellite processing.
  - We are waiting for data to start arriving.
- `SYNCING`
  - The farm is actively receiving satellite data.
- `COMPLETED`
  - The subscription period is over.
- `FAILED`
  - Submission or synchronization failed after retries.

## End-to-End Flow

### 1. Farm Creation

- A farm is created in the main app.
- No `FarmSatelliteSubscription` row is created at this stage.

### 2. Payment Completion

- Once payment is completed, create a `FarmSatelliteSubscription` entry with:
  - `farm`
  - `payment_reference`
  - `subscription_duration_months`
  - `status = PAID`

At this point:

- the farm is eligible for satellite activation
- it has not yet been sent to IrriWatch or `satellite-service`

### 3. Cron Job in Main App: Submit Paid Farms

Run a cron job in the main app for all subscriptions with `status = PAID`.

This cron does 2 things.

#### 3a. Call IrriWatch API

- Send the farm data to IrriWatch.
- On success, populate:
  - `irriwatch_order_uuid`
  - `irriwatch_field_uuid`
  - `subscription_start`
  - `subscription_end`
  - `submitted_at`
- Update:
  - `status = SUBMITTED`

Rules:

- `subscription_start` is the date when this cron job successfully submits the farm.
- `subscription_end` is calculated as:
  - `subscription_start + subscription_duration_months`

#### 3b. Call Internal `satellite-service` API

- After the IrriWatch order/field is created, call the internal `satellite-service` API.
- Send:
  - `irriwatch_order_uuid`
  - `irriwatch_field_uuid`
  - `external_id = farm.id`

The `satellite-service` will create:

- `Order`
- `OrderField`

based on this data.

### 4. Satellite-Service Sync

- The `satellite-service` is responsible for fetching and storing satellite data from IrriWatch through its own background jobs.
- It updates its internal `Order`, `OrderField`, and `SatelliteResult` tables.

### 5. Cron Job in Main App: Check for Data Arrival

Run another cron job in the main app for subscriptions with `status = SUBMITTED`.

This cron:

- checks the `satellite-service`
- verifies whether satellite data has started arriving for the farm

If data is available:

- update `status = SYNCING`

## Business Queries Supported by This Model

### Farms with Active Satellite Data Enabled

Treat these as subscriptions where status is one of:

- `PAID`
- `SUBMITTED`
- `SYNCING`

### Farms That Have Paid but Are Not Yet Sent

- `status = PAID`

### Farms That Are Sent and Waiting for Data

- `status = SUBMITTED`

### Farms That Are Actively Receiving Data

- `status = SYNCING`

### Subscriptions Ending Soon

Use the `is_expiring_soon` property:

- `True` when `subscription_end` is within 7 days from today

## Important Note About `external_id`

Current planned flow sends:

- `external_id = farm.id`

This is fine only if one farm will never need another independent subscription record in `satellite-service`.

Reason:

- in `satellite-service`, `OrderField.external_id` is unique
- if the same farm's irriwatch_order_uuid and irriwatch_field_uuid is changed after renewal, using `farm.id` again may conflict

If renewals change the irriwatch_order_uuid and irriwatch_field_uuid, switch to:

- `external_id = FarmSatelliteSubscription.id`

That is the safer long-term design.
