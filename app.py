from flask import Flask, request, jsonify
from flask_cors import CORS
from automated_response_bot import AutoResponseBot

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 创建机器人实例
bot = AutoResponseBot()

@app.route('/api/query', methods=['POST'])
def handle_query():
    try:
        # 1. 获取用户输入
        user_input = request.json.get('message', '')
        
        # 2. 使用机器人处理整个流程（AI处理->提取SKU->查询->返回结果）
        result = bot.handle_complete_query(user_input)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 