#!/bin/bash

# AWS RDS PostgreSQL Setup Script
# This script creates an RDS PostgreSQL instance for the AI Travel App

set -e

# Configuration
AWS_REGION="us-east-1"
DB_INSTANCE_ID="ai-travel-db"
DB_NAME="ai_travel_db"
DB_USERNAME="postgres"
DB_PASSWORD="ChangeThisSecurePassword123!"  # ⚠️ CHANGE THIS BEFORE RUNNING
DB_INSTANCE_CLASS="db.t3.micro"  # Free tier eligible
ALLOCATED_STORAGE=20
ENGINE_VERSION="17.2"

echo "╔════════════════════════════════════════════════╗"
echo "║   AWS RDS PostgreSQL Setup Script             ║"
echo "║   AI Travel App Database                       ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    echo "Run: curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip' && unzip awscliv2.zip && sudo ./aws/install"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"
echo ""

# Get default VPC
echo "🔍 Finding default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo "❌ No default VPC found. Creating one..."
    VPC_ID=$(aws ec2 create-default-vpc --query 'Vpc.VpcId' --output text --region $AWS_REGION)
fi

echo "✅ Using VPC: $VPC_ID"
echo ""

# Get subnets
echo "🔍 Finding subnets..."
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region $AWS_REGION | tr '\t' ' ')

if [ -z "$SUBNET_IDS" ]; then
    echo "❌ No subnets found in VPC"
    exit 1
fi

echo "✅ Found subnets: $SUBNET_IDS"
echo ""

# Create DB subnet group
echo "📦 Creating DB subnet group..."
aws rds create-db-subnet-group \
    --db-subnet-group-name ai-travel-subnet-group \
    --db-subnet-group-description "Subnet group for AI Travel RDS" \
    --subnet-ids $SUBNET_IDS \
    --region $AWS_REGION 2>/dev/null || echo "ℹ️  Subnet group already exists"

echo ""

# Create security group for RDS
echo "🔒 Creating security group for RDS..."
RDS_SG_ID=$(aws ec2 create-security-group \
    --group-name ai-travel-rds-sg \
    --description "Security group for AI Travel RDS" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=ai-travel-rds-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $AWS_REGION)

echo "✅ Security Group: $RDS_SG_ID"
echo ""

# Allow PostgreSQL access from anywhere (restrict this in production!)
echo "🔓 Configuring security group rules..."
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "ℹ️  Rule already exists"

echo ""

# Create RDS instance
echo "🚀 Creating RDS PostgreSQL instance..."
echo "   Instance: $DB_INSTANCE_ID"
echo "   Class: $DB_INSTANCE_CLASS"
echo "   Engine: PostgreSQL $ENGINE_VERSION"
echo "   Storage: ${ALLOCATED_STORAGE}GB"
echo ""

aws rds create-db-instance \
    --db-instance-identifier $DB_INSTANCE_ID \
    --db-instance-class $DB_INSTANCE_CLASS \
    --engine postgres \
    --engine-version $ENGINE_VERSION \
    --master-username $DB_USERNAME \
    --master-user-password $DB_PASSWORD \
    --allocated-storage $ALLOCATED_STORAGE \
    --db-name $DB_NAME \
    --db-subnet-group-name ai-travel-subnet-group \
    --vpc-security-group-ids $RDS_SG_ID \
    --publicly-accessible \
    --backup-retention-period 7 \
    --storage-encrypted \
    --storage-type gp3 \
    --region $AWS_REGION

echo ""
echo "⏳ Waiting for RDS instance to be available..."
echo "   This usually takes 5-10 minutes. Please wait..."
echo ""

aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region $AWS_REGION

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_ID \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text \
    --region $AWS_REGION)

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           ✅ RDS PostgreSQL Created Successfully!              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Database Information:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Endpoint:    $RDS_ENDPOINT"
echo "  Port:        5432"
echo "  Database:    $DB_NAME"
echo "  Username:    $DB_USERNAME"
echo "  Region:      $AWS_REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔐 Add this to your .env file:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/$DB_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "  1. Change the database password immediately"
echo "  2. Restrict security group to allow only EC2 instance IP"
echo "  3. Store credentials in AWS Secrets Manager"
echo "  4. Enable encryption at rest (already done)"
echo "  5. Set up automated backups (already configured - 7 days retention)"
echo ""
echo "💰 Estimated monthly cost: ~$15 (Free tier: 750 hours/month for 12 months)"
echo ""
