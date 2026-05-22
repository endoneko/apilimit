"""
AIPG - API Proxy Gateway
主应用入口
"""
import os
import sys
import time
import platform
from datetime import datetime
from flask import Flask, redirect, url_for, session, request, g

from core.db import init_db, get_stats as get_db_stats
from core.ngrok_tunnels import start_tunnel
from server.utils.config import load_config

# 导入路由
from server.routes.auth import auth_bp
from server.routes.admin import admin_bp
from server.routes.user import user_bp
from server.routes.playground import playground_bp
from server.routes.api import api_bp


# 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_banner():
    """打印启动横幅"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
    █████╗ ██╗██████╗  ██████╗ 
   ██╔══██╗██║██╔══██╗██╔════╝ 
   ███████║██║██████╔╝██║  ███╗
   ██╔══██║██║██╔═══╝ ██║   ██║
   ██║  ██║██║██║     ╚██████╔╝
   ╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝ 
{Colors.ENDC}
{Colors.GREEN}   API Proxy Gateway - 智能API代理网关{Colors.ENDC}
{Colors.BLUE}   Version: 2.0.0 | Build: 2024.05.22{Colors.ENDC}
    """
    print(banner)


def print_system_info():
    """打印系统信息"""
    print(f"\n{Colors.BOLD}📊 系统信息:{Colors.ENDC}")
    print(f"   {Colors.CYAN}├─ 操作系统:{Colors.ENDC} {platform.system()} {platform.release()}")
    print(f"   {Colors.CYAN}├─ Python版本:{Colors.ENDC} {platform.python_version()}")
    print(f"   {Colors.CYAN}├─ 工作目录:{Colors.ENDC} {os.getcwd()}")
    print(f"   {Colors.CYAN}└─ 启动时间:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def print_config_info(routes_config, providers_config):
    """打印配置信息"""
    print(f"\n{Colors.BOLD}⚙️  配置信息:{Colors.ENDC}")
    # 提供商信息
    providers = providers_config.get('providers', [])
    enabled_providers = [p for p in providers if p.get('enabled', True)]
    print(f"   {Colors.CYAN}├─ 提供商数量:{Colors.ENDC} {len(enabled_providers)}/{len(providers)} (启用/总数)")
    
    for provider in enabled_providers:
        models_count = len(provider.get('models', []))
        status = f"{Colors.GREEN}●{Colors.ENDC}" if provider.get('enabled', True) else f"{Colors.FAIL}●{Colors.ENDC}"
        print(f"   {Colors.CYAN}│  ├─{Colors.ENDC} {status} {provider['name']} ({models_count} 模型)")
    
    # 路由信息
    routes = routes_config.get('routes', [])
    print(f"   {Colors.CYAN}└─ 路由规则:{Colors.ENDC} {len(routes)} 条")


def print_module_info():
    """打印模块加载信息"""
    print(f"\n{Colors.BOLD}🔌 模块加载:{Colors.ENDC}")
    modules = [
        ("认证模块", "auth_bp", True),
        ("管理员模块", "admin_bp", True),
        ("用户模块", "user_bp", True),
        ("Playground模块", "playground_bp", True),
        ("API代理模块", "api_bp", True),
    ]
    for name, _, loaded in modules:
        status = f"{Colors.GREEN}✓{Colors.ENDC}" if loaded else f"{Colors.FAIL}✗{Colors.ENDC}"
        print(f"   {Colors.CYAN}{status} {name}{Colors.ENDC}")


def create_app():
    """创建 Flask 应用实例"""
    # 获取项目根目录（server 的父目录）
    root_dir = os.path.dirname(os.path.dirname(__file__))
    
    app = Flask(__name__, 
                template_folder=os.path.join(root_dir, 'templates'),
                static_folder=os.path.join(root_dir, 'static'))
    app.secret_key = 'super_secret_key_change_in_production'
    
    # 禁用 Flask 默认的请求日志
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # 请求前钩子 - 记录请求信息
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    # 请求后钩子 - 记录响应信息
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            elapsed = (time.time() - g.start_time) * 1000
            status_color = Colors.GREEN if response.status_code < 400 else Colors.WARNING if response.status_code < 500 else Colors.FAIL
            print(f"{Colors.CYAN}[{datetime.now().strftime('%H:%M:%S')}]{Colors.ENDC} "
                  f"{Colors.BOLD}←{Colors.ENDC} {request.method} {request.path} "
                  f"{status_color}{response.status_code}{Colors.ENDC} "
                  f"({elapsed:.1f}ms)")
        return response
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(playground_bp)
    app.register_blueprint(api_bp)
    
    # 首页路由
    @app.route('/', methods=['GET'])
    def index():
        if 'username' in session:
            if session.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.dashboard'))
        return redirect(url_for('auth.login_page'))
    
    # 健康检查接口
    @app.route('/health', methods=['GET'])
    def health_check():
        stats = get_db_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "stats": stats
        }
    
    return app


def run_app():
    """运行应用"""
    # 检查是否是 Flask 重载进程（避免重复输出）
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # 这是重载后的子进程，跳过启动输出
        routes_config = load_config('routes.json')
        local_cfg = routes_config.get('local_config', {})
        host = local_cfg.get('host', '0.0.0.0')
        port = local_cfg.get('port', 8888)
        
        app = create_app()
        app.run(host=host, port=port, debug=local_cfg.get('debug', False ))
        return
    
    # 打印启动横幅（只在主进程执行）
    print_banner()
    
    # 1. 读取配置
    print(f"\n{Colors.BOLD}📂 加载配置文件...{Colors.ENDC}")
    routes_config = load_config('routes.json')
    providers_config = load_config('providers.json')
    print(f"   {Colors.GREEN}✓ 配置加载完成{Colors.ENDC}")
    
    # 2. 打印系统信息
    print_system_info()
    
    # 3. 打印配置信息
    print_config_info(routes_config, providers_config)
    
    # 4. 初始化数据库
    print(f"\n{Colors.BOLD}💾 初始化数据库...{Colors.ENDC}")
    init_db()
    stats = get_db_stats()
    print(f"   {Colors.GREEN}✓ 数据库初始化完成{Colors.ENDC}")
    print(f"   {Colors.CYAN}└─ 统计:{Colors.ENDC} {stats.get('total_requests', 0)} 请求, "
          f"{stats.get('total_tokens', 0)} Tokens")
    
    # 5. 打印模块信息
    print_module_info()
    
    # 6. 启动 Ngrok Tunnel
    print(f"\n{Colors.BOLD}🌐 启动 Ngrok 隧道...{Colors.ENDC}")
    local_cfg = routes_config.get('local_config', {})
    port = local_cfg.get('port', 8888)
    start_tunnel(port)
    
    # 7. 创建并运行应用
    print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}{Colors.BOLD}  🚀 AIPG 服务启动成功！{Colors.ENDC}")
    print(f"{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    host = local_cfg.get('host', '0.0.0.0')
    print(f"\n{Colors.CYAN}   本地访问:{Colors.ENDC} http://本地IP:{port}")
    print(f"{Colors.CYAN}   健康检查:{Colors.ENDC} http://本地IP:{port}/health")
    print(f"{Colors.CYAN}   API端点:{Colors.ENDC} http://本地IP:{port}/v1/chat/completions")
    
    print(f"\n{Colors.WARNING}   按 Ctrl+C 停止服务{Colors.ENDC}\n")
    
    app = create_app()
    app.run(host=host, port=port, debug=local_cfg.get('debug', True))


if __name__ == '__main__':
    try:
        run_app()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️  服务已手动停止{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ 启动失败: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
