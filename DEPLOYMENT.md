# 🚀 AI Travel App - Deployment Guide

Complete guide for deploying the AI Travel App to AWS EC2 with Docker and CI/CD.

---

## 📋 Prerequisites

- AWS Account
- AWS CLI installed and configured
- GitHub repository
- GoDaddy domain (optional, for custom domain)
- SSH client

---

## 🎯 Quick Start (Automated Setup)

### 1. **Install AWS CLI**

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

### 2. **Configure AWS Credentials**

```bash
aws configure
```

Enter:
- **AWS Access Key ID**: Your IAM access key
- **AWS Secret Access Key**: Your IAM secret key
- **Default region**: `us-east-1`
- **Default output format**: `json`

### 3. **Create RDS PostgreSQL Database**

```bash
# Make script executable
chmod +x setup-rds.sh

# Edit and set a secure password
nano setup-rds.sh
# Change: DB_PASSWORD="ChangeThisSecurePassword123!"

# Run the script
./setup-rds.sh
```

**Save the DATABASE_URL** output - you'll need it later!

### 4. **Create EC2 Instance**

```bash
# Make script executable
chmod +x setup-ec2.sh

# Run the script
./setup-ec2.sh
```

**Save the EC2 Public IP** - you'll need it!

### 5. **Configure Environment Variables**

SSH into your EC2 instance:

```bash
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@YOUR_EC2_IP
```

Create `.env` file:

```bash
cd AI-Travel-App
nano .env
```

Paste configuration:

```bash
# Django
SECRET_KEY=your-generated-secret-key
DEBUG=False
ALLOWED_HOSTS=63.177.70.218,hitmanjacktravel.com,www.hitmanjacktravel.com
DJANGO_SETTINGS_MODULE=start_project.settings

# Database (from setup-rds.sh output)
DATABASE_URL=postgresql://postgres:PASSWORD@RDS_ENDPOINT:5432/ai_travel_db

# AWS S3 (optional - for media storage)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=ai-travel-media
AWS_S3_REGION_NAME=us-east-1

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

### 6. **Deploy Application**

```bash
# Still on EC2
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for containers to start
sleep 15

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### 7. **Access Your Application**

Open in browser:
- **Main site**: `http://63.177.70.218`
- **Admin panel**: `http://63.177.70.218/admin`
- **With domain**: `http://hitmanjacktravel.com`

---

## 🔄 Setup CI/CD (GitHub Actions)

### 1. **Add GitHub Secrets**

Go to: GitHub repo → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `EC2_SSH_KEY` | Content of `~/.ssh/ai-travel-key.pem` |
| `EC2_HOST` | `63.177.70.218` |
| `EC2_USER` | `ubuntu` |
| `DATABASE_URL` | Your RDS connection string |
| `SECRET_KEY` | Your Django secret key |
| `ALLOWED_HOSTS` | `63.177.70.218,hitmanjacktravel.com,www.hitmanjacktravel.com` |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name |
| `AWS_S3_REGION_NAME` | `us-east-1` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_HOST_USER` | Your email |
| `EMAIL_HOST_PASSWORD` | App password |
| `DEFAULT_FROM_EMAIL` | `noreply@domain.com` |

### 2. **Test CI/CD**

```bash
# From your local machine
git add .
git commit -m "Setup deployment"
git push origin main
```

GitHub Actions will automatically deploy to EC2!

---

## 🌐 Setup Custom Domain (GoDaddy)

### 1. **Point Domain to EC2**

1. Log in to GoDaddy
2. Go to **DNS Management**
3. Add/Edit **A Record**:
   - **Type**: A
   - **Name**: `@`
   - **Value**: `63.177.70.218`
   - **TTL**: 600 seconds

4. Add **A Record** for www:
   - **Type**: A
   - **Name**: `www`
   - **Value**: `63.177.70.218`
   - **TTL**: 600 seconds

5. Wait 5-30 minutes for DNS propagation

### 2. **Setup SSL Certificate**

```bash
# Make script executable
chmod +x setup-ssl.sh

# Edit configuration
nano setup-ssl.sh
# Update: DOMAIN, EMAIL, EC2_HOST

