# AWS Deployment Guide — Erde Agro FarmApp Backend

> A step-by-step guide to deploying the **erde-agro-farmapp-backend** Django application on AWS using **Docker**, **EC2**, **RDS (PostGIS)**, **Caddy** for HTTPS, and **GitHub Actions** for CI/CD.

---

## Table of Contents

1. [What Are We Building?](#1-what-are-we-building)
2. [AWS Services We Will Use (and Why)](#2-aws-services-we-will-use-and-why)
3. [Step 1 — Set Up a Key Pair (SSH Access)](#step-1--set-up-a-key-pair-ssh-access)
4. [Step 2 — Create Security Groups](#step-2--create-security-groups)
5. [Step 3 — Launch an EC2 Instance](#step-3--launch-an-ec2-instance)
6. [Step 4 — Connect to Your EC2 Instance via SSH](#step-4--connect-to-your-ec2-instance-via-ssh)
7. [Step 5 — Create an RDS PostgreSQL (PostGIS) Database](#step-5--create-an-rds-postgresql-postgis-database)
8. [Step 6 — Install Docker and Caddy on EC2](#step-6--install-docker-and-caddy-on-ec2)
9. [Step 7 — S3 Bucket for File Uploads](#step-7--s3-bucket-for-file-uploads)
10. [Step 8 — Set Up Docker Hub](#step-8--set-up-docker-hub)
11. [Step 9 — Prepare the Server for First Deploy](#step-9--prepare-the-server-for-first-deploy)
12. [Step 10 — Set Up HTTPS with Caddy](#step-10--set-up-https-with-caddy)
13. [Step 11 — Point Your Domain to EC2 (DNS)](#step-11--point-your-domain-to-ec2-dns)
14. [Step 12 — Set Up GitHub Actions CI/CD](#step-12--set-up-github-actions-cicd)
15. [Step 13 — First Deployment](#step-13--first-deployment)
16. [Step 14 — Create Django Superuser](#step-14--create-django-superuser)
17. [Step 15 — Security Hardening Checklist](#step-15--security-hardening-checklist)
18. [Step 16 — Monitoring and Logs](#step-16--monitoring-and-logs)
19. [Architecture Diagram](#architecture-diagram)
20. [How Deployments Work (After Setup)](#how-deployments-work-after-setup)
21. [Common Troubleshooting](#common-troubleshooting)
22. [Cost Estimate](#cost-estimate)

---

## 1. What Are We Building?

Our **erde-agro-farmapp-backend** is a Django REST API that serves a mobile app for farmers and FPOs (Farmer Producer Organizations). It has these main parts:

| Component            | What It Does                                                                                                  | Runs On        |
| -------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- |
| **Django REST API**  | Authentication (Firebase + JWT), farmer/FPO profiles, farm management, crop tracking, satellite data, billing | EC2 (Docker)   |
| **PostGIS Database** | Stores users, profiles, farms (with geospatial data), crops, satellite subscriptions, billing plans           | RDS            |
| **S3 File Storage**  | Stores uploaded documents (Aadhaar, PAN, CIN, GST files), farm documents, video thumbnails                    | S3             |
| **Firebase Auth**    | Verifies farmer login via Firebase ID tokens                                                                  | Google Cloud   |
| **CI/CD Pipeline**   | Automatically builds, pushes, and deploys on every `git push` to `main`                                       | GitHub Actions |

The final setup looks like this:

```
Developer pushes to main
        │
        ▼
GitHub Actions CI/CD
  1. Build Docker image (with GDAL baked in)
  2. Push to Docker Hub
  3. SSH into EC2
  4. Pull new image + restart container
        │
        ▼
EC2 Server
  ┌─────────────────────────────────────────────────┐
  │  Caddy (reverse proxy, auto-TLS)   ← port 443  │
  │    │                                            │
  │    ▼                                            │
  │  Docker: Django + Gunicorn         ← port 8000  │
  │    │                                            │
  │    ├──► RDS PostGIS                ← port 5432  │
  │    ├──► S3 Bucket                  ← file uploads│
  │    └──► Firebase                   ← auth verify │
  └─────────────────────────────────────────────────┘
```

### Why Docker?

| Problem                              | Docker Solution                                           |
| ------------------------------------ | --------------------------------------------------------- |
| GDAL/GEOS install hell on macOS      | Baked into the Docker image once — never worry again      |
| "Works on my machine" bugs           | Same image runs locally and on the server                 |
| Manual deploy (SSH → git pull → ...) | `git push` triggers fully automated deploy                |
| Dependency drift over time           | Image is immutable — every deploy is a clean, known state |

---

## 2. AWS Services We Will Use (and Why)

Here is every AWS service involved, explained simply:

### EC2 (Elastic Compute Cloud)

**What:** A virtual computer (server) running in Amazon's data center.
**Why we need it:** This is where Docker runs our Django application container, and where Caddy handles HTTPS.
**Think of it as:** Renting a laptop in the cloud that's always turned on.

### RDS (Relational Database Service)

**What:** A managed PostgreSQL database hosted by AWS.
**Why we need it:** Our app uses PostGIS (PostgreSQL + geospatial extensions) for storing farm boundaries and location data. RDS handles backups, patches, and scaling for us.
**Think of it as:** AWS runs and takes care of our database; we just connect to it.
**Key benefits:** Automatic backups, easy scaling, point-in-time recovery, patches applied for you.

### S3 (Simple Storage Service)

**What:** Cloud file storage. Files (called "objects") are stored in containers called "buckets."
**Why we need it:** Our app stores uploaded documents (Aadhaar files, PAN/GST/CIN certificates, farm documents, video thumbnails) in S3 via `django-storages`.
**Think of it as:** An unlimited hard drive in the cloud.

### VPC (Virtual Private Cloud)

**What:** A private, isolated network within AWS that your resources live in.
**Why we need it:** EC2 and RDS need to talk to each other securely. A VPC keeps them on the same private network so the database is never exposed to the public internet.
**Think of it as:** Your own private office building — outsiders can't just walk in.
**Note:** AWS creates a default VPC for you automatically. We'll use it.

### Security Groups

**What:** Virtual firewalls that control which traffic can reach your EC2 and RDS.
**Why we need it:** We want the internet to reach our API (ports 80/443) and us to SSH in (port 22), but we do NOT want random people reaching the database (port 5432).
**Think of it as:** A bouncer at the door that checks a list before letting anyone in.

### IAM (Identity and Access Management)

**What:** Controls WHO can do WHAT in your AWS account.
**Why we need it:** We create an IAM user that lets our app upload files to S3.
**Think of it as:** Name badges with different permissions — the janitor can open closets, the manager can open the vault.

### Route 53 (Optional — DNS)

**What:** AWS's domain name service. Maps domain names (like `api.yourdomain.com`) to IP addresses.
**Why we need it:** For HTTPS to work with a real domain name. You can also use any other DNS provider (Cloudflare, Namecheap, GoDaddy, Bigrock, etc.).
**Think of it as:** The phone book of the internet — translates names to addresses.

### Elastic IP

**What:** A static (permanent) public IP address that you can assign to your EC2 instance.
**Why we need it:** By default EC2 gets a new IP every time it restarts. An Elastic IP stays the same forever, so your domain always points to the right place.
**Think of it as:** Getting a permanent phone number instead of a temporary one.

### Key Pair

**What:** A pair of cryptographic keys (one public, one private) used to securely log in to your EC2 instance via SSH.
**Why we need it:** Instead of a password (which can be guessed), we use a key file that only you have.
**Think of it as:** A special key to your office — only the person with the physical key can get in.

---

## Step 1 — Set Up a Key Pair (SSH Access)

A key pair lets you securely connect to your EC2 instance from your terminal.

1. Go to the AWS Console → search for **EC2** → click it
2. In the left sidebar, find **Network & Security** → click **Key Pairs**
3. Click **Create key pair**
4. Fill in:
   - **Name:** `farmapp-key`
   - **Key pair type:** RSA
   - **Private key file format:** `.pem` (works on macOS/Linux)
5. Click **Create key pair**
6. A file called `farmapp-key.pem` will automatically download to your Mac

Now **secure the key file** — this is critically important:

```bash
# Move the key to a safe location
mv ~/Downloads/farmapp-key.pem ~/.ssh/farmapp-key.pem

# Set correct permissions (SSH refuses to use keys that are too open)
chmod 400 ~/.ssh/farmapp-key.pem
```

> **WARNING:** If you lose this `.pem` file, you will be locked out of your server. Back it up securely. Never share it, never commit it to git.

---

## Step 2 — Create Security Groups

Security Groups act as firewalls. We need two:

1. One for EC2 (allows SSH + HTTP + HTTPS from the internet)
2. One for RDS (allows PostgreSQL only from our EC2)

### 2a. EC2 Security Group

1. Go to **EC2** → left sidebar **Network & Security** → **Security Groups**
2. Click **Create security group**
3. Fill in:
   - **Security group name:** `farmapp-ec2-sg`
   - **Description:** `Allow SSH, HTTP, HTTPS for FarmApp backend`
   - **VPC:** Leave as default VPC
4. Under **Inbound rules**, click **Add rule** three times:

   | Type  | Protocol | Port Range | Source                    | Description                 |
   | ----- | -------- | ---------- | ------------------------- | --------------------------- |
   | SSH   | TCP      | 22         | My IP                     | SSH access from my computer |
   | HTTP  | TCP      | 80         | 0.0.0.0/0 (Anywhere IPv4) | HTTP (Caddy redirect)       |
   | HTTPS | TCP      | 443        | 0.0.0.0/0 (Anywhere IPv4) | HTTPS traffic               |

5. **Outbound rules:** Leave the default (all traffic allowed outbound)
6. Click **Create security group**

> **Security note on SSH:** "My IP" auto-fills your current public IP. If your IP changes (e.g., you go to a coffee shop), you'll need to update this rule to SSH in again. This is intentional — it keeps SSH locked to just you.

### 2b. RDS Security Group

1. Click **Create security group** again
2. Fill in:
   - **Security group name:** `farmapp-rds-sg`
   - **Description:** `Allow PostgreSQL from EC2 only`
   - **VPC:** Same default VPC
3. Under **Inbound rules**, click **Add rule**:

   | Type       | Protocol | Port Range | Source           | Description             |
   | ---------- | -------- | ---------- | ---------------- | ----------------------- |
   | PostgreSQL | TCP      | 5432       | `farmapp-ec2-sg` | DB access from EC2 only |

   > **Important:** In the "Source" field, start typing `farmapp-ec2-sg` — it will appear as a dropdown option. Select it. This means ONLY machines in the EC2 security group can reach the database. The database is invisible to the public internet.

4. Click **Create security group**

---

## Step 3 — Launch an EC2 Instance

This is the virtual server where Docker and Caddy will run.

1. Go to **EC2** → click **Launch instance** (the big orange button)

2. **Name:** `farmapp-backend-server`

3. **Application and OS Images (AMI):**
   - Select **Ubuntu** (click the Ubuntu tab)
   - Choose **Ubuntu Server 24.04 LTS** (Free tier eligible)
   - Architecture: **64-bit (x86)**

4. **Instance type:**
   - Select **t3.small** (2 vCPU, 2 GB RAM) — good balance for Docker + Gunicorn workers
   - `t3.micro` (free tier) works too if you want to save money initially, but may be tight under load

5. **Key pair:**
   - Select `farmapp-key` (the one we created in Step 1)

6. **Network settings:** Click **Edit**
   - **VPC:** Default VPC
   - **Subnet:** No preference (any availability zone)
   - **Auto-assign public IP:** **Enable**
   - **Firewall (security groups):** Select **Select existing security group**
   - Choose `farmapp-ec2-sg`

7. **Configure storage:**
   - Change from 8 GB to **25 GB** (gp3)
   - Docker images take space — give yourself headroom

8. Click **Launch instance**

9. You'll see a success page. Click the instance ID link to go to your instance.

10. Wait until **Instance state** shows **Running** and **Status checks** shows **2/2 checks passed**

### Allocate an Elastic IP

So your server has a permanent IP address:

1. Go to **EC2** → left sidebar → **Network & Security** → **Elastic IPs**
2. Click **Allocate Elastic IP address** → Click **Allocate**
3. Select the new Elastic IP → click **Actions** → **Associate Elastic IP address**
4. Choose your `farmapp-backend-server` instance → click **Associate**

> **Write down this Elastic IP.** (e.g., `54.123.45.67`). You'll use it everywhere.

---

## Step 4 — Connect to Your EC2 Instance via SSH

Open Terminal on your Mac and run:

```bash
ssh -i ~/.ssh/farmapp-key.pem ubuntu@YOUR_ELASTIC_IP
```

Replace `YOUR_ELASTIC_IP` with the actual IP from Step 3 (e.g., `54.123.45.67`).

**First time connecting?** You'll see:

```
The authenticity of host '54.123.45.67' can't be established.
Are you sure you want to continue connecting (yes/no)?
```

Type `yes` and press Enter.

You should see a prompt like:

```
ubuntu@ip-172-31-xx-xx:~$
```

**Congratulations — you're inside your cloud server!**

> **Troubleshooting: "Permission denied"**
>
> - Make sure you ran `chmod 400` on the .pem file
> - Make sure the username is `ubuntu` (not `ec2-user` or `root`)
> - Make sure the Security Group has SSH from your IP

> **Troubleshooting: "Connection timed out"**
>
> - Check that the instance is running
> - Check the SSH inbound rule source matches your current IP

---

## Step 5 — Create an RDS PostgreSQL (PostGIS) Database

Our app uses PostGIS (geospatial extension for PostgreSQL), so we need a PostgreSQL RDS instance with PostGIS enabled.

1. Go to the AWS Console → search for **RDS** → click it
2. Click **Create database**
3. Choose:
   - **Creation method:** Standard create
   - **Engine type:** PostgreSQL
   - **Engine version:** PostgreSQL 17 (to match our docker-compose PostGIS 17 setup)
   - **Templates:** **Free tier** (if eligible) or **Dev/Test**

4. **Settings:**
   - **DB instance identifier:** `farmapp-db`
   - **Master username:** `farmapp_admin`
   - **Credentials management:** Select **Self managed**
   - **Master password:** Create a strong password (e.g., `MyStr0ng!Passw0rd#2026`)
   - **Confirm password:** Same password

   > **Write down the username and password.** You'll need them for the environment variables.

5. **Instance configuration:**
   - **DB instance class:** `db.t3.micro` (free tier) or `db.t4g.small` for more power
   - `db.t3.micro` has 1 vCPU, 1 GB RAM — fine for starting out

6. **Storage:**
   - **Storage type:** gp3
   - **Allocated storage:** 20 GB
   - **Storage autoscaling:** Enable it (checkbox), max 50 GB

7. **Connectivity:**
   - **Compute resource:** Select **Don't connect to an EC2 compute resource** (we'll handle it via security groups)
   - **VPC:** Default VPC (same as your EC2)
   - **DB subnet group:** Default
   - **Public access:** **No** ← VERY IMPORTANT. The database should NOT be accessible from the internet.
   - **VPC security group:** Choose **Choose existing** → pick `farmapp-rds-sg`
   - **Availability zone:** No preference

8. **Database authentication:** Password authentication

9. **Additional configuration:**
   - **Initial database name:** `farmapp_db`
   - Leave everything else as default

10. Click **Create database**

11. Wait 5–10 minutes for the database to become **Available**

### Get the RDS Endpoint

1. Once available, click on `farmapp-db`
2. Under **Connectivity & security**, find the **Endpoint** — it looks like:
   ```
   farmapp-db.xxxxxxxxxx.ap-south-1.rds.amazonaws.com
   ```
3. **Write this down.** This is the hostname for your database connection.

### Enable PostGIS Extension

SSH into your EC2 and run:

```bash
# Install PostgreSQL client
sudo apt update && sudo apt install -y postgresql-client

# Connect to the RDS database
psql -h farmapp-db.xxxxxxxxxx.ap-south-1.rds.amazonaws.com \
     -U farmapp_admin \
     -d farmapp_db \
     -p 5432
```

Enter your password when prompted. Then run:

```sql
-- Enable PostGIS extension (required by Django's contrib.gis)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify it's installed
SELECT PostGIS_Version();

-- Exit
\q
```

You should see something like `3.5 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`. PostGIS is now active.

> **Note:** RDS PostgreSQL supports PostGIS out of the box — no special AMI needed. You just need to run `CREATE EXTENSION postgis` once.

> **Troubleshooting: "Connection timed out"**
>
> - Check that both EC2 and RDS are in the same VPC
> - Check that `farmapp-rds-sg` allows port 5432 from `farmapp-ec2-sg`
> - Check that RDS has "Public access: No" (and not "Yes")

---

## Step 6 — Install Docker and Caddy on EC2

SSH into your EC2 instance and run the following commands.

### Install Docker

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker's repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to the docker group (so you don't need sudo for docker commands)
sudo usermod -aG docker ubuntu

# Apply the group change (or log out and back in)
newgrp docker

# Verify Docker is working
docker --version           # Should show Docker 2x.x
docker compose version     # Should show Docker Compose v2.x
docker run hello-world     # Should print "Hello from Docker!"
```

> **Why Docker on EC2?** Docker packages your entire app — Python, GDAL, GEOS, PROJ, all dependencies — into a single image. No more "missing library" errors. The same image that GitHub Actions builds is what runs on the server.

### Install Caddy (HTTPS reverse proxy)

```bash
# Install Caddy's official repository
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list

# Install Caddy
sudo apt update
sudo apt install -y caddy

# Verify
caddy version    # Should show v2.x.x
```

> **Why Caddy runs natively (not in Docker)?** Caddy manages TLS certificates that persist across deploys. Running it natively outside Docker means app container restarts don't affect HTTPS. It's also simpler to configure.

---

## Step 7 — S3 Bucket for File Uploads

Your app uses S3 for all file uploads (Aadhaar documents, PAN/GST/CIN certificates, farm documents, video thumbnails) via `django-storages`.

### Create the S3 Bucket

1. Go to AWS Console → search **S3** → click it
2. Click **Create bucket**
3. Fill in:
   - **Bucket name:** `your-farmapp-bucket-name` (must be globally unique across all of AWS)
   - **Region:** Same region as your EC2 and RDS (e.g., `ap-south-1`)
   - **Object Ownership:** ACLs disabled (recommended)
   - **Block all public access:** **ON** (checked) ← Keep this on. Files should be private — the app generates signed URLs for access.
   - **Bucket Versioning:** Disable (not needed for uploaded documents)
   - **Default encryption:** SSE-S3 (default, free)
4. Click **Create bucket**

### Create an IAM User for S3 Access

1. Go to AWS Console → search **IAM** → click it
2. Go to **Users** → **Create user**
3. **User name:** `farmapp-s3-user`
4. Click **Next**
5. **Permissions:** Select **Attach policies directly**
6. Search for and select: `AmazonS3FullAccess` (for simplicity — you can scope it down later to just your bucket)
7. Click **Next** → **Create user**
8. Click on the user → **Security credentials** tab → **Create access key**
9. Select **Application running on an AWS compute service** → **Next**
10. **Description:** `FarmApp backend S3 access`
11. Click **Create access key**
12. **Copy the Access key ID and Secret access key** — you'll never see the secret again

> **Write these down.** You'll put them in the `.env` file in the next step.

### Files the App Stores in S3

| Path in S3                           | What's Stored             |
| ------------------------------------ | ------------------------- |
| `documents/fpo/pan/`                 | FPO PAN card files        |
| `documents/fpo/cin/`                 | FPO CIN certificate files |
| `documents/fpo/gst/`                 | FPO GST certificate files |
| `documents/farmer/aadhaar/`          | Farmer Aadhaar card files |
| `documents/farmer/farm/`             | Farm documents            |
| `featured-section/video/thumbnails/` | Featured video thumbnails |
| `tutorial-section/video/tutorials/`  | Tutorial video thumbnails |

---

## Step 8 — Set Up Docker Hub

We need a Docker Hub account to store our built Docker images. GitHub Actions will push images here, and the EC2 server will pull them.

### 8a. Create a Docker Hub Account

1. Go to [hub.docker.com](https://hub.docker.com) and sign up (free)
2. **Write down your username** (e.g., `yourcompany`)

### 8b. Create an Access Token

1. Go to **Account Settings** → **Personal access tokens**
2. Click **Generate new token**
3. **Description:** `GitHub Actions CI/CD`
4. **Access permissions:** Read & Write
5. Click **Generate**
6. **Copy the token** — you'll never see it again

> **Write down:**
>
> - Docker Hub username: `yourcompany`
> - Docker Hub token: `dckr_pat_xxxxxxxxxxxxxxxxxxxx`

You'll add these as GitHub Secrets in Step 12.

---

## Step 9 — Prepare the Server for First Deploy

SSH into your EC2 and set up the project directory with config files.

### 9a. Create the Project Directory

```bash
mkdir -p /home/ubuntu/erde-agro-farmapp-backend
cd /home/ubuntu/erde-agro-farmapp-backend
```

### 9b. Create the `.env` File

```bash
nano /home/ubuntu/erde-agro-farmapp-backend/.env
```

Paste the following, replacing the placeholder values:

```env
# Django
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=your-very-long-random-secret-key-here
ALLOWED_HOSTS=api.yourdomain.com,YOUR_ELASTIC_IP
DEBUG=False

# CORS — your mobile app or frontend origin(s)
CORS_ALLOWED_ORIGINS=https://app.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://api.yourdomain.com

# Database — use the RDS endpoint from Step 5
DB_NAME=farmapp_db
DB_USER=farmapp_admin
DB_PASSWORD=MyStr0ng!Passw0rd#2026
DB_HOST=farmapp-db.xxxxxxxxxx.ap-south-1.rds.amazonaws.com
DB_PORT=5432

# AWS S3 — for file uploads (from Step 7)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION_NAME=ap-south-1
AWS_STORAGE_BUCKET_NAME=your-farmapp-bucket-name

# Firebase — path INSIDE the Docker container (don't change this)
FIREBASE_SERVICE_ACCOUNT_PATH=/app/config/firebase-service-account.json

# Docker image (will be overwritten by CI/CD, but set a default)
DOCKER_IMAGE=yourcompany/farmapp-backend:latest

# Satellite Service — connection to your satellite-service API
SATELLITE_SERVICE_BASE_URL=https://satellite-api.yourdomain.com
SATELLITE_SERVICE_TIMEOUT=30
SATELLITE_INTERNAL_AUTH_ISSUER=your_issuer
SATELLITE_INTERNAL_AUTH_AUDIENCE=your_audience
SATELLITE_INTERNAL_AUTH_SHARED_SECRET=your_shared_secret
SATELLITE_INTERNAL_AUTH_ALGORITHM=HS256
```

Save and exit (`Ctrl + X` → `Y` → `Enter`).

> **Important:** The `FIREBASE_SERVICE_ACCOUNT_PATH` is `/app/config/firebase-service-account.json` — this is the path **inside the Docker container**, not on the host. The `docker-compose.prod.yml` mounts the host file to this path.

### Generate a Strong SECRET_KEY

On your Mac or on the server, run:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copy the output and paste it as the `SECRET_KEY` value.

### Breakdown of the Database Variables

```
DB_HOST=farmapp-db.xxxxxxxxxx.ap-south-1.rds.amazonaws.com
        ──────────────────────────────────────────────────────
        RDS Endpoint (from Step 5)

DB_NAME=farmapp_db         ← The "Initial database name" from Step 5
DB_USER=farmapp_admin      ← The "Master username" from Step 5
DB_PASSWORD=MyStr0ng!...   ← The "Master password" from Step 5
DB_PORT=5432               ← Default PostgreSQL port
```

### 9c. Upload Firebase Service Account Key

From your **local terminal** (not SSH):

```bash
scp -i ~/.ssh/farmapp-key.pem \
  /path/to/your/firebase-service-account.json \
  ubuntu@YOUR_ELASTIC_IP:/home/ubuntu/erde-agro-farmapp-backend/config/firebase-service-account.json
```

Or create the directory and paste it manually on the server:

```bash
mkdir -p /home/ubuntu/erde-agro-farmapp-backend/config
nano /home/ubuntu/erde-agro-farmapp-backend/config/firebase-service-account.json
# Paste the JSON content, save and exit
```

Secure the file:

```bash
chmod 600 /home/ubuntu/erde-agro-farmapp-backend/config/firebase-service-account.json
```

### 9d. Copy the Docker Compose Production File

From your **local terminal**, copy the production compose file to the server:

```bash
scp -i ~/.ssh/farmapp-key.pem \
  docker-compose.prod.yml \
  ubuntu@YOUR_ELASTIC_IP:/home/ubuntu/erde-agro-farmapp-backend/docker-compose.prod.yml
```

> **What's on the server now:**
>
> ```
> /home/ubuntu/erde-agro-farmapp-backend/
> ├── .env                                    ← all secrets and config
> ├── docker-compose.prod.yml                 ← how to run the container
> └── config/
>     └── firebase-service-account.json       ← Firebase auth key
> ```
>
> That's it. No Python, no GDAL, no venv on the server. Docker handles everything.

---

## Step 10 — Set Up HTTPS with Caddy

### What is Caddy?

Caddy is a web server that **automatically gets and renews HTTPS certificates** for free (via Let's Encrypt). No manual certificate management needed.

It will sit in front of our Docker container:

```
Internet → Caddy (port 443, HTTPS) → Docker: Gunicorn (port 8000, localhost)
```

### Configure Caddy

```bash
sudo nano /etc/caddy/Caddyfile
```

**Delete everything** in the file and replace with:

```
api.yourdomain.com {
    reverse_proxy 127.0.0.1:8000

    # Allow large file uploads (documents, images)
    request_body {
        max_size 20MB
    }
}
```

Replace `api.yourdomain.com` with your actual domain/subdomain.

**That's the entire config.** Caddy is that simple. It will:

1. Listen on ports 80 and 443
2. Automatically obtain a Let's Encrypt TLS certificate for your domain
3. Automatically redirect HTTP → HTTPS
4. Forward all HTTPS traffic to the Docker container on port 8000
5. Automatically renew the certificate before it expires
6. Allow file uploads up to 20 MB

### Restart Caddy

```bash
# Validate the config
sudo caddy validate --config /etc/caddy/Caddyfile

# Restart Caddy to apply
sudo systemctl restart caddy

# Check status
sudo systemctl status caddy
```

> **Important:** Caddy MUST be able to reach ports 80 and 443 from the internet for the automatic certificate to work. That's why we opened those ports in the Security Group in Step 2.

---

## Step 11 — Point Your Domain to EC2

For HTTPS to work, your domain must point to your EC2's Elastic IP.

### Using Your DNS Provider (Bigrock / GoDaddy / Cloudflare / etc.)

1. Go to your DNS provider's dashboard (and then CPanel if using Bigrock)
2. Add an **A record**:
   - **Name / Host:** `api` (or whatever subdomain you chose, e.g., `farmapp-api`)
   - **Type:** A
   - **Value / Points to:** Your Elastic IP (e.g., `54.123.45.67`)
   - **TTL:** 300 (or "Automatic")

3. Wait for DNS propagation (can take 5 minutes to a few hours)

---

## Step 12 — Set Up GitHub Actions CI/CD

This is the magic — after this step, every `git push` to `main` will automatically build and deploy your app.

### 12a. Add GitHub Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

| Secret Name           | Value                                          | Where It Comes From |
| --------------------- | ---------------------------------------------- | ------------------- |
| `DOCKER_HUB_USERNAME` | Your Docker Hub username (e.g., `yourcompany`) | Step 8              |
| `DOCKER_HUB_TOKEN`    | Your Docker Hub access token                   | Step 8              |
| `EC2_HOST`            | Your Elastic IP (e.g., `54.123.45.67`)         | Step 3              |
| `EC2_SSH_KEY`         | The **entire contents** of `farmapp-key.pem`   | Step 1              |

For `EC2_SSH_KEY`, on your Mac run:

```bash
cat ~/.ssh/farmapp-key.pem
```

Copy the **entire output** (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`) and paste it as the secret value.

### 12b. The Workflow File

The workflow file is already in your repo at `.github/workflows/deploy.yml`. Here's what it does:

```
On every push to main:

1. Checkout the code
2. Log in to Docker Hub
3. Build the Docker image
   - Installs Python 3.13 + GDAL + GEOS + PROJ
   - Installs all pip dependencies
   - Copies the application code
4. Push the image to Docker Hub (tagged with commit SHA + latest)
5. SSH into your EC2 server
6. Pull the new image
7. Restart the container with docker compose
8. Clean up old images
```

### 12c. Understanding the Docker Files

**`Dockerfile`** — the recipe for building the Docker image:

```
python:3.13-slim base image
        │
        ▼
Install system packages (GDAL, GEOS, PROJ, libpq, Pillow deps)
        │
        ▼
pip install requirements.txt (+ gunicorn)
        │
        ▼
Copy application code
        │
        ▼
Run entrypoint.sh on container start
```

**`scripts/entrypoint.sh`** — runs every time the container starts:

1. `python manage.py migrate --noinput` — applies any new database migrations
2. `python manage.py collectstatic --noinput` — collects static files for WhiteNoise
3. Starts Gunicorn with 3 workers, listening on port 8000

> **This means migrations are automatic.** Every deploy runs migrations. If there are no new migrations, it's a no-op (takes <1 second).

**`docker-compose.prod.yml`** — how to run the container on the server:

- Pulls the image from Docker Hub
- Binds port 8000 to localhost only (Caddy proxies external traffic)
- Loads environment variables from `.env`
- Mounts the Firebase service account key into the container
- Auto-restarts if the container crashes

---

## Step 13 — First Deployment

Now let's trigger the first deployment.

### Option A: Push to main (recommended)

From your local machine:

```bash
git add .
git commit -m "Add Docker and CI/CD setup"
git push origin main
```

Go to your GitHub repo → **Actions** tab → you'll see the workflow running. It takes ~2-3 minutes.

### Option B: Manual deploy (if you want to test first)

SSH into your EC2 and run manually:

```bash
cd /home/ubuntu/erde-agro-farmapp-backend

# Log in to Docker Hub
docker login -u yourcompany

# Pull and start the container
export DOCKER_IMAGE=yourcompany/farmapp-backend:latest
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Verify It's Working

```bash
# Check the container is running
docker ps

# You should see:
# CONTAINER ID   IMAGE                              STATUS          PORTS
# abc123         yourcompany/farmapp-backend:latest  Up 10 seconds   127.0.0.1:8000->8000/tcp

# Check the logs (migrations + gunicorn startup)
docker logs farmapp-backend

# You should see:
# Running database migrations...
# Operations to perform: ...
# Collecting static files...
# Starting Gunicorn with 3 workers...

# Test the API
curl http://127.0.0.1:8000/auth/register/

# Test via HTTPS (if DNS is set up)
curl https://api.yourdomain.com/auth/register/
```

---

## Step 14 — Create Django Superuser

For the Django admin panel, create a superuser. Run this command **inside the Docker container**:

```bash
docker exec -it farmapp-backend python manage.py createsuperuser
```

Follow the prompts to set up an admin username and password. You'll use this to access the Django admin panel at `https://api.yourdomain.com/admin/`.

---

## Step 15 — Security Hardening Checklist

Go through this checklist to make sure your setup is secure:

### Server Security

```bash
# Enable automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Select "Yes" when prompted
```

```bash
# Set up a basic firewall (UFW) as an extra layer
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP (Caddy redirect)
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable           # Activate the firewall

# Verify
sudo ufw status
```

### Security Checklist

- [ ] **RDS Public Access is OFF** — database only reachable from EC2
- [ ] **RDS password is strong** — not `password123` or similar
- [ ] **SSH is restricted to your IP** — Security Group has "My IP", not 0.0.0.0/0
- [ ] **S3 bucket blocks public access** — "Block all public access" is ON
- [ ] **SECRET_KEY is unique and random** — not the default insecure one from dev
- [ ] **DEBUG is False** — `.env` has `DEBUG=False`
- [ ] **.env is NOT in the git repo** — it lives only on the server
- [ ] **firebase-service-account.json is NOT in the git repo** — it lives only on the server
- [ ] **.pem file permissions are 400** — `chmod 400 ~/.ssh/farmapp-key.pem`
- [ ] **firebase-service-account.json permissions are 600** — `chmod 600 config/firebase-service-account.json`
- [ ] **Docker container binds to 127.0.0.1** — not 0.0.0.0 (only Caddy faces the internet)
- [ ] **UFW firewall is enabled** — only ports 22, 80, 443 open
- [ ] **Automatic security updates enabled** — unattended-upgrades installed
- [ ] **ALLOWED_HOSTS is set** — only your domain and Elastic IP, not `*`
- [ ] **GitHub Secrets are set** — SSH key and Docker Hub token are stored securely

---

## Step 16 — Monitoring and Logs

### Application Logs

```bash
# Live container logs (Django + Gunicorn output)
docker logs -f farmapp-backend

# Last 100 lines
docker logs --tail 100 farmapp-backend

# Caddy logs
sudo journalctl -u caddy -f
```

### Container Status

```bash
# Is the container running?
docker ps

# Container resource usage (CPU, memory)
docker stats farmapp-backend --no-stream
```

### Disk Space

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up old images (safe to run anytime)
docker image prune -f

# Nuclear option — clean everything unused (images, containers, volumes)
docker system prune -f
```

### Check If Everything Is Running

```bash
# Container status
docker ps

# Caddy status
sudo systemctl status caddy

# Test API locally
curl -s http://127.0.0.1:8000/auth/register/ | python3 -m json.tool

# Test HTTPS from outside
curl https://api.yourdomain.com/auth/register/

# Django Admin
# Visit https://api.yourdomain.com/admin/ in your browser
```

### Django Management Commands

Run any Django management command inside the container:

```bash
# Django shell
docker exec -it farmapp-backend python manage.py shell

# Check migrations status
docker exec -it farmapp-backend python manage.py showmigrations

# Run a specific migration
docker exec -it farmapp-backend python manage.py migrate appname

# Create superuser
docker exec -it farmapp-backend python manage.py createsuperuser
```

---

## Architecture Diagram

```
┌──────────────┐         ┌────────────────────────────────────────────────────┐
│   Developer  │         │              GitHub                                │
│   pushes to  ├────────►│  Actions CI/CD Pipeline                           │
│   main       │         │  1. Build Docker image (Python + GDAL + app)      │
└──────────────┘         │  2. Push to Docker Hub                            │
                         │  3. SSH into EC2 → pull → restart container       │
                         └───────────────────────┬────────────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud (ap-south-1)                                │
│                                                                                │
│  ┌──────────────────── VPC (Default) ──────────────────────────────────────┐   │
│  │                                                                          │   │
│  │  ┌────────────────── EC2 Instance ─────────────────────────────────┐    │   │
│  │  │  farmapp-backend-server (Ubuntu 24.04, t3.small)                 │    │   │
│  │  │                                                                   │    │   │
│  │  │  ┌──────────┐    ┌─────────────────────────────────────────┐     │    │   │
│  │  │  │  Caddy    │───►│  Docker Container                       │     │    │   │
│  │  │  │  :443     │    │  ┌─────────────────────────────────┐   │     │    │   │
│  │  │  │  (HTTPS)  │    │  │  Gunicorn + Django + GDAL       │   │     │    │   │
│  │  │  └──────────┘    │  │  :8000                           │   │     │    │   │
│  │  │                   │  └──────┬──────┬──────┬────────────┘   │     │    │   │
│  │  │                   └─────────┼──────┼──────┼────────────────┘     │    │   │
│  │  │                             │      │      │                       │    │   │
│  │  └─────────────────────────────┼──────┼──────┼───────────────────────┘    │   │
│  │                                │      │      │                            │   │
│  │                                ▼      │      │                            │   │
│  │  ┌───────────────────────────────┐    │      │                            │   │
│  │  │   RDS PostgreSQL 17 + PostGIS │    │      │                            │   │
│  │  │   farmapp_db                  │    │      │                            │   │
│  │  └───────────────────────────────┘    │      │                            │   │
│  │                                       │      │                            │   │
│  └───────────────────────────────────────┼──────┼────────────────────────────┘   │
│                                          │      │                                │
│                                          ▼      │                                │
│  ┌─────────────────────────────────────────┐    │                                │
│  │   S3 Bucket                             │    │                                │
│  │   (documents, thumbnails)               │    │                                │
│  └─────────────────────────────────────────┘    │                                │
│                                                  │                                │
└──────────────────────────────────────────────────┼────────────────────────────────┘
         ▲                                         │
         │ HTTPS (port 443)                        ▼
         │                               ┌──────────────────┐
    ┌────┴─────┐                         │  Firebase Auth   │
    │ Internet │                         │  (Google Cloud)  │
    │ (Mobile  │                         └──────────────────┘
    │  App)    │                                 ▲
    └──────────┘                                 │
                                       ┌─────────┴──────────┐
                                       │  Satellite Service  │
                                       │  (separate EC2)     │
                                       └────────────────────┘
```

---

## How Deployments Work (After Setup)

After the one-time setup is done, **every deployment is just a `git push`:**

```bash
# On your local machine, after making code changes:
git add .
git commit -m "your changes"
git push origin main
```

That's it. Here's what happens automatically:

```
1. GitHub Actions detects the push to main               (~5 seconds)
2. Checks out your code                                  (~10 seconds)
3. Builds the Docker image                               (~1-2 minutes)
   - Python 3.13 + GDAL + GEOS + PROJ installed
   - pip install requirements.txt
   - Your application code copied in
4. Pushes image to Docker Hub                            (~30 seconds)
5. SSHes into your EC2 server                            (~5 seconds)
6. Pulls the new image                                   (~15 seconds)
7. Restarts the container                                (~5 seconds)
   - Runs migrations automatically
   - Collects static files
   - Starts Gunicorn
8. Cleans up old images                                  (~2 seconds)

Total: ~2-3 minutes from push to live
```

### What if you need to change environment variables?

SSH into EC2, edit `.env`, and restart the container:

```bash
ssh -i ~/.ssh/farmapp-key.pem ubuntu@YOUR_ELASTIC_IP
cd /home/ubuntu/erde-agro-farmapp-backend
nano .env
# Make your changes, save and exit
docker compose -f docker-compose.prod.yml up -d
```

### What if you need to update the Firebase key?

```bash
scp -i ~/.ssh/farmapp-key.pem \
  /path/to/new/firebase-service-account.json \
  ubuntu@YOUR_ELASTIC_IP:/home/ubuntu/erde-agro-farmapp-backend/config/firebase-service-account.json

# Then restart the container
ssh -i ~/.ssh/farmapp-key.pem ubuntu@YOUR_ELASTIC_IP
cd /home/ubuntu/erde-agro-farmapp-backend
docker compose -f docker-compose.prod.yml restart
```

### What if a deploy fails?

1. Check GitHub Actions → click the failed run → read the logs
2. If it's a build error → fix the code, push again
3. If it's a deploy error → SSH into EC2, check `docker logs farmapp-backend`
4. To rollback to a previous version:
   ```bash
   # On EC2, deploy a specific commit
   export DOCKER_IMAGE=yourcompany/farmapp-backend:PREVIOUS_COMMIT_SHA
   docker compose -f docker-compose.prod.yml pull
   docker compose -f docker-compose.prod.yml up -d
   ```

---

## Common Troubleshooting

### "502 Bad Gateway" from Caddy

**Cause:** The Docker container isn't running.
**Fix:**

```bash
docker ps                           # Is the container running?
docker logs farmapp-backend         # What went wrong?
docker compose -f docker-compose.prod.yml up -d   # Restart it
```

### Container keeps restarting

**Cause:** App crashes on startup (bad env var, DB connection failed, etc.)
**Fix:**

```bash
# See the crash logs
docker logs --tail 50 farmapp-backend

# Common causes:
# - DB_HOST wrong → check RDS endpoint in .env
# - SECRET_KEY missing → check .env
# - Firebase key not mounted → check config/firebase-service-account.json exists
```

### "Connection refused" when testing locally

**Cause:** Container isn't running or port isn't mapped.
**Fix:**

```bash
docker ps                                      # Check container status
curl http://127.0.0.1:8000/auth/register/      # Is Gunicorn responding?
ss -tlnp | grep 8000                           # Is anything listening on 8000?
```

### "DisallowedHost" error

**Cause:** Your domain is not in `ALLOWED_HOSTS`.
**Fix:** Update `.env`:

```
ALLOWED_HOSTS=api.yourdomain.com,YOUR_ELASTIC_IP
```

Then restart:

```bash
docker compose -f docker-compose.prod.yml up -d
```

### GitHub Actions deploy fails with SSH error

**Cause:** `EC2_SSH_KEY` secret is wrong, or SSH Security Group has wrong IP.
**Fix:**

- Re-paste the entire `.pem` file contents as the `EC2_SSH_KEY` GitHub secret
- Make sure the EC2 Security Group SSH rule allows GitHub Actions IPs (or temporarily set source to `0.0.0.0/0` for the first deploy, then lock it down)

> **Note:** GitHub Actions runs from GitHub's IP ranges, not your personal IP. For SSH to work from GitHub Actions, you may need to allow SSH from `0.0.0.0/0` or use [GitHub's published IP ranges](https://api.github.com/meta). Alternatively, keep SSH restricted to "My IP" and add a second SSH rule for `0.0.0.0/0` — this is an acceptable tradeoff since SSH still requires the private key.

### File uploads failing (S3 errors)

**Cause:** AWS credentials wrong or bucket doesn't exist.
**Fix:**

```bash
# Test inside the container
docker exec -it farmapp-backend python -c "
import boto3
s3 = boto3.client('s3')
print(s3.list_buckets()['Buckets'])
"
```

If that fails, check `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_STORAGE_BUCKET_NAME` in `.env`.

### Can't SSH after IP change

**Cause:** Your home IP changed, and SSH is restricted to the old IP.
**Fix:** Go to EC2 → Security Groups → `farmapp-ec2-sg` → Edit inbound rules → Update the SSH source to your new IP (select "My IP").

### Database migration errors

**Cause:** PostGIS extension not enabled on RDS.
**Fix:**

```bash
sudo apt install -y postgresql-client
psql -h YOUR_RDS_ENDPOINT -U farmapp_admin -d farmapp_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### Out of disk space

**Cause:** Old Docker images piling up.
**Fix:**

```bash
# See what's using space
docker system df

# Clean up old images
docker image prune -f

# Nuclear option if needed
docker system prune -f
```

### RDS out of storage

**Fix:** Go to RDS → Modify → increase storage. If autoscaling is on, this should happen automatically up to your max limit.

---

## Cost Estimate

Here's approximately what this setup costs per month (USD), assuming the `ap-south-1` (Mumbai) region:

| Service        | Instance                         | Monthly Cost                 |
| -------------- | -------------------------------- | ---------------------------- |
| EC2            | t3.small (2 vCPU, 2GB)           | ~$15                         |
| RDS            | db.t3.micro (1 vCPU, 1GB)        | ~$13 (or free for 12 months) |
| S3             | Storage + requests               | ~$1–3 (depends on uploads)   |
| Elastic IP     | Associated with running instance | $0 (free while attached)     |
| Docker Hub     | Free plan (1 private repo)       | $0                           |
| GitHub Actions | Free tier (2,000 min/month)      | $0                           |
| Data Transfer  | First 100 GB/month               | $0 (free tier)               |
| **Total**      |                                  | **~$29–31/month**            |

> **Free tier (first 12 months):** If your AWS account is new, EC2 t3.micro (750 hrs/month) and RDS db.t3.micro (750 hrs/month) are free. That drops the cost to **~$1–3/month** (just S3).

---

## Quick Reference Card

```
SSH into server:       ssh -i ~/.ssh/farmapp-key.pem ubuntu@YOUR_ELASTIC_IP

Deploy (automated):    git push origin main
Deploy (manual):       cd ~/erde-agro-farmapp-backend && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d

Container logs:        docker logs -f farmapp-backend
Container status:      docker ps
Container restart:     cd ~/erde-agro-farmapp-backend && docker compose -f docker-compose.prod.yml restart
Container stop:        cd ~/erde-agro-farmapp-backend && docker compose -f docker-compose.prod.yml down

Caddy logs:            sudo journalctl -u caddy -f
Caddy status:          sudo systemctl status caddy

Django shell:          docker exec -it farmapp-backend python manage.py shell
Django migrations:     docker exec -it farmapp-backend python manage.py showmigrations
Django superuser:      docker exec -it farmapp-backend python manage.py createsuperuser

Health check:          curl https://api.yourdomain.com/auth/register/
Django Admin:          https://api.yourdomain.com/admin/

DB connect:            psql -h YOUR_RDS_ENDPOINT -U farmapp_admin -d farmapp_db

Edit env vars:         nano ~/erde-agro-farmapp-backend/.env && cd ~/erde-agro-farmapp-backend && docker compose -f docker-compose.prod.yml up -d
Clean disk:            docker system prune -f

Rollback:              export DOCKER_IMAGE=yourcompany/farmapp-backend:COMMIT_SHA && cd ~/erde-agro-farmapp-backend && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d
```
