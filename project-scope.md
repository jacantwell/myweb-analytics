# Website Analytics Dashboard - Project Scope

## Executive Summary
Build a SQL-based analytics dashboard using Streamlit to track and visualize user activity across CloudFront + S3 hosted websites, demonstrating SQL and SQLAlchemy proficiency. The dashboard will run locally and connect to a database containing parsed CloudFront access logs.

---

## Current Infrastructure Analysis

### Existing Setup
- **Static websites** hosted on S3 with CloudFront CDN
- **Domains**: Root domain + www subdomain support
- **SSL/TLS**: ACM certificates for HTTPS
- **Routing**: CloudFront Function for Next.js static export routing
- **Access Control**: Origin Access Control (OAC) for secure S3 access

### Critical Gap Identified
⚠️ **No analytics logging currently enabled** - CloudFront access logs and S3 server access logs need to be configured.

---

## Prerequisites: Required CloudFront Configuration

**This analytics application is designed to work with websites that have the following CloudFront setup:**

### Must-Have Configuration
1. **CloudFront Access Logging Enabled**
   - Logs must be delivered to an S3 bucket
   - Standard CloudFront access log format (tab-delimited)
   
2. **Log Bucket Access**
   - Application needs read access to the S3 bucket containing CloudFront logs
   - Logs should be organized with a consistent prefix (e.g., `cloudfront-logs/`)

3. **Log Retention**
   - Sufficient log history for meaningful analytics (recommend 90+ days)
   - Logs should not be encrypted, or encryption keys must be accessible

### CloudFront Logging Configuration Reference

If your CloudFront distribution doesn't have logging enabled, you'll need to add this configuration:

**In CloudFormation (`template-global.yaml`):**
```yaml
CloudFrontDistribution:
  Properties:
    DistributionConfig:
      Logging:
        Bucket: your-logging-bucket.s3.amazonaws.com
        IncludeCookies: false
        Prefix: cloudfront-logs/
```

**Or via AWS Console:**
- Navigate to CloudFront → Your Distribution → Edit
- Under "Logging", toggle "On"
- Select S3 bucket for logs
- Set log prefix (optional)

**Or via AWS CLI:**
```bash
aws cloudfront update-distribution \
  --id YOUR_DISTRIBUTION_ID \
  --distribution-config file://distribution-config.json
```

### Recommended S3 Logging Bucket Setup
```yaml
LoggingBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: your-domain-logs
    AccessControl: LogDeliveryWrite
    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true
    LifecycleConfiguration:
      Rules:
        - Id: DeleteOldLogs
          Status: Enabled
          ExpirationInDays: 90
```

### Verification Steps
Before starting this project, verify:
- [ ] CloudFront logging is enabled
- [ ] Logs are being delivered to S3 (check for recent .gz files)
- [ ] You have AWS credentials with S3 read access to the log bucket
- [ ] Log files follow standard CloudFront access log format

**Note:** It typically takes 5-10 minutes after enabling logging for the first logs to appear in S3.

---

## Project Objectives

### Primary Goals
1. **Capture user analytics** from CloudFront distributions
2. **Store structured data** in a relational database using SQLAlchemy ORM
3. **Build a dashboard** to visualize key metrics
4. **Demonstrate SQL proficiency** through complex queries and data modeling

### Success Criteria
- Real-time or near-real-time analytics data ingestion
- Clean, normalized database schema
- Interactive dashboard with key metrics
- Complex SQL queries showcasing joins, aggregations, window functions

---

## System Architecture

### High-Level Components

```
┌─────────────────┐
│   CloudFront    │
│  (with logging) │
└────────┬────────┘
         │ Logs to S3
         ▼
┌─────────────────┐
│  S3 Log Bucket  │
└────────┬────────┘
         │
         │ Processed by
         ▼
┌─────────────────┐      ┌──────────────┐
│  Log Processor  │─────▶│  PostgreSQL  │
│  (Python/Lambda)│      │   Database   │
└─────────────────┘      └──────┬───────┘
                                 │
                                 │ SQLAlchemy ORM
                                 ▼
                         ┌──────────────┐
                         │   Streamlit  │
                         │   Dashboard  │
                         │ (runs locally)│
                         └──────────────┘
```

### Technology Stack

#### Backend
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL 15+ (RDS or local Docker container)
- **Log Processing**: AWS Lambda + S3 triggers OR Python batch script

