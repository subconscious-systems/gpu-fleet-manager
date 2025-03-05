-- Migration: Schema Enhancements
-- Description: Adds missing relationships, constraints, and indices to support
-- complete multi-tenant architecture for GPU Fleet Manager.
-- Date: 2025-03-04

-- =============================================================================
-- ENSURE ALL TABLES FOLLOW CONSISTENT PATTERNS
-- =============================================================================

-- Ensure UUID primary keys and timestamps use consistent naming and types
DO $$
BEGIN
    -- Add createdAt and updatedAt to any table missing them
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'gpus' AND column_name = 'created_at') THEN
        ALTER TABLE gpus ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'gpus' AND column_name = 'updated_at') THEN
        ALTER TABLE gpus ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- Convert TEXT id fields to UUID where needed
    BEGIN
        -- Check if jobs.id is TEXT or VARCHAR
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'id' 
            AND (data_type = 'character varying' OR data_type = 'text')
        ) THEN
            -- Create temporary column
            ALTER TABLE jobs ADD COLUMN id_new UUID;
            
            -- Update it with UUID values (attempt conversion if possible)
            UPDATE jobs SET id_new = 
                CASE 
                    WHEN id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN id::UUID
                    ELSE gen_random_uuid() 
                END;
            
            -- Drop old column constraints
            ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_pkey CASCADE;
            
            -- Drop the old column
            ALTER TABLE jobs DROP COLUMN id;
            
            -- Rename the new column
            ALTER TABLE jobs RENAME COLUMN id_new TO id;
            
            -- Add primary key constraint
            ALTER TABLE jobs ADD PRIMARY KEY (id);
        END IF;
        
        -- Similar conversion for gpus.id if needed
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'gpus' AND column_name = 'id' 
            AND (data_type = 'character varying' OR data_type = 'text')
        ) THEN
            -- Create temporary column
            ALTER TABLE gpus ADD COLUMN id_new UUID;
            
            -- Update it with UUID values
            UPDATE gpus SET id_new = 
                CASE 
                    WHEN id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN id::UUID
                    ELSE gen_random_uuid() 
                END;
            
            -- Drop old column constraints
            ALTER TABLE gpus DROP CONSTRAINT IF EXISTS gpus_pkey CASCADE;
            
            -- Drop the old column
            ALTER TABLE gpus DROP COLUMN id;
            
            -- Rename the new column
            ALTER TABLE gpus RENAME COLUMN id_new TO id;
            
            -- Add primary key constraint
            ALTER TABLE gpus ADD PRIMARY KEY (id);
        END IF;
        
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Error converting TEXT to UUID: %', SQLERRM;
    END;
END $$;

-- =============================================================================
-- ENHANCE GPU RESOURCE MANAGEMENT
-- =============================================================================

-- Create a more comprehensive gpu_resources table if it doesn't exist yet
CREATE TABLE IF NOT EXISTS gpu_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    gpu_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_id TEXT,
    status TEXT NOT NULL DEFAULT 'available',
    memory_total BIGINT NOT NULL,
    memory_allocated BIGINT NOT NULL DEFAULT 0,
    capabilities JSONB DEFAULT '{}',
    cost_per_hour DECIMAL(10,4),
    is_spot BOOLEAN NOT NULL DEFAULT false,
    spot_request_id TEXT,
    termination_time TIMESTAMPTZ,
    in_use BOOLEAN NOT NULL DEFAULT false,
    metadata JSONB,
    last_active TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    organization_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_gpu_resources_organization 
        FOREIGN KEY (organization_id) 
        REFERENCES organizations(id) 
        ON DELETE CASCADE
);

-- Add organization_id FK to gpus table if it's not already a UUID reference
DO $$
BEGIN
    -- If gpus.organization_id exists and is TEXT, convert it to UUID with FK constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'gpus' AND column_name = 'organization_id' 
        AND (data_type = 'character varying' OR data_type = 'text')
    ) THEN
        -- Create temporary column
        ALTER TABLE gpus ADD COLUMN organization_id_new UUID;
        
        -- Try to update with UUID values based on organizations table
        UPDATE gpus g 
        SET organization_id_new = o.id
        FROM organizations o
        WHERE g.organization_id = o.id::TEXT;
        
        -- For any that didn't match, set to a default organization (first one)
        UPDATE gpus g
        SET organization_id_new = (SELECT id FROM organizations ORDER BY created_at LIMIT 1)
        WHERE organization_id_new IS NULL;
        
        -- Drop the old column
        ALTER TABLE gpus DROP COLUMN organization_id;
        
        -- Rename the new column
        ALTER TABLE gpus RENAME COLUMN organization_id_new TO organization_id;
        
        -- Add not null constraint
        ALTER TABLE gpus ALTER COLUMN organization_id SET NOT NULL;
        
        -- Add foreign key constraint
        ALTER TABLE gpus 
        ADD CONSTRAINT fk_gpus_organization 
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
    
    -- If gpus.organization_id exists but has no FK, add it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'gpus' AND column_name = 'organization_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
        ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = 'gpus' 
        AND ccu.column_name = 'organization_id'
    ) THEN
        ALTER TABLE gpus 
        ADD CONSTRAINT fk_gpus_organization 
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error updating gpus.organization_id: %', SQLERRM;
END $$;

