# 🎯 YOUR DEPLOYMENT GUIDE - Ready to Deploy!

Your AWS Resources:
- **EC2 IP**: `63.177.70.218`
- **RDS Database**: `database-AItravaler`
- **RDS Region**: `eu-central-1`
- **Database User**: `postgres`
- **Database Password**: `10203040#`

---

## 🚀 Step-by-Step Deployment

### **Step 1: Connect to Your EC2**

```bash
# Use your existing EC2 key pair
ssh -i /path/to/your-key.pem ubuntu@63.177.70.218

# Or if using .ppk file (PuTTY), convert it first:
# puttygen your-key.ppk -O private-openssh -o your-key.pem
# chmod 400 your-key.pem
```

---

### **Step 2: Install Docker on EC2** (if not already installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose git curl

# Add user to docker group
sudo usermod -aG docker ubuntu

# Log out and log back in for docker group to take effect
exit
# Then SSH back in
ssh -i /path/to/your-key.pem ubuntu@63.177.70.218

# Verify Docker
docker --version
docker-compose --version
```

---

### **Step 3: Clone Repository**

```bash
# Clone your project
git clone https://github.com/Farabi07/AI_TRAVALLER_APP.git AI-Travel-App
cd AI-Travel-App
```

---

### **Step 4: Create .env File**

```bash
nano .env
```

**Paste this EXACT configuration:**

```bash
# Django Configuration
SECRET_KEY=django-insecure-8k$m9n#@p2w$x7v!q3r&t5y^u8i*o0p-a1s2d3f4g5h6j7k8l9
DEBUG=False
ALLOWED_HOSTS=63.177.70.218,localhost,127.0.0.1
DJANGO_SETTINGS_MODULE=start_project.settings

# Database - YOUR RDS PostgreSQL
DATABASE_URL=postgresql://postgres:10203040%23@database-aitravaler.c9q8q8q8q8q8.eu-central-1.rds.amazonaws.com:5432/postgres

# Email Configuration (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@hitmanjacktravel.com

# AWS S3 (Optional - leave commented for now)
# AWS_ACCESS_KEY_ID=your-aws-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret
# AWS_STORAGE_BUCKET_NAME=ai-travel-media
# AWS_S3_REGION_NAME=eu-central-1
```

**⚠️ IMPORTANT NOTES:**
- The `#` in password is URL-encoded as `%23` in DATABASE_URL
- Replace `c9q8q8q8q8q8` with your actual RDS endpoint (get from AWS Console)
- Update EMAIL_HOST_USER and EMAIL_HOST_PASSWORD with your Gmail credentials

**Get your RDS Endpoint:**
```bash
# From AWS Console: RDS → Databases → database-AItravaler → Connectivity & security → Endpoint
# It will look like: database-aitravaler.xxxxxxxxxxxxx.eu-central-1.rds.amazonaws.com
```

**Get Gmail App Password:**
1. Go to: https://myaccount.google.com/apppasswords
2. Create app password for "Mail"
3. Use that password in EMAIL_HOST_PASSWORD

Save: `Ctrl+O`, `Enter`, `Ctrl+X`

---

### **Step 5: Verify Security Groups**

**Check EC2 Security Group allows:**
```bash
# Port 80 (HTTP) - from anywhere (0.0.0.0/0)
# Port 22 (SSH) - from your IP
# Port 443 (HTTPS) - from anywhere (optional)
```

**Check RDS Security Group allows:**
```bash
# Port 5432 (PostgreSQL) - from EC2 security group or EC2 private IP
```

**To check from EC2:**
```bash
# Test RDS connection (use your actual RDS endpoint)
telnet database-aitravaler.xxxxxxxxxxxxx.eu-central-1.rds.amazonaws.com 5432
# Should connect - press Ctrl+] then type 'quit' to exit
# If it doesn't connect, update RDS security group
```

---

### **Step 6: Deploy Application**

```bash
# Make sure you're in the project directory
cd ~/AI-Travel-App

# Start containers
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for containers to start
echo "Waiting for containers to start..."
sleep 30

# Check container status
docker-compose -f docker-compose.prod.yml ps

# View logs (optional)
docker-compose -f docker-compose.prod.yml logs backend
```

---

### **Step 7: Run Migrations & Setup**

```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Follow prompts:
# Email: admin@example.com
# Password: (your secure password)
# Confirm password: (same password)
```

---

### **Step 8: Test Your Application**

**Open in browser:**
- Main site: http://63.177.70.218
- Admin panel: http://63.177.70.218/admin
- API docs: http://63.177.70.218/api/v1/

**Test Superadmin Login API:**
```bash
curl -X POST http://63.177.70.218/api/v1/user/superadmin/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}'
```

---

## 🔧 Useful Commands

**View logs:**
```bash
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f nginx
```

**Restart services:**
```bash
docker-compose -f docker-compose.prod.yml restart
```

**Stop services:**
```bash
docker-compose -f docker-compose.prod.yml down
```

**Update and redeploy:**
```bash
cd ~/AI-Travel-App
git pull origin main
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

**Access Django shell:**
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell
```

**Database backup:**
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

---

## 🆘 Troubleshooting

**Container won't start:**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check .env file exists
cat .env

# Rebuild from scratch
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d --build
```

**Database connection error:**
```bash
# Test RDS connectivity
telnet database-aitravaler.xxxxx.eu-central-1.rds.amazonaws.com 5432

# Check DATABASE_URL format (password should be URL-encoded)
# The # character must be %23 in the URL

# Test from Django
docker-compose -f docker-compose.prod.yml exec backend python manage.py dbshell
```

**502 Bad Gateway:**
```bash
# Check if backend is running
docker-compose -f docker-compose.prod.yml ps

# Restart backend
docker-compose -f docker-compose.prod.yml restart backend

# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend
```

**Can't access website:**
```bash
# Check EC2 security group allows port 80
# Check containers are running
docker ps

# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx

# Test locally on EC2
curl http://localhost
```

---

## 📝 Quick Reference

**Your Resources:**
- EC2 IP: `63.177.70.218`
- RDS Endpoint: `database-aitravaler.xxxxx.eu-central-1.rds.amazonaws.com`
- RDS Database: `postgres`
- RDS User: `postgres`
- RDS Password: `10203040#` (use `10203040%23` in DATABASE_URL)
- Region: `eu-central-1`

**Important Files on EC2:**
- Application: `~/AI-Travel-App/`
- Environment: `~/AI-Travel-App/.env`
- Logs: `docker-compose -f docker-compose.prod.yml logs`

**Key Commands:**
```bash
# SSH to EC2
ssh -i /path/to/key.pem ubuntu@63.177.70.218

# Go to app directory
cd ~/AI-Travel-App

# View status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart
```

---

## ✅ Deployment Checklist

- [ ] SSH to EC2 works
- [ ] Docker installed on EC2
- [ ] Repository cloned
- [ ] .env file created with correct RDS endpoint
- [ ] RDS security group allows EC2 connection
- [ ] EC2 security group allows port 80
- [ ] Containers started successfully
- [ ] Migrations completed
- [ ] Static files collected
- [ ] Superuser created
- [ ] Can access http://63.177.70.218
- [ ] Admin panel works
- [ ] Superadmin API login works

---

## 🎉 Success!

Your application should now be live at: **http://63.177.70.218**

If you have any issues, check the troubleshooting section above or review the logs!