# Run the script
./setup-ssl.sh
```

Your site will now be accessible via HTTPS! 🔒

---

## 📊 Manual Deployment

If you want to deploy manually without CI/CD:

```bash
# Make script executable
chmod +x deploy-ec2.sh

# Edit configuration
nano deploy-ec2.sh
# Update: EC2_HOST, KEY_PATH

# Run deployment
./deploy-ec2.sh
```

---

## 🛠️ Useful Commands

### **SSH into EC2**
```bash
ssh -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218
```

### **View Logs**
```bash
cd AI-Travel-App
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### **Restart Services**
```bash
docker-compose -f docker-compose.prod.yml restart
```

### **Stop Services**
```bash
docker-compose -f docker-compose.prod.yml down
```

### **Rebuild and Restart**
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### **Run Migrations**
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### **Collect Static Files**
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### **Access Django Shell**
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell
```

### **Database Backup**
```bash
docker-compose -f docker-compose.prod.yml exec backend python manage.py dumpdata > backup.json
```

---

## 🔒 Security Best Practices

### **1. Secure RDS Database**

```bash
# Get EC2 security group ID
EC2_SG=$(aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID \
    --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

# Get RDS security group ID
RDS_SG=$(aws rds describe-db-instances --db-instance-identifier ai-travel-db \
    --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)

# Remove public access
aws ec2 revoke-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0

# Allow only EC2
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG
```

### **2. Restrict SSH Access**

```bash
# Get your current IP
MY_IP=$(curl -s ifconfig.me)

# Update security group
aws ec2 revoke-security-group-ingress \
    --group-id YOUR_SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id YOUR_SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr $MY_IP/32
```

### **3. Enable CloudWatch Monitoring**

```bash
# Enable detailed monitoring
aws ec2 monitor-instances --instance-ids YOUR_INSTANCE_ID
```

### **4. Setup Automated Backups**

RDS backups are already configured (7-day retention).

For application data:

```bash
# Add to crontab on EC2
crontab -e

# Add line for daily backup at 2 AM
0 2 * * * cd /home/ubuntu/AI-Travel-App && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py dumpdata > /home/ubuntu/backups/backup-$(date +\%Y\%m\%d).json
```

---

## 💰 Cost Estimation

| Service | Instance Type | Monthly Cost | Free Tier |
|---------|---------------|--------------|-----------|
| EC2 | t2.micro | $8 | 750 hours/month (12 months) |
| EC2 | t2.medium | $34 | N/A |
| RDS | db.t3.micro | $15 | 750 hours/month (12 months) |
| Data Transfer | - | ~$5 | 15 GB/month free |
| **Total** | - | **$23-56/month** | **FREE** (first year) |

---

## 🆘 Troubleshooting

### **Can't SSH to EC2**
- Check security group allows SSH from your IP
- Verify key permissions: `chmod 400 ~/.ssh/ai-travel-key.pem`
- Try: `ssh -v -i ~/.ssh/ai-travel-key.pem ubuntu@63.177.70.218`

### **Database Connection Failed**
- Check RDS security group allows traffic from EC2
- Verify DATABASE_URL in .env
- Test connection: `docker-compose -f docker-compose.prod.yml exec backend python manage.py dbshell`

### **Container Won't Start**
- Check logs: `docker-compose -f docker-compose.prod.yml logs backend`
- Verify .env file exists and has correct values
- Check disk space: `df -h`

### **502 Bad Gateway**
- Backend container not running: `docker-compose -f docker-compose.prod.yml ps`
- Check backend logs for errors
- Restart: `docker-compose -f docker-compose.prod.yml restart backend`

### **SSL Certificate Issues**
- Ensure domain points to EC2 IP
- Check DNS: `dig +short hitmanjacktravel.com`
- Verify port 80 is accessible
- Re-run: `./setup-ssl.sh`

---

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Review this documentation
3. Check GitHub Issues
4. Contact: your-email@example.com

---

## 🎉 Success!

Your AI Travel App is now:
- ✅ Deployed on AWS EC2
- ✅ Using RDS PostgreSQL
- ✅ Running in Docker containers
- ✅ Auto-deploying via GitHub Actions
- ✅ Secured with HTTPS (if SSL setup completed)
- ✅ Production-ready!

---

**Generated**: January 2026
**Version**: 1.0.0
