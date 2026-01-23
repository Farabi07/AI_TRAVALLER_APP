# AI Travel App - Quick Start

## 📋 What You Need Before Starting

1. **AWS Account** - Sign up at https://aws.amazon.com
2. **GoDaddy Domain** (optional) - For custom domain
3. **GitHub Account** - For code and CI/CD

---

## 🚀 Quick Deployment Steps

### **Step 1: Install AWS CLI**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### **Step 2: Configure AWS**
```bash
aws configure
# Enter your AWS credentials
```

### **Step 3: Create Database**
```bash
./setup-rds.sh
# Save the DATABASE_URL output!
```

### **Step 4: Create Server**
```bash
./setup-ec2.sh
# Save the EC2 IP address!
```

### **Step 5: Deploy Application**
```bash
# SSH into EC2
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218

# Go to app directory
cd AI-Travel-App

# Create .env file
nano .env
# Paste your configuration (see .env.example)

# Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create admin user
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### **Step 6: Setup CI/CD (Optional)**
1. Go to GitHub → Settings → Secrets
2. Add all required secrets (see DEPLOYMENT.md)
3. Push code to GitHub - auto-deploys!

### **Step 7: Add Domain (Optional)**
```bash
# Point domain to EC2 IP in GoDaddy
# Then run:
./setup-ssl.sh
```

---

## 🌐 Access Your App

- **Website**: `http://63.177.70.218`
- **Admin**: `http://63.177.70.218/admin`
- **With Domain**: `https://hitmanjacktravel.com`

---

## 📚 Full Documentation

See **DEPLOYMENT.md** for complete instructions.

---

## ⚡ What's Included

✅ Docker + Docker Compose  
✅ PostgreSQL RDS Database  
✅ Nginx Reverse Proxy  
✅ GitHub Actions CI/CD  
✅ SSL/HTTPS Support  
✅ Automated Deployment Scripts  
✅ Production-Ready Configuration  

---

## 💰 Cost

- **Free Tier**: $0/month (first 12 months)
- **After Free Tier**: ~$25-30/month

---

## 🆘 Need Help?

Check **DEPLOYMENT.md** for troubleshooting and detailed instructions.
