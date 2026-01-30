#!/bin/bash

# SSL/TLS Setup Script using Let's Encrypt
# Run this AFTER you have pointed your domain to the EC2 IP

set -e

# Configuration
DOMAIN="hitmanjacktravel.com"
EMAIL="farhadkabir1212@gmail.com"
EC2_USER="ubuntu"
EC2_HOST="3.66.7.106"
KEY_PATH="~/.ssh/ai-travel-key.pem"
APP_DIR="/home/ubuntu/AI-Travel-App"

echo "╔════════════════════════════════════════════════╗"
echo "║   SSL/TLS Certificate Setup (Let's Encrypt)   ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Validate inputs
if [ "$EC2_HOST" == "YOUR_ELASTIC_IP" ]; then
    echo "❌ Error: Please update EC2_HOST with your Elastic IP in this script"
    exit 1
fi

echo "📝 Configuration:"
echo "  Domain: $DOMAIN"
echo "  Email:  $EMAIL"
echo "  EC2:    $EC2_HOST"
echo ""

# Check DNS
echo "🔍 Checking DNS configuration..."
RESOLVED_IP=$(dig +short $DOMAIN | tail -n1)

if [ "$RESOLVED_IP" != "$EC2_HOST" ]; then
    echo "⚠️  Warning: Domain $DOMAIN resolves to $RESOLVED_IP, but EC2 is at $EC2_HOST"
    echo "Make sure your domain's A record points to $EC2_HOST"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Update nginx.conf for the domain
echo "📝 Updating nginx configuration..."
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST << EOF
    cd $APP_DIR
    
    # Backup current nginx.conf
    cp nginx.conf nginx.conf.backup
    
    # Update server_name
    sed -i "s/server_name _;/server_name $DOMAIN www.$DOMAIN;/g" nginx.conf
    
    # Update SSL certificate paths
    sed -i "s|ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|g" nginx.conf
    sed -i "s|ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|g" nginx.conf
    
    echo "✅ nginx.conf updated"
EOF

echo ""

# Create temporary HTTP-only nginx config for certbot
echo "🔧 Setting up temporary HTTP configuration for certificate generation..."
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST << 'EOF'
    cd /home/ubuntu/AI-Travel-App
    
    # Create temporary nginx config without SSL
    cat > nginx-temp.conf << 'NGINXCONF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name _;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 "Server ready for SSL setup";
            add_header Content-Type text/plain;
        }
    }
}
NGINXCONF

    echo "✅ Temporary nginx config created"
EOF

echo ""

# Restart with temporary config
echo "🔄 Restarting nginx with temporary configuration..."
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST << EOF
    cd $APP_DIR
    docker-compose -f docker-compose.prod.yml down
    
    # Use temporary config
    mv nginx.conf nginx.conf.ssl
    mv nginx-temp.conf nginx.conf
    
    # Start only nginx and certbot
    docker-compose -f docker-compose.prod.yml up -d nginx certbot
    
    sleep 5
    echo "✅ Nginx started with temporary config"
EOF

echo ""

# Generate certificates
echo "🔐 Generating SSL certificates..."
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST << EOF
    cd $APP_DIR
    
    # Create certbot directories
    mkdir -p certbot/conf certbot/www
    
    # Request certificate
    docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN \
        -d www.$DOMAIN
    
    if [ \$? -eq 0 ]; then
        echo "✅ SSL certificates generated successfully"
    else
        echo "❌ Failed to generate SSL certificates"
        exit 1
    fi
EOF

echo ""

# Restore SSL nginx config
echo "🔄 Activating SSL configuration..."
ssh -i $KEY_PATH $EC2_USER@$EC2_HOST << EOF
    cd $APP_DIR
    
    # Restore SSL config
    mv nginx.conf nginx-temp.conf.backup
    mv nginx.conf.ssl nginx.conf
    
    # Restart all services
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d
    
    sleep 10
    echo "✅ SSL configuration activated"
EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           ✅ SSL/TLS Setup Completed Successfully!             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Your site is now accessible via HTTPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  https://$DOMAIN"
echo "  https://www.$DOMAIN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Certificate Information:"
echo "  - Certificates auto-renew every 60 days"
echo "  - Location: /etc/letsencrypt/live/$DOMAIN/"
echo "  - HTTP traffic automatically redirects to HTTPS"
echo ""
echo "🔒 Security Headers Enabled:"
echo "  - X-Frame-Options: SAMEORIGIN"
echo "  - X-Content-Type-Options: nosniff"
echo "  - X-XSS-Protection: 1; mode=block"
echo ""
