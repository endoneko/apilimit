"""
管理员路由模块
处理管理员相关的所有功能
"""
from datetime import datetime
from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify

from core.db import (
    get_stats as get_db_stats, get_recent_logs, get_users,
    update_user_limits
)
from server.services.provider_service import add_provider, get_all_providers

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def require_admin():
    """检查是否为管理员"""
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login_page'))
    return None


@admin_bp.route('', methods=['GET'])
def dashboard():
    """管理员仪表盘"""
    check = require_admin()
    if check:
        return check
    
    stats = get_db_stats()
    users = get_users()
    logs = get_recent_logs()
    providers = get_all_providers()
    
    # 格式化时间戳
    for log in logs:
        log['time_str'] = datetime.fromtimestamp(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('admin.html', stats=stats, users=users, logs=logs, providers=providers)


@admin_bp.route('/provider/add', methods=['POST'])
def add_provider_route():
    """添加提供商"""
    check = require_admin()
    if check:
        return check
    
    name = request.form.get('name')
    base_url = request.form.get('base_url')
    api_key = request.form.get('api_key')
    models_str = request.form.get('models', '')
    
    add_provider(name, base_url, api_key, models_str)
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/user/update', methods=['POST'])
def save_user_limits_route():
    """更新用户限制"""
    check = require_admin()
    if check:
        return check
    
    user_id = request.form.get('user_id')
    quota = int(request.form.get('quota_total'))
    rpm = int(request.form.get('rpm'))
    tpm = int(request.form.get('tpm'))
    status = request.form.get('status')
    
    update_user_limits(user_id, quota, rpm, tpm, status)
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/stats', methods=['GET'])
def get_stats_view():
    """获取统计信息"""
    check = require_admin()
    if check:
        return check
    
    stats = get_db_stats()
    return jsonify({
        "status": "running",
        "database_stats": stats
    })


@admin_bp.route('/api/logs', methods=['GET'])
def api_logs():
    """获取日志"""
    check = require_admin()
    if check:
        return check
    
    logs = get_recent_logs()
    return jsonify({"logs": logs})


@admin_bp.route('/api/users', methods=['GET'])
def api_users():
    """获取用户列表"""
    check = require_admin()
    if check:
        return check
    
    users = get_users()
    return jsonify({"users": users})
