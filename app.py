"""
AIPG - API Proxy Gateway
启动入口

项目结构:
- server/           # 主服务目录
  - routes/         # 路由模块
    - auth.py       # 认证路由
    - admin.py      # 管理员路由
    - user.py       # 用户路由
    - playground.py # Playground路由
    - api.py        # API代理路由
  - services/       # 业务逻辑服务
    - proxy_service.py    # 代理请求处理
    - provider_service.py # 提供商管理
  - utils/          # 工具模块
    - config.py     # 配置管理
    - model_matcher.py # 模型匹配
  - app.py          # 主应用入口
- core/             # 核心模块（数据库、限流器等）
- config/           # 配置文件
- templates/        # HTML模板
"""
from server.app import run_app

if __name__ == '__main__':
    run_app()
