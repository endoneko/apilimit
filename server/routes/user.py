"""
用户路由模块
处理普通用户相关的功能
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session

from core.db import (
    get_user_by_username, get_user_api_keys, get_user_logs,
    generate_api_key
)
from server.services.provider_service import get_all_providers

user_bp = Blueprint('user', __name__, url_prefix='/user')


def require_user():
    """检查是否已登录"""
    if session.get('role') not in ['admin', 'user']:
        return redirect(url_for('auth.login_page'))
    return None


@user_bp.route('', methods=['GET'])
def dashboard():
    """用户仪表盘"""
    check = require_user()
    if check:
        return check
    
    username = session.get('username')
    user = get_user_by_username(username)
    if not user:
        return "User not found", 404
    
    keys = get_user_api_keys(user['id'])
    logs = get_user_logs(user['id'])
    providers = get_all_providers()
    
    # 格式化时间戳
    for log in logs:
        log['time_str'] = datetime.fromtimestamp(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('user.html', user=user, api_keys=keys, logs=logs, providers=providers)


@user_bp.route('/apikey/generate', methods=['POST'])
def generate_apikey():
    """生成API密钥"""
    check = require_user()
    if check:
        return check
    
    if 'user_id' not in session:
        return "Unauthorized", 403
    
    generate_api_key(session['user_id'], session['username'])
    return redirect(url_for('user.dashboard'))
