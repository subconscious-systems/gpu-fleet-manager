# GPU Fleet Manager Database Schema Documentation

This document provides a comprehensive overview of the database schema design for the GPU Fleet Manager project, which implements a multi-tenant architecture for managing GPU resources, jobs, and related entities.

## Table of Contents

1. [Schema Overview](#schema-overview)
2. [Core Multi-Tenant Components](#core-multi-tenant-components)
   - [Users](#users)
   - [Organizations](#organizations)
   - [Organization Members](#organization-members)
   - [Organization Invites](#organization-invites)
   - [API Keys](#api-keys)
   - [Webhooks](#webhooks)
3. [GPU Management Components](#gpu-management-components)
   - [GPU Resources](#gpu-resources)
   - [GPU Metrics](#gpu-metrics)
   - [Jobs](#jobs)
   - [Cost Tracking](#cost-tracking)
4. [Relationships and Constraints](#relationships-and-constraints)
5. [Security and Multi-Tenant Isolation](#security-and-multi-tenant-isolation)
6. [Performance Considerations](#performance-considerations)
7. [Querying Patterns](#querying-patterns)
8. [Migration Strategy](#migration-strategy)

## Schema Overview

The GPU Fleet Manager database schema is designed to support a multi-tenant SaaS platform that enables organizations to manage GPU resources, run jobs on those resources, track costs, and monitor performance metrics. The schema is organized into two main components:

1. **Core Multi-Tenant Components**: These tables handle user authentication, organization management, and API integrations.
2. **GPU Management Components**: These tables manage GPU resources, job processing, cost tracking, and performance metrics.

The schema follows these design principles:

- **Multi-tenant isolation**: All data is associated with an organization and protected by row-level security.
- **UUID primary keys**: All tables use UUIDs as primary keys for security and scalability.
- **Consistent timestamps**: All tables include `created_at` and `updated_at` fields with automatic updates.
- **Foreign key constraints**: Relationships between tables are explicitly defined with appropriate constraints.
- **Indices for performance**: Frequently queried columns are indexed for optimal performance.

## Core Multi-Tenant Components

### Users

The `users` table stores information about the users who can access the system:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar TEXT,
    auth_id TEXT UNIQUE NOT NULL,  -- External auth provider ID (Auth0)
    default_organization_id UUID,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- One-to-many relationship with `organization_members`
- Many-to-one relationship with `organizations` (default organization)
- One-to-many relationship with `organization_invites`

**Primary Use Cases:**
- User authentication and profile management
- User-specific preferences and settings
- Access control and authorization

### Organizations

The `organizations` table represents tenant accounts within the multi-tenant system:

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- One-to-many relationship with `organization_members`
- One-to-many relationship with `gpu_resources`
- One-to-many relationship with `jobs`
- One-to-many relationship with `cost_tracking`
- One-to-many relationship with `api_keys`
- One-to-many relationship with `webhooks`

**Primary Use Cases:**
- Tenant management
- Billing and subscription management
- Resource allocation and access control

### Organization Members

The `organization_members` table implements the many-to-many relationship between users and organizations:

```sql
CREATE TABLE organization_members (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    role TEXT NOT NULL DEFAULT 'MEMBER',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, organization_id)
);
```

**Key Relationships:**
- Many-to-one relationship with `users`
- Many-to-one relationship with `organizations`

**Primary Use Cases:**
- User access control within organizations
- Role-based permissions management
- Team management

### Organization Invites

The `organization_invites` table handles invitations to join organizations:

```sql
CREATE TABLE organization_invites (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    role TEXT NOT NULL DEFAULT 'MEMBER',
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- Many-to-one relationship with `organizations`
- Many-to-one relationship with `users` (if the invited user already exists)

**Primary Use Cases:**
- Invite users to organizations
- Manage pending invitations
- Track invitation status

### API Keys

The `api_keys` table manages API authentication keys for programmatic access:

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    key TEXT UNIQUE NOT NULL,
    key_hash TEXT UNIQUE NOT NULL,
    last_used TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- Many-to-one relationship with `organizations`

**Primary Use Cases:**
- API authentication
- Usage tracking
- Access control for external integrations

### Webhooks

The `webhooks` table configures notification endpoints for events:

```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    url TEXT NOT NULL,
    events TEXT[] NOT NULL,
    type TEXT NOT NULL DEFAULT 'job_status',
    status TEXT NOT NULL DEFAULT 'active',
    error_rate FLOAT NOT NULL DEFAULT 0,
    signing_secret TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- Many-to-one relationship with `organizations`
- One-to-many relationship with `webhook_deliveries`

**Primary Use Cases:**
- Event notifications for job status changes
- Integration with external systems
- Asynchronous communication with client applications

## GPU Management Components

### GPU Resources

The `gpu_resources` table manages the available GPU hardware resources:

```sql
CREATE TABLE gpu_resources (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name TEXT NOT NULL,
    gpu_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_id TEXT,
    status TEXT NOT NULL DEFAULT 'available',
    memory_total BIGINT NOT NULL,
    memory_allocated BIGINT NOT NULL DEFAULT 0,
    capabilities JSONB DEFAULT '{}',
    cost_per_hour DECIMAL(10,4),
    is_spot BOOLEAN NOT NULL DEFAULT FALSE,
    spot_request_id TEXT,
    termination_time TIMESTAMPTZ,
    in_use BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB,
    last_active TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- Many-to-one relationship with `organizations`
- One-to-many relationship with `jobs`
- One-to-many relationship with `gpu_metrics`
- One-to-many relationship with `cost_tracking`

**Primary Use Cases:**
- GPU inventory management
- Resource allocation and scheduling
- Utilization tracking
- Cost management
- Cloud provider integration

### GPU Metrics

The `gpu_metrics` table stores time-series performance data for GPUs:

```sql
CREATE TABLE gpu_metrics (
    id UUID PRIMARY KEY,
    gpu_id UUID NOT NULL REFERENCES gpu_resources(id),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    memory_used BIGINT NOT NULL,
    memory_total BIGINT NOT NULL,
    gpu_utilization DECIMAL(5,2),
    power_usage DECIMAL(10,2),
    temperature DECIMAL(5,2)
);
```

**Key Relationships:**
- Many-to-one relationship with `gpu_resources`

**Primary Use Cases:**
- Performance monitoring
- Resource utilization tracking
- Anomaly detection
- Cost optimization
- Hardware health monitoring

### Jobs

The `jobs` table tracks computational tasks executed on GPUs:

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    gpu_id UUID REFERENCES gpu_resources(id),
    model_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'queued',
    compute_id TEXT,
    compute_status TEXT,
    compute_logs JSONB,
    error_message TEXT,
    memory INTEGER,  -- Memory required in MB
    input TEXT,
    output TEXT,
    webhook_id TEXT,
    webhook_url TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- Many-to-one relationship with `organizations`
- Many-to-one relationship with `users` (optional, for tracking who submitted the job)
- Many-to-one relationship with `gpu_resources` (optional, for tracking which GPU processed the job)
- One-to-one relationship with `cost_tracking`

**Primary Use Cases:**
- Job submission and tracking
- Workload management
- Status monitoring
- Error tracking
- Resource allocation

### Cost Tracking

The `cost_tracking` table records financial data for GPU usage:

```sql
CREATE TABLE cost_tracking (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    gpu_id UUID NOT NULL REFERENCES gpu_resources(id),
    job_id UUID NOT NULL REFERENCES jobs(id) UNIQUE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    cost_per_hour DECIMAL(10,4) NOT NULL,
    total_cost DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Key Relationships:**
- Many-to-one relationship with `organizations`
- Many-to-one relationship with `gpu_resources`
- One-to-one relationship with `jobs`

**Primary Use Cases:**
- Usage billing
- Cost allocation
- Financial reporting
- Budget tracking
- Cost optimization

## Relationships and Constraints

The database schema implements several key relationships to ensure data integrity:

1. **Organization-based Multi-tenancy**:
   - All major resources (`gpu_resources`, `jobs`, `cost_tracking`) have an `organization_id` foreign key
   - This enforces data segregation between tenants
   - Row-level security policies use these relationships for access control

2. **User-Organization Membership**:
   - The `organization_members` table establishes many-to-many relationships between users and organizations
   - Users can belong to multiple organizations with different roles
   - Each user has a default organization for UI/UX simplicity

3. **Resource Allocation**:
   - Jobs are associated with specific GPUs when assigned
   - Cost tracking links jobs and GPUs for accurate financial reporting
   - GPU metrics are associated with specific GPUs for performance tracking

4. **Cascade Deletion**:
   - When an organization is deleted, all associated resources are automatically deleted
   - This prevents orphaned data while maintaining referential integrity

## Security and Multi-Tenant Isolation

The schema implements a robust security model to ensure multi-tenant isolation:

1. **Row-Level Security (RLS)**:
   - RLS policies are applied to all tables with organization-specific data
   - Policies restrict access to only data belonging to the user's organizations
   - Example policy for the `gpu_resources` table:

```sql
CREATE POLICY "Users can view their organization's GPU resources" ON gpu_resources
    FOR ALL
    USING (
        organization_id IN (
            SELECT organization_id FROM organization_members
            WHERE user_id = auth.uid()
        )
    );
```

2. **Authentication**:
   - External Auth0 integration for user authentication
   - API keys for programmatic access
   - Webhook signing secrets for secure event notifications

3. **Authorization**:
   - Role-based access control via the `role` field in `organization_members`
   - Organization-specific permissions
   - Limited access to sensitive fields (e.g., API key hashes)

## Performance Considerations

The schema includes several performance optimizations:

1. **Indexes**:
   - Primary keys are automatically indexed
   - Foreign keys used in JOIN operations are indexed
   - Columns frequently used in WHERE clauses are indexed
   - Composite indexes for common query patterns

2. **Denormalization**:
   - Strategic denormalization for frequently accessed data
   - `organization_id` is included in most tables to reduce JOIN operations
   - Performance-critical data is duplicated to reduce query complexity

3. **Timestamp Management**:
   - Automated triggers for `updated_at` timestamps
   - Pre-computed time ranges for common reporting queries
   - Indexes on timestamp columns for range queries

## Querying Patterns

Common querying patterns are optimized in the schema design:

1. **Organization-specific Resources**:
```sql
SELECT * FROM gpu_resources
WHERE organization_id = '12345678-90ab-cdef-ghij-klmnopqrstuv'
ORDER BY last_active DESC;
```

2. **User's Organizations**:
```sql
SELECT o.* FROM organizations o
JOIN organization_members om ON o.id = om.organization_id
WHERE om.user_id = '12345678-90ab-cdef-ghij-klmnopqrstuv';
```

3. **Job Status Tracking**:
```sql
SELECT j.*, g.name as gpu_name, g.gpu_type
FROM jobs j
LEFT JOIN gpu_resources g ON j.gpu_id = g.id
WHERE j.organization_id = '12345678-90ab-cdef-ghij-klmnopqrstuv'
AND j.status = 'running'
ORDER BY j.created_at DESC;
```

4. **Cost Analysis**:
```sql
SELECT 
    DATE_TRUNC('day', ct.start_time) as day,
    SUM(ct.total_cost) as daily_cost
FROM cost_tracking ct
WHERE ct.organization_id = '12345678-90ab-cdef-ghij-klmnopqrstuv'
AND ct.start_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', ct.start_time)
ORDER BY day;
```

5. **GPU Utilization**:
```sql
SELECT 
    g.name,
    g.gpu_type,
    AVG(gm.gpu_utilization) as avg_utilization,
    MAX(gm.gpu_utilization) as max_utilization
FROM gpu_metrics gm
JOIN gpu_resources g ON gm.gpu_id = g.id
WHERE g.organization_id = '12345678-90ab-cdef-ghij-klmnopqrstuv'
AND gm.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY g.id, g.name, g.gpu_type;
```

## Migration Strategy

This schema design includes a migration strategy that:

1. **Preserves Existing Data**:
   - Migrations are designed to update schema without data loss
   - Type conversions preserve existing values (TEXT to UUID)
   - Default values ensure data integrity during transitions

2. **Backward Compatibility**:
   - New tables use modern conventions (UUIDs, timestamps, JSON)
   - Existing tables are gradually updated to match new conventions
   - Foreign key constraints are added to ensure referential integrity

3. **Row-Level Security**:
   - RLS policies are implemented without disrupting existing queries
   - Security is enforced at the database level for consistent application
   - Policies are updated when table structures change

4. **Index Management**:
   - Indexes are created after data is loaded for faster initial migrations
   - Performance-critical indexes are prioritized
   - Redundant indexes are removed to prevent performance degradation