#### Frontend/Dashboard
- **Framework**: Streamlit
- **Charting**: Plotly (built-in with Streamlit), Altair
- **Deployment**: Local execution (`streamlit run app.py`)

#### Infrastructure
- **Database Hosting**: AWS RDS (PostgreSQL) or local Docker PostgreSQL
- **Log Processing**: Lambda functions triggered by S3 events OR scheduled batch job
- **Dashboard**: Runs locally, connects remotely to database

---

## Database Schema Design

### Core Tables

#### 1. `page_views`
Primary analytics table storing each request.

```sql
CREATE TABLE page_views (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    visitor_id VARCHAR(255),  -- Hashed IP or cookie-based ID
    session_id VARCHAR(255),
    
    -- Request Details
    url_path VARCHAR(1024) NOT NULL,
    query_string TEXT,
    http_method VARCHAR(10),
    status_code INTEGER,
    
    -- Referrer Information
    referrer_domain VARCHAR(255),
    referrer_path VARCHAR(1024),
    
    -- User Agent Parsing
    user_agent TEXT,
    browser VARCHAR(100),
    browser_version VARCHAR(50),
    os VARCHAR(100),
    os_version VARCHAR(50),
    device_type VARCHAR(50),  -- desktop, mobile, tablet, bot
    
    -- Geographic Data
    country_code VARCHAR(2),
    country_name VARCHAR(100),
    region VARCHAR(100),
    city VARCHAR(100),
    
    -- CloudFront Specific
    edge_location VARCHAR(50),
    edge_result_type VARCHAR(50),  -- Hit, Miss, Error
    bytes_sent BIGINT,
    time_taken_ms INTEGER,
    
    -- Indexes
    INDEX idx_timestamp (timestamp),
    INDEX idx_visitor_session (visitor_id, session_id),
    INDEX idx_url_path (url_path),
    INDEX idx_country (country_code),
    INDEX idx_device_type (device_type)
);
```

#### 2. `sessions`
Aggregated session data.

```sql
CREATE TABLE sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    visitor_id VARCHAR(255) NOT NULL,
    
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    
    page_views_count INTEGER DEFAULT 0,
    landing_page VARCHAR(1024),
    exit_page VARCHAR(1024),
    
    device_type VARCHAR(50),
    country_code VARCHAR(2),
    
    INDEX idx_visitor (visitor_id),
    INDEX idx_start_time (start_time)
);
```

#### 3. `visitors`
Unique visitor tracking.

```sql
CREATE TABLE visitors (
    id BIGSERIAL PRIMARY KEY,
    visitor_id VARCHAR(255) UNIQUE NOT NULL,
    
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    total_visits INTEGER DEFAULT 1,
    total_page_views INTEGER DEFAULT 0,
    
    INDEX idx_first_seen (first_seen),
    INDEX idx_last_seen (last_seen)
);
```

#### 4. `daily_metrics`
Pre-aggregated daily statistics for performance.

```sql
CREATE TABLE daily_metrics (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    
    total_page_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    avg_session_duration_seconds INTEGER,
    
    bounce_rate DECIMAL(5,2),  -- Percentage
    
    -- Top performing pages (JSON or separate table)
    top_pages JSONB,
    
    UNIQUE(date),
    INDEX idx_date (date)
);
```

#### 5. `url_metadata` (Optional)
Store page titles and metadata.

```sql
CREATE TABLE url_metadata (
    id BIGSERIAL PRIMARY KEY,
    url_path VARCHAR(1024) UNIQUE NOT NULL,
    page_title VARCHAR(255),
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    
    INDEX idx_category (category)
);
```

---

## SQLAlchemy Models Example

```python
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class PageView(Base):
    __tablename__ = 'page_views'
    
    id = Column(BigInteger, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    visitor_id = Column(String(255), index=True)
    session_id = Column(String(255), index=True)
    
    url_path = Column(String(1024), nullable=False, index=True)
    query_string = Column(Text)
    http_method = Column(String(10))
    status_code = Column(Integer)
    
    referrer_domain = Column(String(255))
    referrer_path = Column(String(1024))
    
    user_agent = Column(Text)
    browser = Column(String(100))
    browser_version = Column(String(50))
    os = Column(String(100))
    device_type = Column(String(50), index=True)
    
    country_code = Column(String(2), index=True)
    country_name = Column(String(100))
    city = Column(String(100))
    
    edge_location = Column(String(50))
    edge_result_type = Column(String(50))
    bytes_sent = Column(BigInteger)
    time_taken_ms = Column(Integer)
    
    __table_args__ = (
        Index('idx_visitor_session', 'visitor_id', 'session_id'),
    )

class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(BigInteger, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False)
    visitor_id = Column(String(255), nullable=False, index=True)
    
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    
    page_views_count = Column(Integer, default=0)
    landing_page = Column(String(1024))
    exit_page = Column(String(1024))
    
    device_type = Column(String(50))
    country_code = Column(String(2))
```

