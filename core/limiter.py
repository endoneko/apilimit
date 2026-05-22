import time
from collections import defaultdict
import threading

# 基于内存的简易令牌桶/滑动窗口替代演示 (Token Bucket / Sliding Window)
# 生产环境中由于多进程/分布式的诉求，强烈建议切换至Redis+Lua脚本

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, user_id, max_rpm):
        # 0或者无需限制则直接放行
        if max_rpm <= 0: return True 
        
        now = time.time()
        with self.lock:
            # 清理 60 秒之前的请求记录（实现 1分钟 滑动窗口）
            reqs = self.requests[user_id]
            reqs = [t for t in reqs if now - t < 60]
            self.requests[user_id] = reqs
            
            # 判断当前分钟时间窗口内，是否超出了 RPM 限制
            if len(reqs) >= max_rpm:
                return False
            
            self.requests[user_id].append(now)
            return True

# 声明全局单例供主应用调用
limiter = RateLimiter()