# 🎯 Next Steps - Ready to Deploy!

Your configuration is now updated with:
- **EC2 IP**: `63.177.70.218`
- **Domain**: `hitmanjacktravel.com`

---

## ✅ Quick Deployment Checklist

### **Step 1: Configure GoDaddy DNS** (Do this FIRST!)

1. Log in to [GoDaddy DNS Management](https://dcc.godaddy.com/manage/hitmanjacktravel.com/dns)
2. Add/Edit these records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 63.177.70.218 | 600 |
| A | www | 63.177.70.218 | 600 |

3. Wait 5-15 minutes for DNS propagation
4. Verify: `dig +short hitmanjacktravel.com` (should show your IP)

---

### **Step 2: Update SSL Script Email**

```bash
nano setup-ssl.sh
# Change line 8: EMAIL="your-actual-email@gmail.com"
```

---

### **Step 3: Create AWS Infrastructure**

```bash
# 1. Create RDS Database (5-10 minutes)
./setup-rds.sh
# ⚠️ SAVE the DATABASE_URL output!

# 2. Create EC2 Instance (3-5 minutes) - SKIP if already created
# ./setup-ec2.sh
# You already have EC2 at 63.177.70.218
```

---

### **Step 4: Deploy Application**

```bash
# Connect to EC2
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218

# Clone repository (if not already there)
git clone https://github.com/Farabi07/AI_TRAVALLER_APP.git AI-Travel-App
cd AI-Travel-App

# Create .env file
nano .env
```

Paste this (update DATABASE_URL and SECRET_KEY):

```bash
# Django
SECRET_KEY=django-insecure-GENERATE-NEW-KEY-HERE
DEBUG=False
ALLOWED_HOSTS=63.177.70.218,hitmanjacktravel.com,www.hitmanjacktravel.com
DJANGO_SETTINGS_MODULE=start_project.settings

# Database (from setup-rds.sh)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/ai_travel_db

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=ai-travel-media
AWS_S3_REGION_NAME=us-east-1

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@hitmanjacktravel.com
```

Save and continue:

```bash
# Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Wait 30 seconds
sleep 30

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Check status
docker-compose -f docker-compose.prod.yml ps
```

---

### **Step 5: Test Access**

Open in browser:
- http://63.177.70.218 (should work immediately)
- http://hitmanjacktravel.com (after DNS propagates)

---

### **Step 6: Enable HTTPS (After DNS works)**

```bash
# Wait until http://hitmanjacktravel.com works!
# Then run from your local machine:
./setup-ssl.sh
```

This will:
- Generate SSL certificate from Let's Encrypt
- Configure nginx for HTTPS
- Auto-renew certificates every 60 days

---

### **Step 7: Setup CI/CD (Optional)**

Add these secrets to GitHub → Settings → Secrets:

| Secret Name | Value |
|-------------|-------|
| EC2_SSH_KEY | Content of `~/.ssh/ai-travel-key.pem` |
| EC2_HOST | `63.177.70.218` |
| EC2_USER | `ubuntu` |
| DATABASE_URL | Your RDS connection string |
| SECRET_KEY | Your Django secret key |
| ALLOWED_HOSTS | `63.177.70.218,hitmanjacktravel.com,www.hitmanjacktravel.com` |

Then push to main:
```bash
git push origin main
```

Auto-deployment activated! 🚀

---

## 🔥 Quick Commands Reference

```bash
# SSH to EC2
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Restart app
docker-compose -f docker-compose.prod.yml restart

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Check DNS
dig +short hitmanjacktravel.com
dig +short www.hitmanjacktravel.com
```

---

## ⚠️ Important Notes

1. **DNS First!** - Configure GoDaddy DNS before running setup-ssl.sh
2. **Generate SECRET_KEY**: Run in Django shell or use online generator
3. **Change RDS password** in setup-rds.sh before running
4. **Save DATABASE_URL** - you'll need it in .env file
5. **Update EMAIL** in setup-ssl.sh with your actual email

---

## 🆘 Troubleshooting

**Can't access http://63.177.70.218**
- Check EC2 security group allows port 80
- Check containers: `docker-compose -f docker-compose.prod.yml ps`
- Check logs: `docker-compose -f docker-compose.prod.yml logs`

**Domain doesn't work**
- Wait for DNS (check with `dig +short hitmanjacktravel.com`)
- Verify GoDaddy A records point to 63.177.70.218
- Can take up to 30 minutes

**SSL setup fails**
- Ensure domain resolves to EC2 IP first
- Port 80 must be accessible
- Run: `curl http://hitmanjacktravel.com/.well-known/acme-challenge/test`

---

## 🎉 You're Ready!

All configurations are updated. Follow the steps above to deploy.

See **DEPLOYMENT.md** for detailed documentation.
