"""Tools package."""

from .base import BaseTool, ToolRegistry
from .github_tools import GitHubGetRepository, GitHubGetPullRequest, GitHubGetDiff
from .test_tools import TestRunner
from .deployment_tools import DeploymentDeploy, DeploymentStatus, DeploymentLogs, DeploymentRollback
from .log_tools import LogFetcher, LogAnalyzer
from .metrics_tools import MetricsCollector, MetricsAnalyzer
from .kubernetes_tools import KubernetesGetPods, KubernetesGetPodLogs, KubernetesGetDeployments

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "GitHubGetRepository",
    "GitHubGetPullRequest",
    "GitHubGetDiff",
    "TestRunner",
    "DeploymentDeploy",
    "DeploymentStatus",
    "DeploymentLogs",
    "DeploymentRollback",
    "LogFetcher",
    "LogAnalyzer",
    "MetricsCollector",
    "MetricsAnalyzer",
    "KubernetesGetPods",
    "KubernetesGetPodLogs",
    "KubernetesGetDeployments",
    "register_all_tools"
]

def register_all_tools(registry: ToolRegistry) -> None:
    """Register all available tools in the provided registry."""
    registry.register(GitHubGetRepository())
    registry.register(GitHubGetPullRequest())
    registry.register(GitHubGetDiff())
    registry.register(TestRunner())
    registry.register(DeploymentDeploy())
    registry.register(DeploymentStatus())
    registry.register(DeploymentLogs())
    registry.register(DeploymentRollback())
    registry.register(LogFetcher())
    registry.register(LogAnalyzer())
    registry.register(MetricsCollector())
    registry.register(MetricsAnalyzer())
    registry.register(KubernetesGetPods())
    registry.register(KubernetesGetPodLogs())
    registry.register(KubernetesGetDeployments())
