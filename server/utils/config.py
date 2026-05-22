"""
配置管理模块
处理所有配置文件的加载和保存
"""
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')


def load_config(filename):
    """加载配置文件"""
    filepath = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(filename, data):
    """保存配置文件"""
    filepath = os.path.join(CONFIG_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