---

## Key Analytics Queries to Implement

### 1. **Daily Active Users (DAU)**
```sql
SELECT 
    DATE(timestamp) as date,
    COUNT(DISTINCT visitor_id) as unique_visitors
FROM page_views
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY date;
```

### 2. **Top Pages by Views**
```sql
SELECT 
    url_path,
    COUNT(*) as views,
    COUNT(DISTINCT visitor_id) as unique_visitors,
    AVG(time_taken_ms) as avg_load_time
FROM page_views
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY url_path
ORDER BY views DESC
LIMIT 10;
```

### 3. **Traffic Sources**
```sql
SELECT 
    CASE 
        WHEN referrer_domain IS NULL THEN 'Direct'
        WHEN referrer_domain LIKE '%google%' THEN 'Google'
        WHEN referrer_domain LIKE '%facebook%' THEN 'Facebook'
        ELSE referrer_domain
    END as source,
    COUNT(*) as visits,
    COUNT(DISTINCT visitor_id) as unique_visitors
FROM page_views
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY source
ORDER BY visits DESC;
```

### 4. **User Journey Analysis (Path Analysis)**
```sql
WITH user_paths AS (
    SELECT 
        session_id,
        url_path,
        timestamp,
        LAG(url_path) OVER (PARTITION BY session_id ORDER BY timestamp) as previous_page,
        LEAD(url_path) OVER (PARTITION BY session_id ORDER BY timestamp) as next_page
    FROM page_views
    WHERE timestamp >= NOW() - INTERVAL '7 days'
)
SELECT 
    previous_page,
    url_path as current_page,
    next_page,
    COUNT(*) as frequency
FROM user_paths
WHERE previous_page IS NOT NULL
GROUP BY previous_page, url_path, next_page
ORDER BY frequency DESC
LIMIT 20;
```

### 5. **Cohort Analysis**
```sql
SELECT 
    DATE_TRUNC('week', first_seen) as cohort_week,
    DATE_TRUNC('week', last_seen) as activity_week,
    COUNT(DISTINCT visitor_id) as returning_visitors
FROM visitors
WHERE first_seen >= NOW() - INTERVAL '90 days'
GROUP BY cohort_week, activity_week
ORDER BY cohort_week, activity_week;
```

### 6. **Geographic Distribution**
```sql
SELECT 
    country_name,
    COUNT(*) as total_views,
    COUNT(DISTINCT visitor_id) as unique_visitors,
    AVG(time_taken_ms) as avg_load_time
FROM page_views
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY country_name
ORDER BY total_views DESC
LIMIT 15;
```

### 7. **Device & Browser Breakdown**
```sql
SELECT 
    device_type,
    browser,
    COUNT(*) as sessions,
    AVG(duration_seconds) as avg_session_duration
FROM sessions
WHERE start_time >= NOW() - INTERVAL '7 days'
GROUP BY device_type, browser
ORDER BY sessions DESC;
```

---

## Dashboard Features (Streamlit)

### Core Metrics Dashboard (Top of Page)
Using `st.metric()` for real-time KPI cards with delta indicators:
- **Today's Visitors**: Unique visitors today vs. yesterday
- **Page Views**: Total views in last 24 hours with % change
- **Active Sessions**: Sessions in last 30 minutes
- **Avg. Session Duration**: Average time on site with trend
- **Bounce Rate**: Single-page sessions percentage

### Visualizations & Components

#### 1. **Traffic Timeline** (`st.line_chart` or `st.plotly_chart`)
- Line chart showing page views and unique visitors over time
- Date range selector using `st.date_input` or `st.slider`
- Time granularity selector: hourly, daily, weekly, monthly

#### 2. **Top Pages Table** (`st.dataframe`)
- Interactive sortable table with URL, views, unique visitors, avg. time
- Built-in filtering and sorting
- Click-to-drill-down functionality using Streamlit sessions

