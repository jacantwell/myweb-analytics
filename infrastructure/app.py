#!/usr/bin/env python3
"""
AWS CDK Application Entry Point for Analytics Dashboard Infrastructure
"""
import os
from aws_cdk import App, Environment
from analytics_stack import AnalyticsStack

# Get environment from context or use defaults
app = App()

# Get AWS account and region from environment or CDK context
env = Environment(
    account=os.environ.get('CDK_DEFAULT_ACCOUNT'),
    region=os.environ.get('CDK_DEFAULT_REGION', 'eu-west-1')
)

# Create the analytics stack
AnalyticsStack(
    app,
    "AnalyticsDashboardStack",
    env=env,
    description="Infrastructure for CloudFront Analytics Dashboard with PostgreSQL RDS"
)

app.synth()
