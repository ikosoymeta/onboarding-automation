"""
PR Creation Monitoring Dashboard Definition

Defines metrics and visualizations for tracking Purchase Request creation
via the Vendor Onboarding Automation Skill.

This dashboard can be imported into Meta's Unidash or similar dashboard tools
to monitor PR creation volume, success rates, approval timelines, and blockers.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class DashboardMetric:
    """Definition of a dashboard metric."""
    name: str
    description: str
    query: str  # SQL or Scuba query
    visualization: str  # 'line', 'bar', 'pie', 'table', 'single_value'
    unit: str = "count"
    thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class DashboardPanel:
    """Definition of a dashboard panel."""
    title: str
    metrics: List[DashboardMetric]
    layout: Dict[str, int]  # x, y, width, height
    refresh_interval: int = 300  # seconds


class PRMonitoringDashboard:
    """PR Creation Monitoring Dashboard.
    
    Tracks key metrics for the Vendor Onboarding Automation Skill's
    PR creation feature, including volume, success rates, approval
    timelines, and common blockers.
    """
    
    def __init__(self):
        self.name = "Vendor Onboarding - PR Creation Metrics"
        self.description = (
            "Monitors Purchase Request creation via the Vendor Onboarding "
            "Automation Skill. Tracks PR volume, success rates, approval "
            "timelines, and common blockers."
        )
        self.panels = self._define_panels()
    
    def _define_panels(self) -> List[DashboardPanel]:
        """Define dashboard panels and metrics."""
        return [
            self._overview_panel(),
            self._volume_panel(),
            self._success_rate_panel(),
            self._approval_timeline_panel(),
            self._blockers_panel(),
            self._supplier_metrics_panel(),
        ]
    
    def _overview_panel(self) -> DashboardPanel:
        """Overview panel with key KPIs."""
        return DashboardPanel(
            title="PR Creation Overview",
            layout={"x": 0, "y": 0, "width": 12, "height": 4},
            metrics=[
                DashboardMetric(
                    name="total_prs_created",
                    description="Total PRs created in selected time period",
                    query="""
                        SELECT COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_created'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                    """,
                    visualization="single_value",
                    unit="count"
                ),
                DashboardMetric(
                    name="prs_submitted",
                    description="PRs submitted directly to approval (vs draft)",
                    query="""
                        SELECT COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_created'
                        AND metadata.submit_for_approval = true
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                    """,
                    visualization="single_value",
                    unit="count"
                ),
                DashboardMetric(
                    name="prs_approved",
                    description="PRs approved in selected time period",
                    query="""
                        SELECT COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_approved'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                    """,
                    visualization="single_value",
                    unit="count"
                ),
                DashboardMetric(
                    name="approval_rate",
                    description="Percentage of submitted PRs that get approved",
                    query="""
                        SELECT 
                          (COUNT(CASE WHEN status = 'approved' THEN 1 END) * 100.0 / 
                           COUNT(CASE WHEN status IN ('approved', 'rejected') THEN 1 END)) as rate
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_status_change'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                    """,
                    visualization="single_value",
                    unit="percent",
                    thresholds={"warning": 80.0, "critical": 60.0}
                ),
            ]
        )
    
    def _volume_panel(self) -> DashboardPanel:
        """PR volume trends over time."""
        return DashboardPanel(
            title="PR Creation Volume Trends",
            layout={"x": 0, "y": 4, "width": 6, "height": 6},
            metrics=[
                DashboardMetric(
                    name="prs_by_day",
                    description="PRs created per day, split by mode",
                    query="""
                        SELECT 
                          DATE(timestamp) as date,
                          metadata.submit_for_approval as is_submitted,
                          COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_created'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                        GROUP BY DATE(timestamp), metadata.submit_for_approval
                        ORDER BY date
                    """,
                    visualization="line",
                    unit="count"
                ),
            ]
        )
    
    def _success_rate_panel(self) -> DashboardPanel:
        """PR success rate by supplier and category."""
        return DashboardPanel(
            title="PR Success Rate Analysis",
            layout={"x": 6, "y": 4, "width": 6, "height": 6},
            metrics=[
                DashboardMetric(
                    name="success_by_supplier",
                    description="PR approval rate by supplier (top 10)",
                    query="""
                        SELECT 
                          metadata.supplier_name as supplier,
                          COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
                          COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
                          (COUNT(CASE WHEN status = 'approved' THEN 1 END) * 100.0 / 
                           COUNT(*)) as approval_rate
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_status_change'
                        AND status IN ('approved', 'rejected')
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                        GROUP BY metadata.supplier_name
                        HAVING COUNT(*) >= 3
                        ORDER BY approval_rate DESC
                        LIMIT 10
                    """,
                    visualization="bar",
                    unit="percent"
                ),
            ]
        )
    
    def _approval_timeline_panel(self) -> DashboardPanel:
        """PR approval timeline metrics."""
        return DashboardPanel(
            title="PR Approval Timeline",
            layout={"x": 0, "y": 10, "width": 6, "height": 6},
            metrics=[
                DashboardMetric(
                    name="avg_approval_time",
                    description="Average time from submission to approval (hours)",
                    query="""
                        SELECT 
                          AVG(EXTRACT(EPOCH FROM (approved_at - submitted_at)) / 3600) as avg_hours,
                          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (approved_at - submitted_at)) / 3600) as median_hours,
                          PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (approved_at - submitted_at)) / 3600) as p95_hours
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_approved'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                    """,
                    visualization="table",
                    unit="hours"
                ),
                DashboardMetric(
                    name="approval_time_by_amount",
                    description="Approval time by PR amount tier",
                    query="""
                        SELECT 
                          CASE 
                            WHEN metadata.amount < 10000 THEN 'Under $10K'
                            WHEN metadata.amount < 50000 THEN '$10K-$50K'
                            ELSE 'Over $50K'
                          END as amount_tier,
                          AVG(EXTRACT(EPOCH FROM (approved_at - submitted_at)) / 3600) as avg_hours,
                          COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_approved'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                        GROUP BY amount_tier
                        ORDER BY avg_hours
                    """,
                    visualization="bar",
                    unit="hours"
                ),
            ]
        )
    
    def _blockers_panel(self) -> DashboardPanel:
        """Common PR blockers and failure reasons."""
        return DashboardPanel(
            title="PR Blockers and Failure Analysis",
            layout={"x": 6, "y": 10, "width": 6, "height": 6},
            metrics=[
                DashboardMetric(
                    name="top_blockers",
                    description="Most common reasons PR creation is blocked",
                    query="""
                        SELECT 
                          UNNEST(metadata.blockers) as blocker,
                          COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_blocked'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                        GROUP BY blocker
                        ORDER BY count DESC
                        LIMIT 10
                    """,
                    visualization="pie",
                    unit="count"
                ),
                DashboardMetric(
                    name="rejection_reasons",
                    description="Most common PR rejection reasons",
                    query="""
                        SELECT 
                          metadata.rejection_reason as reason,
                          COUNT(*) as count
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'pr_rejected'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                        GROUP BY metadata.rejection_reason
                        ORDER BY count DESC
                        LIMIT 10
                    """,
                    visualization="table",
                    unit="count"
                ),
            ]
        )
    
    def _supplier_metrics_panel(self) -> DashboardPanel:
        """Supplier-related metrics."""
        return DashboardPanel(
            title="Supplier Metrics",
            layout={"x": 0, "y": 16, "width": 12, "height": 6},
            metrics=[
                DashboardMetric(
                    name="supplier_readiness",
                    description="Supplier readiness check results",
                    query="""
                        SELECT 
                          metadata.supplier_name as supplier,
                          metadata.exists as exists_in_buyat,
                          metadata.is_active as is_active,
                          metadata.tpa_status as tpa_status,
                          metadata.can_proceed as can_proceed
                        FROM vendor_onboarding_pr_events
                        WHERE event_type = 'supplier_readiness_check'
                        AND timestamp >= '{start_time}'
                        AND timestamp <= '{end_time}'
                        ORDER BY timestamp DESC
                        LIMIT 50
                    """,
                    visualization="table",
                    unit="count"
                ),
            ]
        )
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get complete dashboard configuration."""
        return {
            "name": self.name,
            "description": self.description,
            "panels": [
                {
                    "title": panel.title,
                    "layout": panel.layout,
                    "refresh_interval": panel.refresh_interval,
                    "metrics": [
                        {
                            "name": metric.name,
                            "description": metric.description,
                            "query": metric.query,
                            "visualization": metric.visualization,
                            "unit": metric.unit,
                            "thresholds": metric.thresholds
                        }
                        for metric in panel.metrics
                    ]
                }
                for panel in self.panels
            ],
            "tags": ["vendor-onboarding", "procurement", "pr-creation", "metamate"],
            "owner": "BO&SS: Operations",
            "contact": "ikosoy@meta.com"
        }


# Example usage for creating the dashboard
def create_pr_dashboard():
    """Create and configure the PR monitoring dashboard."""
    dashboard = PRMonitoringDashboard()
    config = dashboard.get_dashboard_config()
    
    # This config can be used with Meta's dashboard tools
    # Example: Unidash API, Scuba dashboard API, etc.
    
    print(f"Dashboard: {config['name']}")
    print(f"Description: {config['description']}")
    print(f"Panels: {len(config['panels'])}")
    print(f"Total Metrics: {sum(len(p['metrics']) for p in config['panels'])}")
    
    return config


if __name__ == "__main__":
    # Generate dashboard configuration
    config = create_pr_dashboard()
    
    # Output as JSON for import into dashboard tools
    import json
    print("\n" + "="*60)
    print("Dashboard Configuration (JSON):")
    print("="*60)
    print(json.dumps(config, indent=2))