-- =============================================================================
-- ENHANCE JOB MANAGEMENT
-- =============================================================================

-- Add organization_id FK to jobs table
DO $$
BEGIN
    -- If jobs.organization_id exists and is TEXT, convert it to UUID with FK constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'jobs' AND column_name = 'organization_id' 
        AND (data_type = 'character varying' OR data_type = 'text')
    ) THEN
        -- Create temporary column
        ALTER TABLE jobs ADD COLUMN organization_id_new UUID;
        
        -- Try to update with UUID values based on organizations table
        UPDATE jobs j 
        SET organization_id_new = o.id
        FROM organizations o
        WHERE j.organization_id = o.id::TEXT;
        
        -- For any that didn't match, set to a default organization (first one)
        UPDATE jobs j
        SET organization_id_new = (SELECT id FROM organizations ORDER BY created_at LIMIT 1)
        WHERE organization_id_new IS NULL;
        
        -- Drop the old column
        ALTER TABLE jobs DROP COLUMN organization_id;
        
        -- Rename the new column
        ALTER TABLE jobs RENAME COLUMN organization_id_new TO organization_id;
        
        -- Add not null constraint
        ALTER TABLE jobs ALTER COLUMN organization_id SET NOT NULL;
        
        -- Add foreign key constraint
        ALTER TABLE jobs 
        ADD CONSTRAINT fk_jobs_organization 
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
    
    -- If jobs.organization_id exists but has no FK, add it
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'jobs' AND column_name = 'organization_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
        ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = 'jobs' 
        AND ccu.column_name = 'organization_id'
    ) THEN
        ALTER TABLE jobs 
        ADD CONSTRAINT fk_jobs_organization 
        FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
    
    -- Create or ensure proper reference from jobs to gpus
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'jobs' AND column_name = 'gpu_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu 
        ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_name = 'jobs' 
        AND ccu.column_name = 'gpu_id'
    ) THEN
        -- Try to add FK constraint if column types match
        BEGIN
            ALTER TABLE jobs 
            ADD CONSTRAINT fk_jobs_gpu 
            FOREIGN KEY (gpu_id) REFERENCES gpus(id) ON DELETE SET NULL;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Could not add FK from jobs.gpu_id to gpus.id: %', SQLERRM;
                
                -- If gpus.id is UUID but jobs.gpu_id is TEXT, convert jobs.gpu_id
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'jobs' AND column_name = 'gpu_id' 
                    AND (data_type = 'character varying' OR data_type = 'text')
                ) THEN
                    -- Create temporary column
                    ALTER TABLE jobs ADD COLUMN gpu_id_new UUID;
                    
                    -- Try to update with UUID values
                    UPDATE jobs 
                    SET gpu_id_new = 
                        CASE 
                            WHEN gpu_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN gpu_id::UUID
                            ELSE NULL
                        END;
                    
                    -- Drop the old column
                    ALTER TABLE jobs DROP COLUMN gpu_id;
                    
                    -- Rename the new column
                    ALTER TABLE jobs RENAME COLUMN gpu_id_new TO gpu_id;
                    
                    -- Add foreign key constraint
                    ALTER TABLE jobs 
                    ADD CONSTRAINT fk_jobs_gpu 
                    FOREIGN KEY (gpu_id) REFERENCES gpus(id) ON DELETE SET NULL;
                END IF;
        END;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error updating jobs relationships: %', SQLERRM;
END $$;

-- =============================================================================
-- SETUP COST TRACKING
-- =============================================================================

-- Create cost_tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    gpu_id UUID NOT NULL,
    job_id UUID NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    cost_per_hour DECIMAL(10,4) NOT NULL,
    total_cost DECIMAL(10,4),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_cost_tracking_organization 
        FOREIGN KEY (organization_id) 
        REFERENCES organizations(id) 
        ON DELETE CASCADE,
        
    CONSTRAINT fk_cost_tracking_gpu 
        FOREIGN KEY (gpu_id) 
        REFERENCES gpus(id) 
        ON DELETE CASCADE,
        
    CONSTRAINT fk_cost_tracking_job 
        FOREIGN KEY (job_id) 
        REFERENCES jobs(id) 
        ON DELETE CASCADE,
        
    CONSTRAINT uq_cost_tracking_job UNIQUE (job_id)
);

-- =============================================================================
-- SETUP GPU METRICS TRACKING
-- =============================================================================

-- Ensure gpu_metrics table properly references gpus
CREATE TABLE IF NOT EXISTS gpu_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gpu_id UUID NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    memory_used BIGINT NOT NULL,
    memory_total BIGINT NOT NULL,
    gpu_utilization DECIMAL(5,2),
    power_usage DECIMAL(10,2),
    temperature DECIMAL(5,2),
    
    CONSTRAINT fk_gpu_metrics_gpu 
        FOREIGN KEY (gpu_id) 
        REFERENCES gpus(id) 
        ON DELETE CASCADE
);

