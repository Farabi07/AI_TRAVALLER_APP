#!/bin/bash

# AWS EC2 Instance Setup Script
# This script creates an EC2 instance and configures it for Docker deployment

set -e

# Configuration
AWS_REGION="us-east-1"
INSTANCE_TYPE="t2.medium"  # Recommended: t2.medium for production, t2.micro for testing
KEY_NAME="ai-travel-key"
INSTANCE_NAME="ai-travel-app"
AMI_ID="ami-0e86e20dae9224db8"  # Ubuntu 22.04 LTS (us-east-1)

echo "╔════════════════════════════════════════════════╗"
echo "║   AWS EC2 Instance Setup Script               ║"
echo "║   AI Travel App Server                         ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"
echo ""

# Create key pair if it doesn't exist
echo "🔑 Setting up SSH key pair..."
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $AWS_REGION &> /dev/null; then
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text \
        --region $AWS_REGION > ~/.ssh/$KEY_NAME.pem
    
    chmod 400 ~/.ssh/$KEY_NAME.pem
    echo "✅ Created new key pair: ~/.ssh/$KEY_NAME.pem"
else
    echo "ℹ️  Key pair already exists: $KEY_NAME"
fi

echo ""

# Get default VPC
echo "🔍 Finding default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo "Creating default VPC..."
    VPC_ID=$(aws ec2 create-default-vpc --query 'Vpc.VpcId' --output text --region $AWS_REGION)
fi

echo "✅ Using VPC: $VPC_ID"
echo ""

# Create security group
echo "🔒 Creating security group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name ai-travel-ec2-sg \
    --description "Security group for AI Travel EC2" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=ai-travel-ec2-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $AWS_REGION)

echo "✅ Security Group: $SG_ID"
echo ""

# Configure security group rules
echo "🔓 Configuring security group rules..."

# SSH
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "   SSH rule exists"

# HTTP
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "   HTTP rule exists"

# HTTPS
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "   HTTPS rule exists"

# Port 8000 for testing
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "   Port 8000 rule exists"

echo ""

# User data script to install Docker
USER_DATA=$(cat << 'USERDATA'
#!/bin/bash
apt-get update
apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install additional tools
apt-get install -y git curl wget nano htop

# Create app directory
mkdir -p /home/ubuntu/AI-Travel-App
chown ubuntu:ubuntu /home/ubuntu/AI-Travel-App

# Enable Docker service
systemctl enable docker
systemctl start docker

echo "✅ EC2 instance setup completed" > /home/ubuntu/setup-complete.txt
USERDATA
)

# Launch EC2 instance
echo "🚀 Launching EC2 instance..."
echo "   Type: $INSTANCE_TYPE"
echo "   AMI: $AMI_ID (Ubuntu 22.04)"
echo ""

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --user-data "$USER_DATA" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":30,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --region $AWS_REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Instance created: $INSTANCE_ID"
echo ""

echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

echo "⏳ Waiting for instance status checks..."
aws ec2 wait instance-status-ok --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
EC2_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $AWS_REGION)

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          ✅ EC2 Instance Created Successfully!                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Instance Information:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Instance ID:   $INSTANCE_ID"
echo "  Public IP:     $EC2_IP"
echo "  Instance Type: $INSTANCE_TYPE"
echo "  Region:        $AWS_REGION"
echo "  SSH Key:       ~/.ssh/$KEY_NAME.pem"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔐 Connect to your instance:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ssh -i ~/.ssh/$KEY_NAME.pem ubuntu@$EC2_IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo "  1. Wait 2-3 minutes for user data script to complete"
echo "  2. SSH into the instance"
echo "  3. Verify Docker: docker --version"
echo "  4. Clone your repository or use CI/CD"
echo "  5. Create .env file with your configuration"
echo "  6. Run: docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "💰 Estimated monthly cost:"
echo "  t2.micro:  ~$8/month (Free tier: 750 hours/month for 12 months)"
echo "  t2.medium: ~$34/month"
echo ""
echo "⚠️  Add this IP to ALLOWED_HOSTS in your .env:"
echo "ALLOWED_HOSTS=$EC2_IP,your-domain.com"
echo ""