#### 3. **Geographic Heat Map** (`st.plotly_chart` with Plotly choropleth)
- World map colored by visitor density
- Hover details showing country-specific metrics
- Side table with top countries

#### 4. **Traffic Sources** (`st.plotly_chart` pie/donut chart)
- Distribution of direct, search, social, referral traffic
- Interactive legend for filtering

#### 5. **Device & Browser Distribution** (`st.bar_chart` or Plotly)
- Stacked bar chart comparing desktop, mobile, tablet usage
- Browser breakdown by device type

#### 6. **User Journey Flow** (`st.plotly_chart` Sankey diagram)
- Visual flow of user paths through the site
- Configurable depth (2-5 page sequences)

#### 7. **Recent Activity Feed** (`st.dataframe` with auto-refresh)
- Live-updating table of recent page views
- Auto-refresh using `st.experimental_rerun()` with timer
- Filterable by country, device, page

### Multi-Page Streamlit App Structure

```
📁 streamlit_app/
├── 🏠 Home.py                 # Overview dashboard
├── pages/
│   ├── 1_📊_Traffic_Analysis.py
│   ├── 2_🗺️_Geographic_Insights.py
│   ├── 3_📱_Device_Analytics.py
│   ├── 4_🔀_User_Journeys.py
│   ├── 5_📈_Cohort_Analysis.py
│   └── 6_🔍_SQL_Query_Explorer.py  # Show raw SQL + results
```

### Streamlit-Specific Features

**Sidebar Navigation:**
- Date range picker
- Metric selection (views, visitors, sessions)
- Country/device filters
- Refresh interval setting

**Caching Strategy:**
```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_daily_metrics(start_date, end_date):
    # Expensive SQL query
    return results
```

**State Management:**
```python
if 'selected_page' not in st.session_state:
    st.session_state.selected_page = None
```

**SQL Query Explorer Page:**
- Show the actual SQL queries used for each visualization
- Explain query optimization techniques
- Display query execution plans
- Allow custom SQL query execution (for demo purposes)

---

## Implementation Phases

### Phase 1: Infrastructure & Database Setup (Week 1)
- [ ] Verify CloudFront logging is enabled and accessible
- [ ] Set up development environment (Python 3.11+, virtual environment)
- [ ] Provision PostgreSQL database (RDS or local Docker)
- [ ] Create database schemas and tables
- [ ] Set up SQLAlchemy models and connection pooling

### Phase 2: Log Processing Pipeline (Week 1-2)
- [ ] Build CloudFront log parser (handles .gz compressed files)
- [ ] Implement user-agent parsing (using `user-agents` library)
- [ ] Create visitor ID hashing mechanism (privacy-preserving)
- [ ] Build session detection logic (30-minute timeout)
- [ ] Develop batch processing script or Lambda function
- [ ] Test with sample log data

### Phase 3: SQLAlchemy ORM & Data Layer (Week 2)
- [ ] Define all SQLAlchemy models with relationships
- [ ] Implement database connection pooling
- [ ] Create data access layer (DAL) with query methods
- [ ] Build complex analytical query functions
- [ ] Add data validation and error handling
- [ ] Create helper functions for common aggregations

### Phase 4: Streamlit Dashboard Development (Week 3)
- [ ] Set up Streamlit multi-page app structure
- [ ] Create main overview dashboard (Home.py)
- [ ] Implement core metric cards with delta indicators
- [ ] Build traffic timeline visualization
- [ ] Add top pages interactive table
- [ ] Create geographic heat map
- [ ] Build traffic sources and device distribution charts
- [ ] Implement user journey flow diagram
- [ ] Add SQL Query Explorer page
- [ ] Configure caching strategy for query performance

### Phase 5: Testing & Optimization (Week 4)
- [ ] Load test database queries with realistic data volumes
- [ ] Optimize slow queries with appropriate indexes
- [ ] Implement query result caching in Streamlit
- [ ] Add error handling and user-friendly error messages
- [ ] Test with edge cases (no data, missing values)
- [ ] Profile application performance
- [ ] Add loading spinners and progress indicators

### Phase 6: Documentation & Polish (Week 4)
- [ ] Write comprehensive README with setup instructions
- [ ] Document database schema with ERD diagram
- [ ] Create SQL query library with explanations
- [ ] Add inline code comments and docstrings
- [ ] Create demo video or screenshots
- [ ] Prepare portfolio presentation materials
- [ ] Write blog post or case study (optional)

