import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CostTracker:
    """Tracks GPU usage costs and provides cost optimization insights"""
    
    def __init__(self):
        self.base_costs = {
            'A100': 3.0,  # Cost per hour
            'A6000': 2.0,
            'V100': 1.5,
            'T4': 0.5
        }
        self.usage_history: Dict[str, Dict] = {}
    
    def start_tracking(self, gpu_id: str, gpu_model: str, provider: str, cost_per_hour: float):
        """Start tracking costs for a GPU"""
        self.usage_history[gpu_id] = {
            'model': gpu_model,
            'provider': provider,
            'cost_per_hour': cost_per_hour,
            'start_time': datetime.utcnow(),
            'total_cost': 0.0,
            'total_hours': 0.0,
            'jobs_completed': 0
        }
    
    def stop_tracking(self, gpu_id: str) -> Optional[Dict]:
        """Stop tracking costs for a GPU and return usage stats"""
        if gpu_id not in self.usage_history:
            return None
            
        usage = self.usage_history[gpu_id]
        end_time = datetime.utcnow()
        hours = (end_time - usage['start_time']).total_seconds() / 3600
        
        usage['total_hours'] = hours
        usage['total_cost'] = hours * usage['cost_per_hour']
        usage['end_time'] = end_time
        
        return usage
    
    def record_job_completion(self, gpu_id: str):
        """Record a completed job for cost averaging"""
        if gpu_id in self.usage_history:
            self.usage_history[gpu_id]['jobs_completed'] += 1
    
    def get_cost_efficiency(self, gpu_id: str) -> float:
        """Calculate cost efficiency score (0-1) for a GPU"""
        if gpu_id not in self.usage_history:
            return 0.0
            
        usage = self.usage_history[gpu_id]
        base_cost = self.base_costs.get(usage['model'], 1.0)
        
        # Calculate efficiency based on cost per job
        if usage['jobs_completed'] > 0 and usage['total_cost'] > 0:
            cost_per_job = usage['total_cost'] / usage['jobs_completed']
            base_cost_per_job = base_cost / 2  # Assume 2 jobs per hour as baseline
            return min(base_cost_per_job / cost_per_job, 1.0)
        
        return 0.0
    
    def get_usage_report(self, since: Optional[datetime] = None) -> Dict:
        """Generate a cost and usage report"""
        if since is None:
            since = datetime.utcnow() - timedelta(days=1)
            
        total_cost = 0.0
        total_jobs = 0
        provider_costs = {}
        model_costs = {}
        
        for gpu_id, usage in self.usage_history.items():
            if 'start_time' in usage and usage['start_time'] >= since:
                cost = usage['total_cost']
                jobs = usage['jobs_completed']
                
                total_cost += cost
                total_jobs += jobs
                
                # Track by provider
                provider = usage['provider']
                provider_costs[provider] = provider_costs.get(provider, 0.0) + cost
                
                # Track by model
                model = usage['model']
                model_costs[model] = model_costs.get(model, 0.0) + cost
        
        return {
            'total_cost': total_cost,
            'total_jobs': total_jobs,
            'cost_per_job': total_cost / total_jobs if total_jobs > 0 else 0,
            'by_provider': provider_costs,
            'by_model': model_costs
        }

# Global cost tracker instance
cost_tracker = CostTracker()
