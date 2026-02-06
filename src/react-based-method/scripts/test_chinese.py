import requests
import json

url = "http://127.0.0.1:1025/v1/chat/completions"

# 正确构建请求数据，requests库会自动处理UTF-8编码
payload = {
    "messages": [
        {"role": "user", "content": "你好，请用中文介绍一下你自己。"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
}

# 明确指定请求头，确保服务器知道我们发送的是UTF-8
headers = {
    'Content-Type': 'application/json; charset=utf-8',
}

try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print(f"状态码: {response.status_code}")
    print("响应头:", response.headers.get('content-type', '未知'))
    
    # 尝试以多种方式解码响应内容，确保看到原始错误
    if response.status_code != 200:
        print("\n⚠️ 请求失败，原始响应内容如下：")
        # 先尝试UTF-8，失败则用错误替代字符显示
        try:
            print(response.text)
        except UnicodeDecodeError:
            print(response.content)  # 打印原始字节
    else:
        result = response.json()
        print("\n✅ 成功！AI回复：")
        print(result['choices'][0]['message']['content'])

except requests.exceptions.ConnectionError:
    print("❌ 无法连接到服务器，请确认服务器是否运行在端口 1234。")
except requests.exceptions.Timeout:
    print("❌ 请求超时。")
except Exception as e:
    print(f"❌ 发生未知错误: {e}")