**Total Timeline: ~4 weeks** (reduced from 6 weeks with original scope)

---

## SQL Proficiency Demonstrations

This project will showcase:

1. **Schema Design**: Normalized database with proper relationships and indexes
2. **Complex Joins**: Multi-table queries combining page views, sessions, and visitors
3. **Window Functions**: LAG/LEAD for user journey, ROW_NUMBER for rankings
4. **Aggregations**: GROUP BY with multiple dimensions, ROLLUP/CUBE for subtotals
5. **CTEs**: Common Table Expressions for readable, modular queries
6. **Subqueries**: Correlated and uncorrelated subqueries
7. **Performance Optimization**: Index strategy, query planning, partitioning
8. **Data Integrity**: Foreign keys, constraints, triggers (if needed)

---

## Technical Considerations

### CloudFront Log Format
CloudFront access logs are tab-delimited with these key fields:
- `date`, `time`, `x-edge-location`, `sc-bytes`, `c-ip`
- `cs-method`, `cs(Host)`, `cs-uri-stem`, `sc-status`
- `cs(Referer)`, `cs(User-Agent)`, `cs-uri-query`
- `x-edge-result-type`, `x-edge-response-result-type`

### Log Processing Challenges
- **Volume**: CloudFront can generate millions of log entries
- **Latency**: Logs delivered to S3 within minutes but not instant
- **Parsing**: Logs require parsing and enrichment (GeoIP, user-agent)
- **Deduplication**: Handle potential duplicate log entries

