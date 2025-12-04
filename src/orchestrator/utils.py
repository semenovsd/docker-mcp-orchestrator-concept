"""Utility functions for Orchestrator."""

import asyncio
import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def run_command(
    cmd: List[str], timeout: int = 30, retries: int = 3, delay: int = 1
) -> tuple[str, int]:
    """
    Run a command asynchronously with retry logic.

    Args:
        cmd: Command to run
        timeout: Command timeout in seconds
        retries: Number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        Tuple of (stdout, return_code)
    """
    for attempt in range(retries):
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            if process.returncode == 0:
                return stdout.decode("utf-8"), 0
            else:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                logger.warning(
                    f"Command failed (attempt {attempt + 1}/{retries}): {error_msg}"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    return error_msg, process.returncode

        except asyncio.TimeoutError:
            logger.warning(f"Command timeout (attempt {attempt + 1}/{retries})")
            if attempt < retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))
            else:
                return "Command timeout", -1

        except Exception as e:
            logger.error(f"Error running command: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))
            else:
                return str(e), -1

    return "Max retries exceeded", -1


def parse_json_output(output: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON output from command.

    Args:
        output: JSON string output

    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return None


def find_tool_server(tool_name: str, servers: Dict[str, List[str]]) -> Optional[str]:
    """
    Find which server provides a specific tool.

    Args:
        tool_name: Name of the tool
        servers: Dictionary mapping server names to their tool names

    Returns:
        Server name that provides the tool, or None if not found
    """
    for server, tools in servers.items():
        if tool_name in tools:
            return server
    return None


def escape_url_for_xml(url: str) -> str:
    """
    Escape URL for safe use in XML documents (VAST, etc.).

    This function escapes ampersand characters (&) in URLs to &amp; to prevent
    XML parser errors. It correctly handles URLs that may already contain
    some escaped entities.

    Args:
        url: URL string that may contain unescaped ampersands

    Returns:
        URL with ampersands properly escaped for XML

    Examples:
        >>> escape_url_for_xml("https://example.com?param1=value1&param2=value2")
        'https://example.com?param1=value1&amp;param2=value2'

        >>> escape_url_for_xml("https://example.com?c=25&pli=123")
        'https://example.com?c=25&amp;pli=123'

        >>> escape_url_for_xml("https://example.com?&mh_camp=123")
        'https://example.com?&amp;mh_camp=123'
    """
    if not url:
        return url

    # Pattern to match ampersands that are NOT part of XML entity references
    # XML entities: &amp; &lt; &gt; &quot; &apos; &#123; &#x1F;
    # This regex matches & that is NOT followed by:
    # - amp; (for &amp;)
    # - lt; (for &lt;)
    # - gt; (for &gt;)
    # - quot; (for &quot;)
    # - apos; (for &apos;)
    # - # followed by digits or x+hex (for numeric entities)
    entity_pattern = r"&(?!(?:amp|lt|gt|quot|apos);|#(?:\d+|x[0-9a-fA-F]+);)"

    # Replace unescaped ampersands with &amp;
    escaped_url = re.sub(entity_pattern, "&amp;", url)

    return escaped_url
