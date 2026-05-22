"""
认证路由模块
处理登录、注册、登出等认证相关功能
"""
from flask import Blueprint, request, render_template, redirect, url_for, session

from core.db import get_user_by_username, create_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user_by_username(username)
        if user and user.get('password') == password:
            session['username'] = user['username']
            session['role'] = user['role']
            session['user_id'] = user['id']
            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
        return render_template('login.html', error="用户名或密码错误，请重试！")
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    """注册页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('register.html', error="用户名和密码不能为空！")
            
        success = create_user(username, password)
        if success:
            return render_template('login.html', error="注册成功！请登录。")
        else:
            return render_template('register.html', error="该用户名已存在，请换一个重试！")
            
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('auth.login_page'))
