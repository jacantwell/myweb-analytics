# 📊 Web Analytics Dashboard

A SQL-based analytics dashboard using **Streamlit** and **SQLAlchemy** to track and visualize user activity across CloudFront + S3 hosted websites.

## 🎯 Project Overview

This project demonstrates proficiency in:
- **SQL & Database Design**: Normalized PostgreSQL schema with complex queries
- **SQLAlchemy ORM**: Modern SQLAlchemy 2.0 with type hints
- **AWS Infrastructure**: CDK-based infrastructure as code
- **Data Visualization**: Interactive Streamlit dashboard
- **CloudFront Log Processing**: Parse and analyze access logs

### Architecture

```
CloudFront (with logging) → S3 Logs → Log Processor → PostgreSQL → Streamlit Dashboard
```

## ✨ Features

- 📈 Real-time analytics metrics (page views, visitors, sessions)
- 🗺️ Geographic distribution analysis
- 📱 Device and browser analytics
- 🔀 User journey tracking
- 📊 Interactive visualizations with Plotly
- 🏗️ Infrastructure as Code (AWS CDK)
- 🐳 Local development with Docker

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for local PostgreSQL)
- **AWS CLI** (for AWS deployment)
- **Node.js & npm** (for AWS CDK)

### Option 1: Local Development (Recommended for Getting Started)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd myweb-analytics
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and ensure USE_AWS_RDS=false for local development
   ```

4. **Start PostgreSQL with Docker Compose**
   ```bash
   docker-compose up -d
   ```

5. **Initialize the database**
   ```bash
   python scripts/init_database.py
   ```

6. **Test the connection**
   ```bash
   python scripts/test_connection.py
   ```

7. **Run the Streamlit dashboard** (coming in Phase 4)
   ```bash
   streamlit run streamlit_app/Home.py
   ```

### Option 2: AWS Deployment

1. **Install AWS CDK**
   ```bash
   npm install -g aws-cdk
   ```

2. **Configure AWS credentials**
   ```bash
   aws configure
   ```

3. **Deploy infrastructure**
   ```bash
   cd infrastructure
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cdk bootstrap  # First time only
   cdk deploy
   ```

4. **Update .env with RDS endpoint**
   ```bash
   # Copy outputs from CDK deployment
   USE_AWS_RDS=true
   DB_HOST=<rds-endpoint-from-cdk-output>
   DB_SECRET_ARN=<secret-arn-from-cdk-output>
   ```

5. **Initialize the database**
   ```bash
   python scripts/init_database.py
   ```

## 📁 Project Structure

```
myweb-analytics/
├── README.md
├── project-scope.md          # Detailed project requirements
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Local PostgreSQL setup
├── .env.example              # Environment configuration template
│
├── infrastructure/           # AWS CDK Infrastructure as Code
│   ├── app.py               # CDK app entry point
│   ├── analytics_stack.py   # Main stack (VPC, RDS, S3)
│   ├── cdk.json             # CDK configuration
│   └── README.md            # Infrastructure documentation
│
├── database/                 # Database layer
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy ORM models
│   ├── connection.py        # Database connection management
│   └── queries.py           # Complex analytical queries (coming)
│
├── log_processor/           # CloudFront log processing (Phase 2)
│   ├── parser.py            # Log file parser
│   ├── enrichment.py        # User-agent & GeoIP enrichment
│   └── loader.py            # Batch loading to database
│
├── streamlit_app/           # Streamlit dashboard (Phase 4)
│   ├── Home.py              # Main dashboard
│   ├── config.py            # Dashboard configuration
│   └── pages/               # Multi-page app sections
│
├── scripts/                 # Utility scripts
│   ├── init_database.py     # Initialize database tables
│   ├── test_connection.py   # Test database connection
│   └── generate_sample_logs.py  # Generate test data (coming)
│
├── tests/                   # Unit tests (coming)
└── docs/                    # Additional documentation
```

## 🗃️ Database Schema

### Core Tables

#### `page_views`
Primary analytics table storing each HTTP request with:
- Request details (URL, method, status)
- User agent data (browser, OS, device type)
- Geographic information
- CloudFront edge metrics

#### `sessions`
Aggregated session data:
- Session duration and page view count
- Landing and exit pages
- Device and location attributes

#### `visitors`
Unique visitor tracking:
- First and last seen timestamps
- Lifetime page views and visits

#### `daily_metrics`
Pre-aggregated daily statistics for performance:
- Total page views and unique visitors
- Average session duration
- Bounce rate

#### `url_metadata`
Optional page metadata:
- Page titles and categories
- Active/inactive status

## 🛠️ Technology Stack

### Backend
- **Python 3.11+**
- **SQLAlchemy 2.0** - ORM with modern type hints
- **PostgreSQL 15** - Relational database
- **Boto3** - AWS SDK

### Frontend
- **Streamlit** - Dashboard framework
- **Plotly** - Interactive visualizations
- **Pandas** - Data manipulation

### Infrastructure
- **AWS CDK** - Infrastructure as Code
- **Docker** - Local development environment
- **AWS RDS** - Managed PostgreSQL
- **AWS S3** - CloudFront log storage

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Environment
ENVIRONMENT=local              # local, development, production
USE_AWS_RDS=false             # Use AWS RDS or local PostgreSQL

# Database (Local)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=analytics
DB_USER=analytics_admin
DB_PASSWORD=local_dev_password

# Database (AWS)
# DB_HOST=your-rds-endpoint.rds.amazonaws.com
# DB_SECRET_ARN=arn:aws:secretsmanager:...

# CloudFront Logs
CLOUDFRONT_LOGS_BUCKET=your-logs-bucket
CLOUDFRONT_LOGS_PREFIX=cloudfront-logs/

# Session Detection
SESSION_TIMEOUT_MINUTES=30
```

