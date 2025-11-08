# Analytics Dashboard - AWS CDK Infrastructure

This directory contains the AWS Cloud Development Kit (CDK) infrastructure code for the Analytics Dashboard.

## Infrastructure Components

The CDK stack provisions:

- **VPC**: Multi-AZ VPC with public, private, and isolated subnets
- **RDS PostgreSQL**: Database instance (db.t3.micro) in isolated subnet
- **S3 Bucket**: For storing CloudFront access logs
- **Secrets Manager**: Secure storage for database credentials
- **Security Groups**: Network access control for RDS and Lambda
- **IAM Roles**: Permissions for Lambda log processor

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
   ```bash
   aws configure
   ```

2. **AWS CDK** installed globally
   ```bash
   npm install -g aws-cdk
   ```

3. **Python 3.11+** with pip

## Setup

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies with UV**:
   ```bash
   cd infrastructure
   uv sync
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Bootstrap CDK** (first time only per AWS account/region):
   ```bash
   cdk bootstrap
   ```

## Deployment

1. **Synthesize CloudFormation template** (optional, to preview):
   ```bash
   cdk synth
   ```

2. **Deploy the stack**:
   ```bash
   cdk deploy
   ```

3. **View outputs** (database endpoint, bucket name, etc.):
   The deploy command will output important values. Save these for your application configuration.

## Accessing Database Credentials

The database credentials are stored in AWS Secrets Manager. To retrieve them:

```bash
aws secretsmanager get-secret-value \
  --secret-id <secret-arn-from-output> \
  --query SecretString \
  --output text
```

## Connecting to RDS from Local Machine

The RDS instance is in a private subnet by default. To connect from your local machine:

### Option 1: SSH Tunnel via EC2 Bastion (Recommended)
1. Launch a small EC2 instance in the public subnet
2. Create SSH tunnel:
   ```bash
   ssh -i your-key.pem -L 5432:rds-endpoint:5432 ec2-user@bastion-ip
   ```
3. Connect to `localhost:5432`

### Option 2: Enable Public Access (Development Only)
Modify the stack to set `publicly_accessible=True` and update security group to allow your IP.

**⚠️ Warning**: Never expose production databases publicly.

### Option 3: AWS Systems Manager Session Manager
Use Session Manager for secure access without SSH keys or public IPs.

## Cost Estimates

Monthly costs (approximate, us-east-1):
- RDS db.t3.micro (single-AZ): ~$15
- NAT Gateway: ~$32
- S3 storage (100GB logs): ~$2.30
- VPC/networking: ~$0
- **Total**: ~$50/month

### Cost Optimization Tips
- Use local PostgreSQL for development (see docker-compose.yml)
- Stop RDS instance when not in use (can be automated with Lambda)
- Use db.t3.micro for development, scale up for production
- Consider Aurora Serverless v2 for variable workloads

## Updating Infrastructure

After making changes to the stack:

```bash
cdk diff  # Preview changes
cdk deploy  # Apply changes
```

## Destroying Infrastructure

**⚠️ Warning**: This will delete all resources including the database.

```bash
cdk destroy
```

## Outputs Reference

After deployment, you'll receive outputs like:

```
AnalyticsDashboardStack.DatabaseEndpoint = analytics-db.xxxxx.us-east-1.rds.amazonaws.com
AnalyticsDashboardStack.DatabasePort = 5432
AnalyticsDashboardStack.DatabaseName = analytics
AnalyticsDashboardStack.DatabaseSecretArn = arn:aws:secretsmanager:...
AnalyticsDashboardStack.LogsBucketName = analyticsdashboardstack-cloudfront...
```

Use these values in your `.env` file for application configuration.

## Security Considerations

- Database is in private/isolated subnet (no internet access)
- Credentials stored in Secrets Manager (encrypted)
- Security groups restrict access to specific sources
- All S3 buckets have public access blocked
- IAM roles follow principle of least privilege

## Next Steps

After infrastructure is deployed:

1. Retrieve database credentials from Secrets Manager
2. Update `.env` file with RDS endpoint and credentials
3. Run database migrations to create tables
4. Configure CloudFront distributions to log to the S3 bucket
5. Deploy Lambda function for log processing (Phase 2)
