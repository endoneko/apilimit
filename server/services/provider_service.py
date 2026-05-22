"""
提供商服务模块
处理提供商的增删改查
"""
import os
from datetime import datetime

from server.utils.config import load_config, save_config


def add_provider(name, base_url, api_key, models_str=None):
    """
    添加新的提供商
    
    Args:
        name: 提供商名称
        base_url: 基础URL
        api_key: API密钥
        models_str: 模型列表字符串，逗号分隔
    
    Returns:
        新创建的提供商信息
    """
    # 解析模型列表
    models = []
    if models_str:
        models = [m.strip() for m in models_str.split(',') if m.strip()]
    
    # 如果没有指定模型，根据 base_url 智能推断
    if not models:
        base_url_lower = base_url.lower()
        if 'openai' in base_url_lower:
            models = ['gpt-*', 'text-embedding-*', 'dall-e-*']
        elif 'anthropic' in base_url_lower or 'claude' in base_url_lower:
            models = ['claude-*']
        elif 'google' in base_url_lower or 'gemini' in base_url_lower:
            models = ['gemini-*', 'gemma*']
        elif 'ollama' in base_url_lower or '11434' in base_url:
            models = ['*']
        else:
            models = ['*']
    
    config = load_config('providers.json')
    new_provider = {
        "id": f"custom_{os.urandom(4).hex()}",
        "name": name,
        "type": "custom",
        "base_url": base_url,
        "api_keys": [
            {"key": api_key, "name": "Default Key", "is_active": True}
        ],
        "models": models,
        "enabled": True,
        "created_at": datetime.now().isoformat()
    }
    config.setdefault('providers', []).append(new_provider)
    save_config('providers.json', config)
    
    print(f"[ADMIN] Added new provider: {name} with models: {models}")
    return new_provider


def get_all_providers():
    """获取所有提供商"""
    config = load_config('providers.json')
    return config.get('providers', [])


def get_enabled_providers():
    """获取所有启用的提供商"""
    providers = get_all_providers()
    return [p for p in providers if p.get('enabled', True)]


def collect_all_models():
    """
    收集所有启用的提供商的模型
    
    Returns:
        去重后的模型列表
    """
    providers = get_enabled_providers()
    all_models = []
    
    for provider in providers:
        models = provider.get('models', [])
        for model_pattern in models:
            is_pattern = '*' in model_pattern
            all_models.append({
                'name': model_pattern,
                'provider': provider['name'],
                'is_pattern': is_pattern
            })
    
    # 去重
    seen = set()
    unique_models = []
    for m in all_models:
        if m['name'] not in seen:
            seen.add(m['name'])
            unique_models.append(m)
    
    return unique_models
