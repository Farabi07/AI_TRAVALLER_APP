# 🚀 Deploy Now - IP Only (No Domain Required)

Your application is configured to work with **IP only** (no domain needed).

---

## ⚡ Quick Deploy Steps

### **Step 1: Create Database (5-10 minutes)**

```bash
# Edit password first
nano setup-rds.sh
# Line 24: DB_PASSWORD="YourSecurePassword123!"

# Create RDS
./setup-rds.sh

# ⚠️ SAVE the DATABASE_URL output!
```

---

### **Step 2: Connect to EC2**

```bash
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218
```

If you get "Host key verification failed", first run:
```bash
ssh-keygen -R 63.177.70.218
```

---

### **Step 3: Setup Application on EC2**

```bash
# Clone repository
git clone https://github.com/Farabi07/AI_TRAVALLER_APP.git AI-Travel-App
cd AI-Travel-App

# Create .env file
nano .env
```

**Paste this configuration** (update DATABASE_URL and SECRET_KEY):

```bash
# Django
SECRET_KEY=django-insecure-CHANGE-THIS-TO-RANDOM-STRING
DEBUG=False
ALLOWED_HOSTS=63.177.70.218,localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=start_project.settings

# Database (from setup-rds.sh output)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/ai_travel_db

# AWS S3 (optional - leave commented for now)
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret
# AWS_STORAGE_BUCKET_NAME=ai-travel-media
# AWS_S3_REGION_NAME=us-east-1

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@hitmanjacktravel.com
```

**Generate SECRET_KEY:**
```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Copy the output and paste it in your .env file.

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

---

### **Step 4: Deploy Application**

```bash
# Make sure you're in AI-Travel-App directory
cd ~/AI-Travel-App

# Start services
docker-compose -f docker-compose.prod.yml up -d --build

# Wait 30 seconds for containers to start
sleep 30

# Check if containers are running
docker-compose -f docker-compose.prod.yml ps

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# View logs (optional)
docker-compose -f docker-compose.prod.yml logs -f backend
```

Press `Ctrl+C` to exit logs.

---

### **Step 5: Test Your Application**

Open in browser:
- **Main site**: http://63.177.70.218
- **Admin panel**: http://63.177.70.218/admin
- **API**: http://63.177.70.218/api/v1/

Test superadmin login:
- **POST** http://63.177.70.218/api/v1/user/superadmin/login/
- Body: `{"email": "admin@example.com", "password": "yourpassword"}`

---

## 🔧 Useful Commands

```bash
# SSH to server
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Restart application
docker-compose -f docker-compose.prod.yml restart

# Stop application
docker-compose -f docker-compose.prod.yml down

# Update code and redeploy
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Check container status
docker-compose -f docker-compose.prod.yml ps

# View nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

---

## 🔐 Setup GitHub CI/CD (Optional)

Add these secrets to GitHub → Settings → Secrets:

| Secret Name | Value |
|-------------|-------|
| EC2_SSH_KEY | Content of `~/.ssh/ai-travel-key.pem` |
| EC2_HOST | `63.177.70.218` |
| EC2_USER | `ubuntu` |
| DATABASE_URL | Your RDS connection string |
| SECRET_KEY | Your Django secret key |
| ALLOWED_HOSTS | `63.177.70.218,localhost,127.0.0.1` |

Then:
```bash
git push origin main  # Auto-deploys to EC2!
```

---

## 🌐 Add Domain Later (Optional)

When your domain is ready:

1. **Point domain to IP** (GoDaddy DNS):
   - A record: `@` → `63.177.70.218`
   - A record: `www` → `63.177.70.218`

2. **Update configuration**:
   ```bash
   # SSH to EC2
   ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218
   cd AI-Travel-App
   
   # Update .env
   nano .env
   # Add domain to ALLOWED_HOSTS: 63.177.70.218,hitmanjacktravel.com,www.hitmanjacktravel.com
   
   # Switch to SSL nginx config
   cp nginx.conf nginx-ssl.conf
   nano docker-compose.prod.yml
   # Change: nginx-ip-only.conf → nginx.conf
   
   # Restart
   docker-compose -f docker-compose.prod.yml restart nginx
   ```

3. **Run from local machine**:
   ```bash
   ./setup-ssl.sh
   ```

---

## 🆘 Troubleshooting

**Can't SSH to EC2:**
```bash
chmod 400 ~/.ssh/ai-travel-key.pem
ssh-keygen -R 63.177.70.218
ssh -v -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218
```

**Can't access http://63.177.70.218:**
- Check EC2 security group allows port 80 from anywhere (0.0.0.0/0)
- Check containers: `docker-compose -f docker-compose.prod.yml ps`
- Check logs: `docker-compose -f docker-compose.prod.yml logs`

**Database connection error:**
- Verify DATABASE_URL in .env
- Check RDS security group allows EC2 IP
- Test: `docker-compose -f docker-compose.prod.yml exec backend python manage.py dbshell`

**502 Bad Gateway:**
- Backend not running: `docker-compose -f docker-compose.prod.yml restart backend`
- Check logs: `docker-compose -f docker-compose.prod.yml logs backend`

---

## ✅ Success Checklist

- [ ] RDS database created
- [ ] SSH connection works
- [ ] .env file created with correct DATABASE_URL
- [ ] SECRET_KEY generated and added to .env
- [ ] Containers running (`docker-compose ps` shows "Up")
- [ ] Migrations completed
- [ ] Superuser created
- [ ] Can access http://63.177.70.218
- [ ] Can login to admin panel
- [ ] Superadmin API login works

---

## 🎉 You're Live!

Your application is now accessible at:
**http://63.177.70.218**

No domain or SSL needed right now. You can add those later when ready! 🚀
