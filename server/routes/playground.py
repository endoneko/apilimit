"""
Playground 路由模块
处理 API 调试中心
"""
from flask import Blueprint, render_template, redirect, url_for, session

from core.db import get_user_by_username, get_user_api_keys
from server.services.provider_service import collect_all_models

playground_bp = Blueprint('playground', __name__)


@playground_bp.route('/playground', methods=['GET'])
def playground_page():
    """Playground 页面"""
    if session.get('role') not in ['admin', 'user']:
        return redirect(url_for('auth.login_page'))
    
    username = session.get('username')
    user = get_user_by_username(username)
    keys = get_user_api_keys(user['id'])
    
    # 获取所有可用模型
    models = collect_all_models()
    
    return render_template('playground.html', user=user, api_keys=keys, models=models)
