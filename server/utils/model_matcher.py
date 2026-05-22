"""
模型匹配工具模块
处理模型名称的通配符匹配
"""
import fnmatch


def match_model_pattern(model_name, pattern):
    """
    匹配模型名称是否符合通配符模式
    支持 * 通配符，如:
    - "gpt-*" 匹配 "gpt-4", "gpt-3.5-turbo"
    - "gemma*" 匹配 "gemma4:26b", "gemma2:9b"
    - "claude-*" 匹配 "claude-3-opus", "claude-3-sonnet"
    """
    if not pattern:
        return False
    # 使用 fnmatch 进行 Unix shell 风格的通配符匹配
    return fnmatch.fnmatch(model_name.lower(), pattern.lower())
