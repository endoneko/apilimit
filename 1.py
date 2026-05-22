import requests
import time

url = "https://mappable-homoiothermal-nevada.ngrok-free.dev/v1/chat/completions"
headers = {
    "Authorization": "Bearer aip_endonekouser_e0beca5d",
    "Content-Type": "application/json"
}
data = {
    "model": "gemma4:26b",
    "messages": [{"role": "user", "content": "你好，测试连接"}]
}

# 添加重试机制
max_retries = 3
for i in range(max_retries):
    try:
        print(f"正在尝试连接... (第 {i+1} 次)")
        response = requests.post(url, headers=headers, json=data, timeout=1000)
        print("连接成功！")
        print(response.json())
        break
    except requests.exceptions.ConnectionError as e:
        print(f"连接失败: {e}")
        if i < max_retries - 1:
            print("2秒后重试...")
            time.sleep(2)
        else:
            print("\n请确保 Flask 服务已启动：")
            print("1. 打开终端")
            print("2. 运行: python app.py")
            print("3. 等待服务启动后，再次运行此脚本")
    except Exception as e:
        print(f"发生错误: {e}")
        break
