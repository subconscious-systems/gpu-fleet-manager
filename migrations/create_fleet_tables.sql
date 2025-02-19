-- Create timestamp trigger function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create GPU table
CREATE TABLE IF NOT EXISTS public.gpus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_id TEXT,
    status TEXT NOT NULL DEFAULT 'available',
    total_memory INTEGER NOT NULL,
    available_memory INTEGER NOT NULL,
    capabilities JSONB DEFAULT '{}',
    cost_per_hour DECIMAL(10,4),
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    organization_id UUID,
    spot_request_id TEXT,
    termination_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enable RLS on gpus
ALTER TABLE public.gpus ENABLE ROW LEVEL SECURITY;

-- Add timestamp trigger to gpus table
DROP TRIGGER IF EXISTS update_gpus_timestamp ON public.gpus;
CREATE TRIGGER update_gpus_timestamp
    BEFORE UPDATE ON public.gpus
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Create Jobs table
CREATE TABLE IF NOT EXISTS public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    organization_id UUID,
    model_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    priority INTEGER DEFAULT 50,
    status TEXT NOT NULL DEFAULT 'queued',
    compute_id TEXT,
    compute_status TEXT,
    compute_logs JSONB DEFAULT '{}',
    gpu_id UUID REFERENCES public.gpus(id),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enable RLS on jobs
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

-- Add timestamp trigger to jobs table
DROP TRIGGER IF EXISTS update_jobs_timestamp ON public.jobs;
CREATE TRIGGER update_jobs_timestamp
    BEFORE UPDATE ON public.jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Create GPU Metrics table
CREATE TABLE IF NOT EXISTS public.gpu_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gpu_id UUID REFERENCES public.gpus(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    memory_used INTEGER NOT NULL,
    memory_total INTEGER NOT NULL,
    gpu_utilization DECIMAL(5,2),
    power_usage DECIMAL(10,2),
    temperature DECIMAL(5,2)
);

-- Enable RLS on gpu_metrics
ALTER TABLE public.gpu_metrics ENABLE ROW LEVEL SECURITY;

-- Create Cost Tracking table
CREATE TABLE IF NOT EXISTS public.cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID,
    gpu_id UUID REFERENCES public.gpus(id),
    job_id UUID REFERENCES public.jobs(id),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    cost_per_hour DECIMAL(10,4) NOT NULL,
    total_cost DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Enable RLS on cost_tracking
ALTER TABLE public.cost_tracking ENABLE ROW LEVEL SECURITY;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_gpus_organization_id ON public.gpus(organization_id);
CREATE INDEX IF NOT EXISTS idx_gpus_status ON public.gpus(status);
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON public.jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_organization_id ON public.jobs(organization_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON public.jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON public.jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_gpu_id ON public.jobs(gpu_id);
CREATE INDEX IF NOT EXISTS idx_gpu_metrics_gpu_id ON public.gpu_metrics(gpu_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_organization_id ON public.cost_tracking(organization_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_gpu_id ON public.cost_tracking(gpu_id);
CREATE INDEX IF NOT EXISTS idx_cost_tracking_job_id ON public.cost_tracking(job_id);
