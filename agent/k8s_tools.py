import logging
import os
from typing import Dict, List, Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from agent.config import get_config

logger = logging.getLogger(__name__)

async def get_k8s_mcp_tools(k8s_server_path: str) -> List[Any]:
    """
    Get tools from the Kubernetes MCP server.
    
    Args:
        k8s_server_path (str): Path to the Kubernetes MCP server script.
        
    Returns:
        List[Any]: List of tools provided by the MCP server.
    """
    try:
        logger.info(f"Connecting to Kubernetes MCP server at {k8s_server_path}")
        
        client = MultiServerMCPClient(
            {
                "kubernetes": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        k8s_server_path,
                        "run",
                        "server.py"
                    ],
                    "transport": "stdio",
                }
            }
        )
        
        tools = await client.get_tools()
        logger.info(f"Successfully retrieved {len(tools)} tools from Kubernetes MCP server")
        
        return tools
    except Exception as e:
        logger.error(f"Failed to get tools from Kubernetes MCP server: {e}")
        raise