See `.env.example` for complete configuration options.

## 📊 Example SQL Queries

The project showcases advanced SQL techniques:

### Daily Active Users
```sql
SELECT
    DATE(timestamp) as date,
    COUNT(DISTINCT visitor_id) as unique_visitors
FROM page_views
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date;
```

### User Journey Analysis (Window Functions)
```sql
WITH user_paths AS (
    SELECT
        session_id,
        url_path,
        timestamp,
        LAG(url_path) OVER (PARTITION BY session_id ORDER BY timestamp) as previous_page
    FROM page_views
)
SELECT previous_page, url_path, COUNT(*) as transitions
FROM user_paths
WHERE previous_page IS NOT NULL
GROUP BY previous_page, url_path
ORDER BY transitions DESC;
```

See `project-scope.md` for 15+ additional complex queries.

## 🚦 Development Roadmap

### ✅ Phase 1: Infrastructure & Database Setup (CURRENT)
- [x] Project structure
- [x] AWS CDK infrastructure code
- [x] Docker Compose for local PostgreSQL
- [x] SQLAlchemy models
- [x] Database connection management
- [x] Initialization scripts

### 📋 Phase 2: Log Processing Pipeline
- [ ] CloudFront log parser
- [ ] User-agent parsing
- [ ] GeoIP enrichment
- [ ] Session detection
- [ ] Batch loading to database

### 📋 Phase 3: Complex SQL Queries
- [ ] Analytical query functions
- [ ] Query optimization
- [ ] Performance benchmarking

### 📋 Phase 4: Streamlit Dashboard
- [ ] Multi-page app structure
- [ ] Core metrics dashboard
- [ ] Traffic visualizations
- [ ] Geographic heat maps
- [ ] SQL Query Explorer

### 📋 Phase 5: Testing & Optimization
- [ ] Unit tests
- [ ] Performance optimization
- [ ] Query caching

### 📋 Phase 6: Documentation
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Demo video

## 🧪 Testing

### Test Database Connection
```bash
python scripts/test_connection.py
```

### Run Unit Tests (coming)
```bash
pytest tests/
```

## 📝 Development Commands

### Local PostgreSQL Management
```bash
# Start PostgreSQL
docker-compose up -d

# Stop PostgreSQL
docker-compose down

# View logs
docker-compose logs -f postgres

# Access PostgreSQL CLI
docker-compose exec postgres psql -U analytics_admin -d analytics

# Start with pgAdmin (for GUI management)
docker-compose --profile tools up -d
# Access at http://localhost:5050
```

### Database Management
```bash
# Initialize database (create tables)
python scripts/init_database.py

# Drop and recreate tables (CAUTION!)
python scripts/init_database.py --drop

# Test connection
python scripts/test_connection.py
```

### AWS Infrastructure
```bash
cd infrastructure

# Preview changes
cdk diff

# Deploy infrastructure
cdk deploy

# Destroy infrastructure (CAUTION!)
cdk destroy
```

## 📚 Documentation

- **[project-scope.md](project-scope.md)** - Detailed project requirements and specifications
- **[infrastructure/README.md](infrastructure/README.md)** - AWS CDK infrastructure documentation
- **Database Schema** - See `database/models.py` for full schema with comments

## 🔐 Security Considerations

- ✅ Database in private subnet (AWS deployment)
- ✅ Credentials stored in AWS Secrets Manager
- ✅ IP addresses hashed for privacy
- ✅ All S3 buckets block public access
- ✅ Security groups restrict network access

## 💰 Cost Estimates

### AWS Deployment (approximate monthly costs)
- RDS db.t3.micro: ~$15
- NAT Gateway: ~$32
- S3 storage: ~$2
- **Total: ~$50/month**

### Local Development
- **$0/month** - Everything runs locally

## 🤝 Contributing

This is a portfolio project. Feedback and suggestions are welcome!

## 📄 License

This project is for portfolio and educational purposes.

## 🙋 Questions?

See the detailed [project-scope.md](project-scope.md) for comprehensive documentation on:
- System architecture
- Database design rationale
- SQL query examples
- Dashboard wireframes
- Implementation phases

---

**Current Status**: ✅ Phase 1 Complete - Infrastructure and database foundation ready!

**Next Steps**:
1. Enable CloudFront logging on your websites
2. Begin Phase 2: Log processing pipeline
3. Build analytical SQL queries