-- =============================================================================
-- CREATE MISSING INDICES
-- =============================================================================

-- Add indices for all tables where foreign keys or common search fields exist
CREATE INDEX IF NOT EXISTS idx_gpus_organization_id ON gpus(organization_id);
CREATE INDEX IF NOT EXISTS idx_gpus_status ON gpus(status);
CREATE INDEX IF NOT EXISTS idx_gpus_provider ON gpus(provider);
CREATE INDEX IF NOT EXISTS idx_gpus_last_active ON gpus(last_active);

CREATE INDEX IF NOT EXISTS idx_jobs_organization_id ON jobs(organization_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_gpu_id ON jobs(gpu_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);

CREATE INDEX IF NOT EXISTS idx_gpu_metrics_gpu_id ON gpu_metrics(gpu_id);
CREATE INDEX IF NOT EXISTS idx_gpu_metrics_timestamp ON gpu_metrics(timestamp);

CREATE INDEX IF NOT EXISTS idx_cost_tracking_organization_id ON cost_tracking(organization_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_gpu_id ON cost_tracking(gpu_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_job_id ON cost_tracking(job_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_time_range ON cost_tracking(start_time, end_time);

-- If gpu_resources table exists, add indices
CREATE INDEX IF NOT EXISTS idx_gpu_resources_organization_id ON gpu_resources(organization_id);
CREATE INDEX IF NOT EXISTS idx_gpu_resources_status ON gpu_resources(status);
CREATE INDEX IF NOT EXISTS idx_gpu_resources_provider ON gpu_resources(provider);
CREATE INDEX IF NOT EXISTS idx_gpu_resources_last_active ON gpu_resources(last_active);

-- =============================================================================
-- IMPLEMENT ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables that might not have it yet
ALTER TABLE IF EXISTS gpus ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS gpu_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cost_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS gpu_resources ENABLE ROW LEVEL SECURITY;

-- Create policies for multi-tenant isolation
DO $$
BEGIN
    -- For gpus table
    DROP POLICY IF EXISTS "Users can view their organization's GPUs" ON gpus;
    CREATE POLICY "Users can view their organization's GPUs" ON gpus
        FOR ALL
        USING (
            organization_id IN (
                SELECT organization_id FROM organization_members
                WHERE user_id = auth.uid()
            )
        );

    -- For jobs table
    DROP POLICY IF EXISTS "Users can view their organization's jobs" ON jobs;
    CREATE POLICY "Users can view their organization's jobs" ON jobs
        FOR ALL
        USING (
            organization_id IN (
                SELECT organization_id FROM organization_members
                WHERE user_id = auth.uid()
            )
        );

    -- For gpu_metrics table
    DROP POLICY IF EXISTS "Users can view their organization's GPU metrics" ON gpu_metrics;
    CREATE POLICY "Users can view their organization's GPU metrics" ON gpu_metrics
        FOR ALL
        USING (
            gpu_id IN (
                SELECT id FROM gpus WHERE
                organization_id IN (
                    SELECT organization_id FROM organization_members
                    WHERE user_id = auth.uid()
                )
            )
        );

    -- For cost_tracking table
    DROP POLICY IF EXISTS "Users can view their organization's cost tracking" ON cost_tracking;
    CREATE POLICY "Users can view their organization's cost tracking" ON cost_tracking
        FOR ALL
        USING (
            organization_id IN (
                SELECT organization_id FROM organization_members
                WHERE user_id = auth.uid()
            )
        );

    -- For gpu_resources table if it exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gpu_resources') THEN
        DROP POLICY IF EXISTS "Users can view their organization's GPU resources" ON gpu_resources;
        CREATE POLICY "Users can view their organization's GPU resources" ON gpu_resources
            FOR ALL
            USING (
                organization_id IN (
                    SELECT organization_id FROM organization_members
                    WHERE user_id = auth.uid()
                )
            );
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error setting up RLS policies: %', SQLERRM;
END $$;

-- =============================================================================
-- CREATE UPDATE TRIGGERS FOR TIMESTAMPS
-- =============================================================================

-- Create update_timestamp function if it doesn't exist
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for automatic timestamp updates
DO $$
BEGIN
    -- For gpus table
    DROP TRIGGER IF EXISTS update_gpus_timestamp ON gpus;
    CREATE TRIGGER update_gpus_timestamp
        BEFORE UPDATE ON gpus
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp();

    -- For jobs table
    DROP TRIGGER IF EXISTS update_jobs_timestamp ON jobs;
    CREATE TRIGGER update_jobs_timestamp
        BEFORE UPDATE ON jobs
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp();

    -- For gpu_resources table if it exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'gpu_resources') THEN
        DROP TRIGGER IF EXISTS update_gpu_resources_timestamp ON gpu_resources;
        CREATE TRIGGER update_gpu_resources_timestamp
            BEFORE UPDATE ON gpu_resources
            FOR EACH ROW
            EXECUTE FUNCTION update_timestamp();
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error setting up update triggers: %', SQLERRM;
END $$;
