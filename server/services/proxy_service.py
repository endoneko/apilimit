"""
代理服务模块
处理API请求的转发和响应处理
"""
import json
import requests
from flask import request, jsonify, Response

from core.db import deduct_quota, log_request
from server.utils.config import load_config
from server.utils.model_matcher import match_model_pattern


def find_provider_by_model(requested_model, providers):
    """根据模型名称查找匹配的提供商"""
    if not requested_model:
        return None, None
    
    for provider in providers:
        if not provider.get('enabled', True):
            continue
        supported_models = provider.get('models', [])
        for pattern in supported_models:
            if match_model_pattern(requested_model, pattern):
                print(f"[ROUTER] Model '{requested_model}' matched to provider '{provider['name']}' via pattern '{pattern}'")
                return provider, provider['id']
    return None, None


def find_provider_by_route(request_path, routes_config, providers):
    """根据路由表查找提供商"""
    route = next((r for r in routes_config.get('routes', []) if r['path'] == request_path), None)
    if route:
        provider_id = route['provider']
        provider = next((p for p in providers if p['id'] == provider_id), None)
        print(f"[ROUTER] Using route table match: {provider_id}")
        return provider, provider_id
    return None, None


def get_default_provider(providers):
    """获取默认提供商（第一个启用的提供商）"""
    provider = next((p for p in providers if p.get('enabled', True)), None)
    if provider:
        print(f"[ROUTER] Using default provider: {provider['id']}")
        return provider, provider['id']
    return None, None


def forward_request(subpath, user, payload):
    """
    转发请求到目标提供商
    
    Args:
        subpath: API路径
        user: 用户信息
        payload: 请求体
    
    Returns:
        Flask Response对象
    """
    request_path = f"/v1/{subpath}"
    user_id = user['id']
    requested_model = payload.get('model', '')
    
    # 加载配置
    routes_config = load_config('routes.json')
    providers_config = load_config('providers.json')
    providers = providers_config.get('providers', [])
    
    # 智能路由与Provider匹配
    provider = None
    provider_id = None
    
    # 1. 首先尝试根据模型名称智能匹配提供商
    if requested_model:
        provider, provider_id = find_provider_by_model(requested_model, providers)
    
    # 2. 如果模型没有匹配到，尝试从路由表匹配
    if not provider:
        provider, provider_id = find_provider_by_route(request_path, routes_config, providers)
    
    # 3. 如果都没有匹配到，使用默认提供商
    if not provider:
        provider, provider_id = get_default_provider(providers)
    
    if not provider or not provider.get('enabled', True):
        return jsonify({"error": "Corresponding provider is offline or missing"}), 404
    
    # 获取目标连接与提供商凭证
    target_url = f"{provider['base_url'].rstrip('/')}/{subpath}"
    active_keys = [k for k in provider.get('api_keys', []) if k.get('is_active')]
    
    if not active_keys:
        return jsonify({"error": "No active API keys available on Provider"}), 503
    
    provider_key = active_keys[0]['key']
    
    headers = {
        "Authorization": f"Bearer {provider_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # 请求转发与响应处理
        request_method = request.method
        if request_method == 'GET':
            resp = requests.get(target_url, headers=headers, stream=True)
            payload = {}
        else:
            resp = requests.post(target_url, headers=headers, json=payload, stream=True)
        
        is_stream = request.args.get('stream') == 'true' or payload.get('stream')
        
        # 计算真实 token 消耗
        actual_tokens = 0
        
        if is_stream:
            return handle_stream_response(resp, payload, user_id, provider, target_url)
        else:
            return handle_normal_response(resp, payload, user_id, provider, target_url)
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] Proxy request failed: {str(e)}")
        print(f"[ERROR] Target URL: {target_url}")
        print(f"[ERROR] Traceback: {error_details}")
        log_request(user_id, provider['id'] if provider else 'unknown', target_url, 500, 0)
        return jsonify({"error": "Proxy Request Failed", "details": str(e)}), 500


def handle_stream_response(resp, payload, user_id, provider, target_url):
    """处理流式响应"""
    full_content = b''
    for chunk in resp.iter_content(chunk_size=1024):
        if chunk:
            full_content += chunk
    
    actual_tokens = 0
    
    # 尝试从流式响应中提取 token 使用量
    try:
        content_str = full_content.decode('utf-8', errors='ignore')
        for line in content_str.split('\n'):
            if line.startswith('data:') and '"usage"' in line:
                data = json.loads(line[5:].strip())
                usage = data.get('usage', {})
                actual_tokens = usage.get('total_tokens', 0)
                break
    except Exception as e:
        print(f"[WARN] Failed to extract tokens from stream: {e}")
    
    # 如果无法提取，使用估算
    if actual_tokens == 0:
        input_text = json.dumps(payload.get('messages', []))
        output_estimate = len(full_content) // 4
        actual_tokens = len(input_text) // 4 + output_estimate
    
    # 扣除配额并记录日志
    if actual_tokens > 0:
        deduct_quota(user_id, actual_tokens)
    log_request(user_id, provider['id'], target_url, resp.status_code, actual_tokens)
    
    def generate():
        yield full_content
    
    return Response(generate(), content_type=resp.headers.get('content-type', 'application/json'))


def handle_normal_response(resp, payload, user_id, provider, target_url):
    """处理非流式响应"""
    response_content = resp.content
    actual_tokens = 0
    
    try:
        response_json = json.loads(response_content)
        usage = response_json.get('usage', {})
        actual_tokens = usage.get('total_tokens', 0)
        if actual_tokens == 0:
            actual_tokens = usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)
    except Exception as e:
        print(f"[WARN] Failed to parse response for token usage: {e}")
    
    # 如果无法获取真实 token，使用估算
    if actual_tokens == 0:
        input_text = json.dumps(payload.get('messages', []))
        actual_tokens = len(input_text) // 4 + len(response_content) // 4
    
    # 扣除配额并记录日志
    if actual_tokens > 0:
        deduct_quota(user_id, actual_tokens)
    log_request(user_id, provider['id'], target_url, resp.status_code, actual_tokens)
    
    print(f"[PROXY] Request completed: {actual_tokens} tokens used")
    return Response(response_content, status=resp.status_code, 
                   content_type=resp.headers.get('content-type', 'application/json'))
