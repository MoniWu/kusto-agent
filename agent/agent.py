import logging
import os
from collections.abc import AsyncIterable
from typing import Any, Dict, List, Literal, Optional, Union

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables.config import (
    RunnableConfig,
)
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from agent.config import get_config
from agent.k8s_tools import get_k8s_mcp_tools
from agent.prompt.instructions import (
    K8S_AGENT_SYSTEM_INSTRUCTION,
)

logger = logging.getLogger(__name__)

# Get application config
config = get_config()

memory = MemorySaver()

class K8sAgent:

    def __init__(self):
        azure_config = config.get('azure_openai', {})
        logger.info("Using Azure OpenAI Service")
        self.model = AzureChatOpenAI(
            azure_deployment=azure_config.get('deployment_name'),
            openai_api_version=azure_config.get('api_version'),
            azure_endpoint=azure_config.get('endpoint'),
            api_key=azure_config.get('api_key'),
            temperature=0
        )    
        
    async def initialize_k8s_tools(self, k8s_server_path: str) -> None:
        """
        Initialize the K8s MCP tools and update the agent graph.
        
        Args:
            k8s_server_path (str): Path to the K8s MCP server script.
        """
        try:
            logger.info(f"Initializing K8s MCP tools from {k8s_server_path}")
            # Get tools from the K8s MCP server
            k8s_tools = await get_k8s_mcp_tools(k8s_server_path)
            
            # Update the tools list
            self.tools = k8s_tools
            
            # Recreate the agent graph with the new tools
            self.graph = create_react_agent(
                self.model,
                tools=self.tools,
                checkpointer=memory,
                prompt=K8S_AGENT_SYSTEM_INSTRUCTION
            )
            
            logger.info(f"Successfully initialized K8s agent with {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize K8s tools: {str(e)}")
            raise

    async def stream(
        self, query: str, sessionId: str
    ) -> AsyncIterable[dict[str, Any]]:
        """
        Stream the agent's response for a given query.
        
        Args:
            query (str): The user's query
            sessionId (str): The session ID for continuity
            
        Yields:
            dict: Status updates and the final response
        """
        inputs: dict[str, Any] = {'messages': [('user', query)]}
        config: RunnableConfig = {'configurable': {'thread_id': sessionId}}

        try:
            async for item in self.graph.astream(inputs, config, stream_mode='values'):
                message = item['messages'][-1]
                if (
                    isinstance(message, AIMessage)
                    and message.tool_calls
                    and len(message.tool_calls) > 0
                ):
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': 'Processing your Kubernetes request...',
                    }
                elif isinstance(message, ToolMessage):
                    # Extract information about the tool being used if available
                    tool_name = "Kubernetes tool"
                    if hasattr(message, 'tool_call_id') and message.tool_call_id:
                        parts = message.tool_call_id.split('_')
                        if len(parts) > 1:
                            tool_name = parts[0]
                    
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': f'Executing {tool_name}...',
                    }

            yield await self.get_agent_response(config)
        except Exception as e:
            logger.error(f"Error in stream processing: {str(e)}")
            yield {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error processing your request: {str(e)}',
            }
          
    async def get_agent_response(self, config: RunnableConfig) -> dict[str, Any]:
        """
        Get the final response from the agent without requiring any specific format.
        
        Args:
            config (RunnableConfig): The configuration for the agent
            
        Returns:
            dict: The formatted response with task completion status
        """
        try:
            current_state = await self.graph.aget_state(config)
            messages = current_state.values.get('messages', [])
            
            if not messages:
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': 'No response received. Please try again.',
                }
            
            # Get the last message from the AI
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                # Just return the content as is
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': last_message.content,
                }
                
        except Exception as e:
            logger.error(f"Error processing agent response: {str(e)}")
            
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': 'We encountered an issue processing the response. Please try your request again.',
            }
        
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
