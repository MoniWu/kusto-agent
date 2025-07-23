"""
Configuration module for the A2A Agent.

This module contains configuration settings for the A2A Agent application.
"""

import os
import logging
import yaml

logger = logging.getLogger(__name__)

# Default configuration settings
DEFAULT_CONFIG = {
    "azure_openai": {
        "api_key": None,  # Should be set via environment variable
        "endpoint": None,  # Should be set via environment variable
        "api_version": None,  # Should be set via environment variable
        "deployment_name": None,  # Should be set via environment variable
    },
    "appinsight": {
        "app_id": None,  # Should be set via environment variable
    }
}


def get_config(config_path=None):
    """
    Get the configuration for the application.
    
    Args:
        config_path (str, optional): Path to a custom configuration file.
        
    Returns:
        dict: The configuration dictionary.
    """
    import json
    from copy import deepcopy
    from dotenv import load_dotenv
    
    # Ensure environment variables are loaded, with .env.local taking precedence
    load_dotenv()
    
    config = deepcopy(DEFAULT_CONFIG)
    
    # Override with custom config file if provided
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            custom_config = yaml.safe_load(f)
            _deep_update(config, custom_config)
      # Override with environment variables
        
    # Override Azure OpenAI settings from environment variables
    if os.environ.get('AZURE_OPENAI_API_KEY'):
        config['azure_openai']['api_key'] = os.environ.get('AZURE_OPENAI_API_KEY')
    if os.environ.get('AZURE_OPENAI_ENDPOINT'):
        config['azure_openai']['endpoint'] = os.environ.get('AZURE_OPENAI_ENDPOINT')
    if os.environ.get('AZURE_OPENAI_API_VERSION'):
        config['azure_openai']['api_version'] = os.environ.get('AZURE_OPENAI_API_VERSION')
    if os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME'):
        config['azure_openai']['deployment_name'] = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME')
    
    # Override AppInsight settings from environment variables
    if os.environ.get('AZURE_APPINSIGHT_ID'):
        config['appinsight']['app_id'] = os.environ.get('AZURE_APPINSIGHT_ID')


    return config
