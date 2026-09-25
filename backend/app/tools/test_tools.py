"""Test execution tools."""

from typing import Any, Dict
import asyncio
from .base import BaseTool

class TestRunner(BaseTool):
    """Execute test suite for the project."""
    name = "tests.run"
    description = "Execute test suite for the project"
    input_schema = {
        "type": "object", 
        "properties": {
            "test_path": {"type": "string"}, 
            "timeout": {"type": "integer"}
        },
        "required": []
    }
    output_schema = {
        "type": "object",
        "properties": {
            "passed": {"type": "integer"},
            "failed": {"type": "integer"},
            "errors": {"type": "integer"},
            "total": {"type": "integer"},
            "output": {"type": "string"}
        },
        "required": ["passed", "failed", "errors", "total", "output"]
    }
    required_permissions = ["test:execute"]
    timeout_seconds = 180
    is_side_effect_free = True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the concrete platform logic for this tool."""
        test_path = parameters.get("test_path", "")
        timeout = parameters.get("timeout", self.timeout_seconds)
        
        try:
            # Simulate test run by running pytest via asyncio subprocess
            cmd = ["pytest"]
            if test_path:
                cmd.append(test_path)
                
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                stdout, stderr = await process.communicate()
                return {
                    "passed": 0,
                    "failed": 0,
                    "errors": 1,
                    "total": 1,
                    "output": f"Tests timed out after {timeout} seconds\nStdout:\n{stdout.decode()}\nStderr:\n{stderr.decode()}"
                }
                
            out = stdout.decode()
            err = stderr.decode()
            full_output = f"{out}\n{err}"
            
            # Very basic parsing, would realistically parse pytest json or junit xml
            passed = out.count("PASSED")
            failed = out.count("FAILED")
            errors = out.count("ERROR")
            total = passed + failed + errors
            
            return {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": total,
                "output": full_output
            }
        except Exception as exc:
            return {
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "total": 0,
                "output": str(exc)
            }
