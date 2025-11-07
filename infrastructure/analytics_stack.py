"""
AWS CDK Stack for Analytics Dashboard Infrastructure

This stack provisions:
- VPC with public and private subnets
- RDS PostgreSQL instance in private subnet
- S3 bucket for CloudFront logs (if needed)
- Secrets Manager for database credentials
- Security groups and IAM roles
- Lambda layer for log processing dependencies (optional)
"""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
)
from constructs import Construct


class AnalyticsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ==========================================
        # VPC Configuration
        # ==========================================
        vpc = ec2.Vpc(
            self,
            "AnalyticsVPC",
            max_azs=2,  # Deploy across 2 availability zones for high availability
            nat_gateways=1,  # Use 1 NAT gateway to reduce costs (production would use 2+)
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # ==========================================
        # Security Groups
        # ==========================================

        # Security group for RDS PostgreSQL
        db_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for PostgreSQL RDS instance",
            allow_all_outbound=False,
        )

        # Security group for Lambda functions (if processing logs)
        lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True,
        )

        # Allow Lambda to connect to RDS
        db_security_group.add_ingress_rule(
            peer=lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda functions to connect to PostgreSQL",
        )

        # Allow connections from your local machine (optional - for development)
        # You can add your IP here or use Systems Manager Session Manager for secure access
        # Uncomment and set your IP range if needed:
        # db_security_group.add_ingress_rule(
        #     peer=ec2.Peer.ipv4("YOUR_IP/32"),
        #     connection=ec2.Port.tcp(5432),
        #     description="Allow connections from development machine",
        # )

        # ==========================================
        # RDS PostgreSQL Database
        # ==========================================

        # Create secret for database credentials
        db_credentials = secretsmanager.Secret(
            self,
            "DBCredentials",
            description="PostgreSQL database credentials for analytics dashboard",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "analytics_admin"}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=32,
            ),
        )

        # RDS PostgreSQL instance
        database = rds.DatabaseInstance(
            self,
            "AnalyticsDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO,  # db.t3.micro for cost efficiency
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[db_security_group],
            credentials=rds.Credentials.from_secret(db_credentials),
            database_name="analytics",
            allocated_storage=20,  # GB
            max_allocated_storage=100,  # Enable storage autoscaling up to 100GB
            storage_encrypted=True,
            backup_retention=Duration.days(7),
            deletion_protection=False,  # Set to True in production
            removal_policy=RemovalPolicy.DESTROY,  # Set to RETAIN in production
            multi_az=False,  # Set to True for production high availability
            publicly_accessible=False,  # Keep database private
            cloudwatch_logs_exports=["postgresql"],  # Enable CloudWatch logs
            enable_performance_insights=True,
            performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT,
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self,
                "ParameterGroup",
                "default.postgres15",
            ),
        )

        # ==========================================
        # S3 Bucket for CloudFront Logs
        # ==========================================

        logs_bucket = s3.Bucket(
            self,
            "CloudFrontLogsBucket",
            bucket_name=None,  # Let CDK generate a unique name
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=RemovalPolicy.DESTROY,  # Set to RETAIN in production
            auto_delete_objects=True,  # Set to False in production
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldLogs",
                    enabled=True,
                    expiration=Duration.days(90),  # Delete logs after 90 days
                ),
                s3.LifecycleRule(
                    id="TransitionToIA",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        )
                    ],
                ),
            ],
        )

        # Grant CloudFront permission to write logs to the bucket
        logs_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:PutObject"],
                resources=[logs_bucket.arn_for_objects("*")],
            )
        )

        # ==========================================
        # IAM Role for Lambda Log Processor
        # ==========================================

        lambda_role = iam.Role(
            self,
            "LogProcessorLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role for Lambda function that processes CloudFront logs",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )

        # Grant Lambda access to read from logs bucket
        logs_bucket.grant_read(lambda_role)

        # Grant Lambda access to read database credentials
        db_credentials.grant_read(lambda_role)

        # ==========================================
        # Outputs
        # ==========================================

        CfnOutput(
            self,
            "VPCId",
            value=vpc.vpc_id,
            description="VPC ID",
            export_name="AnalyticsVPCId",
        )

        CfnOutput(
            self,
            "DatabaseEndpoint",
            value=database.db_instance_endpoint_address,
            description="RDS PostgreSQL endpoint",
            export_name="AnalyticsDatabaseEndpoint",
        )

        CfnOutput(
            self,
            "DatabasePort",
            value=str(database.db_instance_endpoint_port),
            description="RDS PostgreSQL port",
            export_name="AnalyticsDatabasePort",
        )

        CfnOutput(
            self,
            "DatabaseName",
            value="analytics",
            description="Database name",
            export_name="AnalyticsDatabaseName",
        )

        CfnOutput(
            self,
            "DatabaseSecretArn",
            value=db_credentials.secret_arn,
            description="ARN of the secret containing database credentials",
            export_name="AnalyticsDatabaseSecretArn",
        )

        CfnOutput(
            self,
            "LogsBucketName",
            value=logs_bucket.bucket_name,
            description="S3 bucket for CloudFront access logs",
            export_name="AnalyticsLogsBucketName",
        )

        CfnOutput(
            self,
            "LambdaRoleArn",
            value=lambda_role.role_arn,
            description="IAM role ARN for Lambda log processor",
            export_name="AnalyticsLambdaRoleArn",
        )

        CfnOutput(
            self,
            "LambdaSecurityGroupId",
            value=lambda_security_group.security_group_id,
            description="Security group ID for Lambda functions",
            export_name="AnalyticsLambdaSecurityGroupId",
        )

        # Store references for potential future use
        self.vpc = vpc
        self.database = database
        self.logs_bucket = logs_bucket
        self.db_security_group = db_security_group
        self.lambda_security_group = lambda_security_group
        self.lambda_role = lambda_role