### Scalability Considerations
- **Database**: Consider partitioning `page_views` by date
- **Batch Processing**: Process logs in batches to reduce database load
- **Caching**: Cache frequent queries (e.g., today's metrics)
- **Archival**: Move old data to separate archive tables or S3

### Privacy & Compliance
- **IP Hashing**: Hash IP addresses to protect user privacy
- **GDPR**: Consider data retention policies and user deletion
- **Cookie Consent**: May need consent mechanism for tracking
- **Anonymization**: Consider anonymizing data after certain period

---

## Estimated Costs (AWS)

### Monthly Estimates (for moderate traffic site: ~100K pageviews/month)

| Service | Usage | Cost |
|---------|-------|------|
| CloudFront | 100K requests, 1GB data transfer | ~$1 |
| S3 (logs) | 1GB storage, PUT/GET requests | ~$1 |
| RDS (db.t3.micro) | PostgreSQL, 20GB storage | ~$15 |
| Lambda | 1M invocations, 128MB, 3s avg | ~$0.50 |
| **Total** | | **~$17-20/month** |

**Cost Savings with Local Development:**
- ✅ No EC2/ECS costs for hosting application
- ✅ No API Gateway costs
- ✅ No CloudFront costs for serving dashboard
- ✅ Can use local PostgreSQL in Docker to eliminate RDS costs (~$0/month)

### Zero-Cost Option for Portfolio Development

For learning/demo purposes without AWS costs:

1. **Local PostgreSQL**: Run in Docker container
2. **Sample Log Files**: Download or generate CloudFront-format logs
3. **Process Logs Locally**: Python script instead of Lambda
4. **Streamlit Dashboard**: Runs on localhost
5. **Demo Data**: Seed with 6 months of synthetic traffic data

**Total Cost: $0/month** - Everything runs locally on your machine.

---

## Local Development Setup (Recommended for Portfolio)

For portfolio demonstration with minimal costs:

### Components
1. **PostgreSQL in Docker**: 
   ```bash
   docker run --name analytics-postgres \
     -e POSTGRES_PASSWORD=yourpassword \
     -e POSTGRES_DB=analytics \
     -p 5432:5432 \
     -d postgres:15
   ```

2. **Sample Log Generator**: Create Python script to generate realistic CloudFront-style logs
   - Simulate various user behaviors (bounces, multi-page sessions)
   - Include realistic user agents, referrers, geo-locations
   - Generate 6-12 months of historical data

3. **Log Processor**: Batch Python script that:
   - Reads sample or real CloudFront logs
   - Parses and enriches data
   - Loads into PostgreSQL using SQLAlchemy

4. **Streamlit Dashboard**: 
   ```bash
   streamlit run Home.py
   ```
   - Connects to local or remote PostgreSQL
   - Auto-reloads on code changes
   - Accessible at `http://localhost:8501`

### Development Workflow
```
1. Generate/download logs → 2. Process with Python → 3. Load to PostgreSQL
                                                           ↓
                                                    4. View in Streamlit
```

### Benefits
- ✅ Zero AWS costs during development
- ✅ Fast iteration cycle
- ✅ Full control over test data
- ✅ Easy to demo (just run Docker + Streamlit)
- ✅ Can migrate to RDS later if needed

---

## Deliverables

### Code Repositories
1. **Log Processor**: Python scripts for parsing CloudFront logs and loading to database
2. **SQLAlchemy Models**: Database models, relationships, and data access layer
3. **Streamlit Dashboard**: Multi-page Streamlit application
4. **Utilities**: Sample log generator, database seed scripts, migration scripts

### Documentation
1. **README**: Project overview, setup instructions, and quickstart guide
2. **Database Schema**: ERD diagram and comprehensive table descriptions
3. **SQL Query Library**: 15+ annotated SQL queries demonstrating various techniques
4. **Streamlit App Guide**: Page-by-page feature documentation
5. **Setup Guide**: Docker commands, environment configuration, troubleshooting

### Portfolio Artifacts
1. **Demo Video/Screenshots**: Walkthrough of dashboard functionality
2. **SQL Showcase Document**: Complex queries with explanations and performance notes
3. **Architecture Diagram**: System component overview
4. **Blog Post/Case Study**: Technical write-up of the project (optional)
5. **Performance Analysis**: Query optimization before/after results

### Repository Structure
```
analytics-dashboard/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── schema.md
│   ├── sql-queries.md
│   └── architecture-diagram.png
├── log_processor/
│   ├── parser.py
│   ├── enrichment.py
│   └── loader.py
├── database/
│   ├── models.py
│   ├── connection.py
│   ├── queries.py
│   └── migrations/
├── streamlit_app/
│   ├── Home.py
│   ├── config.py
│   ├── utils.py
│   └── pages/
│       ├── 1_📊_Traffic_Analysis.py
│       ├── 2_🗺️_Geographic_Insights.py
│       ├── 3_📱_Device_Analytics.py
│       ├── 4_🔀_User_Journeys.py
│       ├── 5_📈_Cohort_Analysis.py
│       └── 6_🔍_SQL_Query_Explorer.py
└── scripts/
    ├── generate_sample_logs.py
    ├── seed_database.py
    └── analyze_performance.py
```

---

## Success Metrics

- ✅ Database handling 1M+ page view records efficiently
- ✅ Dashboard loads in <2 seconds with cached queries
- ✅ Complex queries execute in <500ms (with proper indexing)
- ✅ At least 15 advanced SQL queries demonstrated (joins, window functions, CTEs, subqueries)
- ✅ Clean SQLAlchemy ORM implementation with proper relationships
- ✅ Properly normalized database schema (3NF)
- ✅ Streamlit dashboard with 6+ different visualization types
- ✅ Multi-page Streamlit app with intuitive navigation
- ✅ Caching strategy implemented for optimal performance
- ✅ SQL Query Explorer page showcasing query techniques

---

## Next Steps

1. **Review this scope** and decide: AWS RDS + Lambda OR fully local PostgreSQL + Python scripts
2. **Verify CloudFront logging** is enabled on your existing websites (see Prerequisites section)
3. **Set up development environment**: PostgreSQL (Docker or RDS), Python 3.11+, Streamlit
4. **Start with log parsing** proof-of-concept to understand CloudFront log format
5. **Build database schema** and create SQLAlchemy models

### Quick Start Recommendations

**For Portfolio/Demo Focus:**
- Use fully local setup (PostgreSQL in Docker)
- Generate synthetic log data for faster iteration
- Focus on complex SQL queries and dashboard polish

**For Real Website Analytics:**
- Use AWS RDS for database (can access from anywhere)
- Set up Lambda for automated log processing
- Connect to actual CloudFront logs from your websites

---

## Ready to Build?

Would you like me to help with any specific component, such as:
- ✅ Sample SQLAlchemy models with relationships and complex queries?
- ✅ CloudFront log parsing script with user-agent and GeoIP enrichment?
- ✅ Streamlit dashboard structure and layout examples?
- ✅ Database seeding script to generate realistic test data?
- ✅ Docker Compose configuration for local PostgreSQL setup?
