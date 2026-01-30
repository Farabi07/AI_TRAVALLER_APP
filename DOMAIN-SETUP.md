# Domain Setup Guide for hitmanjacktravel.com

## Prerequisites
- ✅ AWS Elastic IP assigned to your EC2 instance
- ✅ GoDaddy domain: hitmanjacktravel.com
- ✅ SSH access to EC2

## Step 1: Configure GoDaddy DNS (Do this FIRST)

1. Log in to [GoDaddy Domain Manager](https://dcc.godaddy.com/domains)
2. Click on your domain **hitmanjacktravel.com**
3. Go to **DNS** tab
4. Add/Update these records:

```
Type    Name    Value                      TTL
A       @       YOUR_ELASTIC_IP            600 seconds
A       www     YOUR_ELASTIC_IP            600 seconds
```

Replace `YOUR_ELASTIC_IP` with your actual Elastic IP address.

5. **Wait 5-30 minutes** for DNS propagation

## Step 2: Verify DNS Propagation

Check if your domain points to your Elastic IP:

```bash
# Check DNS
dig +short hitmanjacktravel.com
dig +short www.hitmanjacktravel.com

# Or use online tool
# https://dnschecker.org/#A/hitmanjacktravel.com
```

Both should return your Elastic IP address.

## Step 3: Update Configuration on EC2

SSH to your EC2 and update the `.env` file:

```bash
ssh -i ~/path/to/your-key.pem ubuntu@YOUR_ELASTIC_IP
cd ~/AI-Travel-App

# Edit .env file
nano .env
```

Update these lines:
```env
ALLOWED_HOSTS=hitmanjacktravel.com,www.hitmanjacktravel.com,YOUR_ELASTIC_IP
GOOGLE_CALLBACK_URL=https://hitmanjacktravel.com/accounts/google/login/callback/
DEFAULT_FROM_EMAIL=noreply@hitmanjacktravel.com
```

## Step 4: Deploy Updated Configuration

```bash
cd ~/AI-Travel-App

# Pull latest code with domain configuration
git pull origin main

# Stop containers
docker-compose -f docker-compose.prod.yml down

# Start with new domain config (without SSL first)
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

## Step 5: Test HTTP Access

```bash
curl -I http://hitmanjacktravel.com
curl -I http://www.hitmanjacktravel.com
```

Both should return `HTTP/1.1 301` (redirect) or `HTTP/1.1 200 OK`

## Step 6: Set Up SSL Certificate

Once DNS is propagated and HTTP works:

```bash
cd ~/AI-Travel-App

# Stop nginx
docker-compose -f docker-compose.prod.yml stop nginx

# Get SSL certificate
docker run -it --rm \
    -v $(pwd)/certbot/conf:/etc/letsencrypt \
    -v $(pwd)/certbot/www:/var/www/certbot \
    -p 80:80 \
    certbot/certbot certonly \
    --standalone \
    --email farhadkabir1212@gmail.com \
    --agree-tos \
    --no-eff-email \
    -d hitmanjacktravel.com \
    -d www.hitmanjacktravel.com

# Start all services with SSL
docker-compose -f docker-compose.prod.yml up -d

# Verify SSL
curl -I https://hitmanjacktravel.com
```

## Step 7: Update Google OAuth Callback

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Go to **APIs & Services** → **Credentials**
4. Edit your OAuth 2.0 Client ID
5. Add to **Authorized redirect URIs**:
   ```
   https://hitmanjacktravel.com/accounts/google/login/callback/
   ```

## Troubleshooting

### DNS not propagating
- Wait 5-30 minutes after updating GoDaddy DNS
- Check with: `dig +short hitmanjacktravel.com @8.8.8.8`
- Use https://dnschecker.org to verify globally

### SSL certificate fails
- Make sure DNS is fully propagated first
- Ensure port 80 is accessible from internet
- Check EC2 security group allows port 80 and 443

### 502 Bad Gateway
```bash
# Check backend is running
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs backend
```

### Static files not loading
```bash
# Recollect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

## Important Notes

- 🔒 SSL certificates auto-renew every 60 days via certbot container
- 🌐 Always use HTTPS after SSL is set up
- 📧 Update email settings in Django admin after deployment
- 🔑 Keep your `.env` file secure - never commit it to git

## Your URLs After Setup

- 🌐 **Website**: https://hitmanjacktravel.com
- 🌐 **WWW**: https://www.hitmanjacktravel.com (redirects to main)
- 🔧 **Admin**: https://hitmanjacktravel.com/admin/
- 📚 **API Docs**: https://hitmanjacktravel.com/api/schema/swagger-ui/
