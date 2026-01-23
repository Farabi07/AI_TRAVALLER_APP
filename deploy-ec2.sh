#!/bin/bash

# Manual Deployment Script for EC2
# Use this to deploy manually to your EC2 instance

set -e

# Configuration - UPDATE THESE VALUES
EC2_USER="ubuntu"
EC2_HOST="63.177.70.218"
KEY_PATH="~/.ssh/ai-travel-key.pem"  # ⚠️ UPDATE THIS
APP_DIR="/home/ubuntu/AI-Travel-App"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔════════════════════════════════════════════════╗"
echo "║   AI Travel App - EC2 Deployment Script       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if EC2_HOST is set
if [ "$EC2_HOST" == "YOUR_EC2_PUBLIC_IP" ]; then
    echo -e "${RED}❌ Error: Please update EC2_HOST in this script${NC}"
    echo "Edit this file and set EC2_HOST to your EC2 public IP"
    exit 1
fi

# Check if SSH key exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}❌ Error: SSH key not found at $KEY_PATH${NC}"
    echo "Update KEY_PATH in this script or create the key"
    exit 1
fi

echo -e "${YELLOW}🚀 Deploying to EC2: $EC2_HOST${NC}"
echo ""

# Test SSH connection
echo "🔍 Testing SSH connection..."
if ! ssh -i $KEY_PATH -o ConnectTimeout=5 -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST "echo 'SSH OK'" &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to EC2 instance${NC}"
    echo "Check:"
    echo "  - EC2_HOST is correct"
    echo "  - KEY_PATH is correct"
    echo "  - Security group allows SSH from your IP"
    exit 1
fi

echo -e "${GREEN}✅ SSH connection successful${NC}"
echo ""

# Copy files to EC2
echo "📦 Copying files to EC2..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.env' \
    --exclude 'env' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'staticfiles' \
    --exclude 'media' \
    --exclude 'postgres_data' \
    --exclude '.github' \
    --exclude '*.pem' \
    --exclude 'certbot' \
    -e "ssh -i $KEY_PATH -o StrictHostKeyChecking=no" \
    ./ $EC2_USER@$EC2_HOST:$APP_DIR/

echo -e "${GREEN}✅ Files copied successfully${NC}"
echo ""

# Check if .env exists on EC2
echo "🔍 Checking for .env file on EC2..."
if ! ssh -i $KEY_PATH -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST "[ -f $APP_DIR/.env ]"; then
    echo -e "${YELLOW}⚠️  .env file not found on EC2${NC}"
    echo ""
    echo "Please create .env file on EC2:"
    echo "  1. SSH into EC2: ssh -i $KEY_PATH $EC2_USER@$EC2_HOST"
    echo "  2. cd $APP_DIR"
    echo "  3. nano .env"
    echo "  4. Add your configuration (see .env.example)"
    echo ""
    read -p "Press Enter to continue deployment anyway, or Ctrl+C to cancel..."
else
    echo -e "${GREEN}✅ .env file found${NC}"
fi

echo ""

# Deploy on EC2
echo "🔧 Running deployment commands on EC2..."
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $EC2_USER@$EC2_HOST << EOF
    set -e
    cd $APP_DIR
    
    echo "🐳 Stopping old containers..."
    docker-compose -f docker-compose.prod.yml down || true
    
    echo "🔨 Building new images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    echo "🚀 Starting new containers..."
    docker-compose -f docker-compose.prod.yml up -d
    
    echo "⏳ Waiting for backend to be ready..."
    sleep 15
    
    echo "🗄️  Running migrations..."
    docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput || true
    
    echo "📦 Collecting static files..."
    docker-compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput || true
    
    echo "🧹 Cleaning up old Docker images..."
    docker image prune -af
    
    echo ""
    echo "📊 Current container status:"
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "📝 Recent backend logs:"
    docker-compose -f docker-compose.prod.yml logs --tail=20 backend
EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            ✅ Deployment Completed Successfully!               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Access your application:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  http://$EC2_HOST"
echo "  http://$EC2_HOST/admin"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Useful commands:"
echo "  View logs:    ssh -i $KEY_PATH $EC2_USER@$EC2_HOST 'cd $APP_DIR && docker-compose -f docker-compose.prod.yml logs -f'"
echo "  Restart:      ssh -i $KEY_PATH $EC2_USER@$EC2_HOST 'cd $APP_DIR && docker-compose -f docker-compose.prod.yml restart'"
echo "  Stop:         ssh -i $KEY_PATH $EC2_USER@$EC2_HOST 'cd $APP_DIR && docker-compose -f docker-compose.prod.yml down'"
echo ""
