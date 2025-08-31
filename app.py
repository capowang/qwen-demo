from openai import OpenAI
from flask import Flask, request, jsonify, render_template_string, Response
import json
import os

app = Flask(__name__)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-9106aa79fbe8424595078b861140c00d"),  
    base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
)

# 存储对话历史
conversation_history = []

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "HTML file not found", 404

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400

        # 构建消息历史
        messages = [
            {
                "role": "system",
                "content": "你是一位熟悉《非暴力沟通》的老师，请结合书中的内容和实例，耐心讲解，风格亲切。"
            }
        ]
        
        # 添加对话历史
        for msg in conversation_history[-10:]:  # 只保留最近10条消息
            messages.append(msg)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})
        
        def generate():
            try:
                # 调用通义千问 API，启用流式输出
                response = client.chat.completions.create(
                    model="qwen-max",
                    messages=messages,
                    tools=[
                        {
                            "type": "retrieval",
                            "function": {
                                "name": "knowledge_search",
                                "description": "搜索非暴力沟通相关的知识库内容"
                            },
                            "retrieval": {
                                "knowledge_id": "gyy4cpk7df"
                            }
                        }
                    ],
                    stream=True,  # 启用流式输出
                )
                
                full_response = ""
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        # 发送每个字符到前端
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
                # 保存对话历史
                conversation_history.append({"role": "user", "content": user_message})
                conversation_history.append({"role": "assistant", "content": full_response})
                
                # 发送完成信号
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                
            except Exception as e:
                print(f"Error in stream: {e}")
                yield f"data: {json.dumps({'error': '服务器错误', 'done': True})}\n\n"
        
        return Response(generate(), mimetype='text/plain')
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': '服务器内部错误'}), 500

# Vercel 需要这个
app.debug = False

if __name__ == '__main__':
    print("启动非暴力沟通 AI 助手...")
    print("访问地址: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080) 