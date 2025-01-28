from inventory_search import get_inventory_info
import re
from datetime import datetime
import logging
from openai import OpenAI

class AutoResponseBot:
    def __init__(self):
        self.setup_logging()
        self.setup_ai()
        self.patterns = {
            'sku_pattern': r'[A-Za-z0-9-]+',
            'quantity_pattern': r'\d+',
            'location_pattern': r'[A-Z0-9#_-]+'
        }
        
    def setup_ai(self):
        """设置AI客户端"""
        self.client = OpenAI(
            api_key="sk-799032b9f4ca411695d258d6992a432c", 
            base_url="https://api.deepseek.com"
        )

    def process_with_ai(self, user_message):
        """使用AI处理用户消息"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": """你是一个仓库助手，负责理解用户的查询意图。
                    请将用户的自然语言查询转换为标准格式：
                    - 如果是查询库存，转换为"请查询 [SKU] 的库存"
                    - 如果是查询位置，转换为"[SKU] 在哪个位置？"
                    - 如果是查询多个产品，转换为"查一下这些产品：[SKU1], [SKU2]"
                    只返回转换后的格式，不需要其他解释。"""},
                    {"role": "user", "content": user_message}
                ],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"AI processing error: {str(e)}")
            return user_message

    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            filename=f'bot_logs_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('AutoResponseBot')

    def get_inventory_status(self, sku_list):
        """直接使用inventory_search中的get_inventory_info函数"""
        try:
            # 直接调用 inventory_search.py 中的函数
            return get_inventory_info(sku_list)
        except Exception as e:
            self.logger.error(f"Error getting inventory info: {str(e)}")
            return None

    def extract_skus(self, message):
        """从消息中提取SKU"""
        # 查找所有可能的SKU
        skus = re.findall(self.patterns['sku_pattern'], message)
        # 过滤掉太短的匹配（可能是噪声）
        return [sku for sku in skus if len(sku) >= 4]

    def format_response(self, inventory_info):
        """格式化响应消息"""
        if not inventory_info:
            return "抱歉，未能获取库存信息。"

        response = []
        for item in inventory_info:
            sku_info = (
                f"商品编号: {item['id']}\n"
                f"库存数量: {item['final_amount']}\n"
                f"库存位置: \n{item['location_list']}"
            )
            response.append(sku_info)
        
        return "\n".join(response)

    def process_message(self, message):
        """处理客户消息"""
        try:
            # 记录收到的消息
            self.logger.info(f"Received message: {message}")

            # 提取SKU
            skus = self.extract_skus(message)
            if not skus:
                return "未能识别到有效的商品编号，请提供正确的SKU。"

            # 获取库存信息
            inventory_info = self.get_inventory_status(skus)
            if not inventory_info:
                return "抱歉，查询库存信息时出现错误。"

            # 格式化响应
            response = self.format_response(inventory_info)
            
            # 记录响应
            self.logger.info(f"Response generated for SKUs: {skus}")
            
            return response

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return "处理您的请求时出现错误，请稍后重试。"

    def handle_special_commands(self, message):
        """处理特殊命令"""
        commands = {
            '/help': '可用命令:\n- 直接输入SKU查询库存\n- /help 显示帮助信息',
            '/status': '系统正常运行中'
        }
        return commands.get(message.lower(), None)

    def handle_complete_query(self, user_input):
        """
        处理完整的查询流程：
        1. AI处理用户输入
        2. 提取SKU
        3. 查询库存
        4. 返回结果
        """
        try:
            # 1. AI处理用户输入，转换为标准格式
            processed_message = self.process_with_ai(user_input)
            
            # 2. 提取SKU
            skus = self.extract_skus(processed_message)
            if not skus:
                return {
                    'original_input': user_input,
                    'ai_understanding': processed_message,
                    'response': "未能识别到有效的商品编号，请提供正确的SKU。"
                }
            
            # 3. 查询库存信息
            inventory_info = self.get_inventory_status(skus)
            if not inventory_info:
                return {
                    'original_input': user_input,
                    'ai_understanding': processed_message,
                    'response': "抱歉，查询库存信息时出现错误。"
                }
            
            # 4. 格式化响应
            formatted_response = self.format_response(inventory_info)
            
            # 5. 记录日志
            self.logger.info(f"""
                User Input: {user_input}
                AI Understanding: {processed_message}
                SKUs Found: {skus}
                Response: {formatted_response}
            """)
            
            # 6. 返回完整结果
            return {
                'original_input': user_input,
                'ai_understanding': processed_message,
                'response': formatted_response
            }
            
        except Exception as e:
            self.logger.error(f"Error in handle_complete_query: {str(e)}")
            return {
                'original_input': user_input,
                'ai_understanding': None,
                'response': "处理您的请求时出现错误，请稍后重试。",
                'error': str(e)
            }

def main():
    bot = AutoResponseBot()
    
    while True:
        try:
            # 等待用户输入
            user_input = input("\n请输入您的问题（输入 'quit' 退出）: ")
            
            if user_input.lower() == 'quit':
                print("感谢使用，再见！")
                break
                
            # 首先用AI处理用户输入
            processed_message = bot.process_with_ai(user_input)
            print(f"理解为: {processed_message}")
            
            # 检查是否是特殊命令
            special_response = bot.handle_special_commands(processed_message)
            if special_response:
                print(f"机器人响应: {special_response}")
            else:
                response = bot.process_message(processed_message)
                print(f"机器人响应: {response}")
                
        except KeyboardInterrupt:
            print("\n程序已终止")
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()