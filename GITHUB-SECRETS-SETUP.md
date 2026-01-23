# 🔐 GitHub Secrets Setup Guide

To enable automatic deployment, add these secrets to your GitHub repository.

## 📍 How to Add Secrets

1. Go to your GitHub repository: https://github.com/Farabi07/AI_TRAVALLER_APP
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

---

## 🔑 Required Secrets

### **1. EC2_SSH_KEY**

Your EC2 private key content. Get it from:

```bash
# On your local machine
cat ~/.ssh/your-ec2-key.pem
```

**Important:** Copy the ENTIRE content including:
- `-----BEGIN RSA PRIVATE KEY-----`
- All lines in between
- `-----END RSA PRIVATE KEY-----`

**Name:** `EC2_SSH_KEY`  
**Value:** Paste the entire private key content

---

### **2. EC2_HOST**

Your EC2 public IP address.

**Name:** `EC2_HOST`  
**Value:** `63.177.70.218`

---

### **3. DATABASE_URL**

Your RDS PostgreSQL connection string.

**Get RDS Endpoint:**
```bash
aws rds describe-db-instances \
    --db-instance-identifier database-aitravaler \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text \
    --region eu-central-1
```

**Format:**
```
postgresql://postgres:10203040%23@YOUR-RDS-ENDPOINT.eu-central-1.rds.amazonaws.com:5432/postgres
```

**⚠️ Important:** 
- Password `#` must be encoded as `%23`
- Replace `YOUR-RDS-ENDPOINT` with actual endpoint from AWS

**Name:** `DATABASE_URL`  
**Value:** `postgresql://postgres:10203040%23@database-aitravaler.xxxxx.eu-central-1.rds.amazonaws.com:5432/postgres`

---

## ✅ Verify Setup

After adding all secrets:

1. Go to **Actions** tab in GitHub
2. You should see "Deploy to EC2" workflow
3. Push a commit to test:
   ```bash
   git add .
   git commit -m "Test automatic deployment"
   git push origin main
   ```
4. Watch the deployment in **Actions** tab

---

## 🚀 How It Works

Every time you push to `main` branch:

1. ✅ GitHub Actions triggers automatically
2. ✅ Connects to your EC2 via SSH
3. ✅ Pulls latest code
4. ✅ Stops old containers
5. ✅ Builds and starts new containers
6. ✅ Runs database migrations
7. ✅ Collects static files
8. ✅ Verifies deployment

**Total time:** ~2-3 minutes

---

## 🔧 Manual Deployment (Backup)

If GitHub Actions fails, deploy manually:

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@63.177.70.218
cd ~/AI-Travel-App
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

---

## 📊 Monitor Deployments

### **View Deployment Logs:**
- GitHub → Your Repo → **Actions** → Click on latest run

### **View Application Logs:**
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@63.177.70.218
cd ~/AI-Travel-App
docker-compose -f docker-compose.prod.yml logs -f
```

### **Check Container Status:**
```bash
docker-compose -f docker-compose.prod.yml ps
```

---

## 🎯 Secrets Checklist

- [ ] `EC2_SSH_KEY` - Private key content
- [ ] `EC2_HOST` - `63.177.70.218`
- [ ] `DATABASE_URL` - RDS connection string with encoded password

**After adding all 3 secrets, you're ready to deploy automatically!** 🎉
