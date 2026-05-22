"""
API 路由模块
处理 OpenAI 兼容的 API 请求
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify

from core.db import check_api_key
from core.limiter import limiter
from server.services.proxy_service import forward_request

api_bp = Blueprint('api', __name__, url_prefix='/v1')


@api_bp.route('/user/quota', methods=['GET'])
def get_user_quota():
    """获取用户额度信息"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Unauthorized"}), 401
    
    api_key = auth_header.split(' ')[1]
    user = check_api_key(api_key)
    if not user:
        return jsonify({"error": "Invalid Key"}), 403
    
    return jsonify({
        "username": user['username'],
        "quota_total": user['quota_total'],
        "quota_used": user['quota_used'],
        "remaining": max(0, user['quota_total'] - user['quota_used']),
        "status": user['status']
    })


@api_bp.route('/<path:subpath>', methods=['GET', 'POST'])
def openai_proxy(subpath):
    """
    OpenAI 兼容的代理路由
    处理所有 /v1/* 请求
    """
    # 1. 鉴权
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({"error": "Unauthorized format"}), 401
    
    api_key = auth_header.split(' ')[1]
    user = check_api_key(api_key)
    
    if not user:
        return jsonify({"error": "Invalid API Key or Inactive"}), 403
    
    user_id = user['id']
    
    # 2. 高级安全拦截 (IP白名单与过期时间检查)
    client_ip = request.remote_addr
    if user['ip_whitelist']:
        whitelist = [ip.strip() for ip in user['ip_whitelist'].split(',')]
        if whitelist and client_ip not in whitelist:
            return jsonify({"error": f"IP {client_ip} not in whitelist"}), 403
    
    if user['expires_at']:
        try:
            exp_time = datetime.strptime(user['expires_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp_time:
                return jsonify({"error": "Account membership expired"}), 403
        except Exception:
            pass
    
    # 3. 配额与流控检查
    if user['role'] != 'admin':  # Admin 跳过速率限制
        if user['status'] != 'active':
            return jsonify({"error": "Account suspended or inactive"}), 403
        
        if user['quota_total'] > 0 and user['quota_used'] >= user['quota_total']:
            return jsonify({"error": "Quota Exceeded"}), 429
        
        if not limiter.is_allowed(user_id, user['rpm']):
            return jsonify({"error": "Rate limit exceeded (Too many requests per minute)"}), 429
    
    # 4. 获取请求体
    payload = request.json or {}
    
    # 5. 转发请求
    return forward_request(subpath, user, payload)
