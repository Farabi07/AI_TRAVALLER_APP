#!/bin/bash
# SSL Setup Script for hitmanjacktravel.com and api.hitmanjacktravel.com

set -e

echo "=================================================="
echo "SSL Certificate Setup for Travel App"
echo "=================================================="

cd ~/AI-Travel-App

echo ""
echo "Step 1: Updating .env file with domain configuration..."
echo "Add these domains to your .env ALLOWED_HOSTS:"
echo "ALLOWED_HOSTS=hitmanjacktravel.com,www.hitmanjacktravel.com,api.hitmanjacktravel.com,3.66.7.106,localhost,127.0.0.1"
echo ""
read -p "Press Enter after updating .env file..."

echo ""
echo "Step 2: Stopping nginx container..."
docker-compose -f docker-compose.prod.yml stop nginx

echo ""
echo "Step 3: Obtaining SSL certificate for main domain (hitmanjacktravel.com)..."
sudo certbot certonly --standalone \
  -d hitmanjacktravel.com \
  -d www.hitmanjacktravel.com \
  --email farhadkabir1212@gmail.com \
  --agree-tos \
  --non-interactive

echo ""
echo "Step 4: Obtaining SSL certificate for API subdomain (api.hitmanjacktravel.com)..."
sudo certbot certonly --standalone \
  -d api.hitmanjacktravel.com \
  --email farhadkabir1212@gmail.com \
  --agree-tos \
  --non-interactive

echo ""
echo "Step 5: Copying certificates to project directory..."
sudo cp -r /etc/letsencrypt certbot/conf/

echo ""
echo "Step 6: Setting correct permissions..."
sudo chown -R $USER:$USER certbot/

echo ""
echo "Step 7: Updating nginx configuration..."
cp nginx-domain-ssl.conf nginx-ip-only.conf
docker-compose -f docker-compose.prod.yml down

echo ""
echo "Step 8: Starting all services with SSL..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "Step 9: Waiting for services to start..."
sleep 10

echo ""
echo "=================================================="
echo "✅ SSL Setup Complete!"
echo "=================================================="
echo ""
echo "Testing HTTPS access..."
echo ""

curl -I https://hitmanjacktravel.com || echo "⚠️  Main domain not responding yet"
echo ""
curl -I https://www.hitmanjacktravel.com || echo "⚠️  WWW subdomain not responding yet"
echo ""
curl -I https://api.hitmanjacktravel.com || echo "⚠️  API subdomain not responding yet"

echo ""
echo "=================================================="
echo "Next Steps:"
echo "=================================================="
echo "1. Test your API: https://api.hitmanjacktravel.com/user/api/v1/login/"
echo "2. Check SSL grade: https://www.ssllabs.com/ssltest/analyze.html?d=api.hitmanjacktravel.com"
echo "3. Update Google OAuth redirect URI to: https://api.hitmanjacktravel.com/accounts/google/login/callback/"
echo "4. Certificates will auto-renew via certbot service in docker-compose"
echo "=================================================="
