"""GitHub integration tools."""

from typing import Any, Dict
import httpx
from .base import BaseTool

class GitHubGetRepository(BaseTool):
    """Fetch repository metadata."""
    name = "github.get_repository"
    description = "Fetch repository metadata"
    input_schema = {
        "type": "object",
        "properties": {
            "owner": {"type": "string"},
            "repo": {"type": "string"}
        },
        "required": ["owner", "repo"]
    }
    output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "default_branch": {"type": "string"}
        },
        "required": ["id", "name", "default_branch"]
    }
    required_permissions = ["repo:read"]
    timeout_seconds = 15
    is_side_effect_free = True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the concrete platform logic for this tool."""
        owner = parameters.get("owner")
        repo = parameters.get("repo")
        token = context.get("github_token")
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers=headers,
                    timeout=self.timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "default_branch": data.get("default_branch")
                }
            except httpx.HTTPError as exc:
                return {"error": f"GitHub API request failed: {str(exc)}"}


class GitHubGetPullRequest(BaseTool):
    """Fetch pull request details."""
    name = "github.get_pull_request"
    description = "Fetch pull request details"
    input_schema = {
        "type": "object",
        "properties": {
            "owner": {"type": "string"},
            "repo": {"type": "string"},
            "pull_number": {"type": "integer"}
        },
        "required": ["pull_number"]
    }
    output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "number": {"type": "integer"},
            "title": {"type": "string"},
            "state": {"type": "string"},
            "body": {"type": "string"},
            "base_branch": {"type": "string"},
            "head_branch": {"type": "string"},
            "head_sha": {"type": "string"},
            "author": {"type": "string"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "additions": {"type": "integer"},
            "deletions": {"type": "integer"},
            "changed_files": {"type": "integer"}
        },
        "required": ["id", "number", "title", "state", "base_branch", "head_branch"]
    }
    required_permissions = ["repo:read"]
    timeout_seconds = 15
    is_side_effect_free = True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the concrete platform logic for this tool."""
        owner = parameters.get("owner") or context.get("owner")
        repo = parameters.get("repo") or context.get("repo")
        pull_number = parameters.get("pull_number")
        token = context.get("github_token")
        
        if not owner or not repo:
            return {"error": "Missing owner or repo in parameters or context"}
            
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}",
                    headers=headers,
                    timeout=self.timeout_seconds
                )
                response.raise_for_status()
                data = response.json()
                return {
                    "id": data.get("id"),
                    "number": data.get("number"),
                    "title": data.get("title"),
                    "state": data.get("state"),
                    "body": data.get("body"),
                    "base_branch": data.get("base", {}).get("ref"),
                    "head_branch": data.get("head", {}).get("ref"),
                    "head_sha": data.get("head", {}).get("sha"),
                    "author": data.get("user", {}).get("login"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "additions": data.get("additions"),
                    "deletions": data.get("deletions"),
                    "changed_files": data.get("changed_files")
                }
            except httpx.HTTPError as exc:
                return {"error": f"GitHub API request failed: {str(exc)}"}


class GitHubGetDiff(BaseTool):
    """Fetch diff for a pull request."""
    name = "github.get_diff"
    description = "Fetch diff for a pull request"
    input_schema = {
        "type": "object",
        "properties": {
            "owner": {"type": "string"},
            "repo": {"type": "string"},
            "pull_number": {"type": "integer"}
        },
        "required": ["pull_number"]
    }
    output_schema = {
        "type": "object",
        "properties": {
            "pull_number": {"type": "integer"},
            "diff_text": {"type": "string"},
            "files_changed": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "status": {"type": "string"},
                        "additions": {"type": "integer"},
                        "deletions": {"type": "integer"},
                        "patch": {"type": "string"}
                    }
                }
            }
        },
        "required": ["pull_number", "diff_text", "files_changed"]
    }
    required_permissions = ["repo:read"]
    timeout_seconds = 30
    is_side_effect_free = True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the concrete platform logic for this tool."""
        owner = parameters.get("owner") or context.get("owner")
        repo = parameters.get("repo") or context.get("repo")
        pull_number = parameters.get("pull_number")
        token = context.get("github_token")
        
        if not owner or not repo:
            return {"error": "Missing owner or repo in parameters or context"}
            
        headers = {"Accept": "application/vnd.github.v3.diff"}
        api_headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            api_headers["Authorization"] = f"Bearer {token}"
            
        async with httpx.AsyncClient() as client:
            try:
                # Get the diff text
                diff_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}",
                    headers=headers,
                    timeout=self.timeout_seconds
                )
                diff_response.raise_for_status()
                diff_text = diff_response.text

                # Get files changed
                files_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files",
                    headers=api_headers,
                    timeout=self.timeout_seconds
                )
                files_response.raise_for_status()
                files_data = files_response.json()
                
                files_changed = []
                for file_info in files_data:
                    files_changed.append({
                        "filename": file_info.get("filename"),
                        "status": file_info.get("status"),
                        "additions": file_info.get("additions"),
                        "deletions": file_info.get("deletions"),
                        "patch": file_info.get("patch", "")
                    })

                return {
                    "pull_number": pull_number,
                    "diff_text": diff_text,
                    "files_changed": files_changed
                }
            except httpx.HTTPError as exc:
                return {"error": f"GitHub API request failed: {str(exc)}"}
