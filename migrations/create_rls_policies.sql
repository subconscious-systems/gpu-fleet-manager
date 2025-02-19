-- GPU Fleet Manager RLS Policies

-- GPUs policies
CREATE POLICY "Users can view GPUs in their organization" ON public.gpus
    FOR SELECT
    USING (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = gpus.organization_id
        )
    );

CREATE POLICY "Organization admins can manage GPUs" ON public.gpus
    FOR ALL
    USING (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = gpus.organization_id 
            AND role = 'admin'
        )
    );

-- Jobs policies
CREATE POLICY "Users can view jobs in their organization" ON public.jobs
    FOR SELECT
    USING (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = jobs.organization_id
        )
    );

CREATE POLICY "Users can create jobs in their organization" ON public.jobs
    FOR INSERT
    WITH CHECK (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = NEW.organization_id
        )
    );

CREATE POLICY "Users can update jobs in their organization" ON public.jobs
    FOR UPDATE
    USING (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = jobs.organization_id
        )
    );

-- GPU Metrics policies
CREATE POLICY "Users can view GPU metrics in their organization" ON public.gpu_metrics
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 
            FROM public.gpus g
            JOIN organization_member om ON g.organization_id = om.organization_id
            WHERE g.id = gpu_metrics.gpu_id 
            AND om.user_id = auth.uid()
        )
    );

-- Cost Tracking policies
CREATE POLICY "Users can view costs for their organization" ON public.cost_tracking
    FOR SELECT
    USING (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = cost_tracking.organization_id
        )
    );

CREATE POLICY "Organization admins can manage cost tracking" ON public.cost_tracking
    FOR ALL
    USING (
        auth.uid() IN (
            SELECT user_id 
            FROM organization_member 
            WHERE organization_id = cost_tracking.organization_id 
            AND role = 'admin'
        )
    );
