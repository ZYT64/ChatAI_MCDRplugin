# -*- coding: utf-8 -*-
"""
MCDR Plugin for DeepSeek AI Chat
当玩家输入"!!ds <聊天内容>"时，通过DeepSeek API获取回复并单独发送给该玩家
"""

from mcdreforged.api.all import *
import json
import requests
import threading

# 插件信息
PLUGIN_METADATA = {
    'id': 'deepseek_chat',
    'version': '1.0.0',
    'name': 'DeepSeek Chat Plugin',
    'description': 'A plugin to interact with DeepSeek API',
    'author': 'MCDR User',
    'dependencies': {
        'mcdreforged': '>=2.0.0',
    }
}

# 配置信息
CONFIG_FILE = 'config/deepseek_config.json'
default_config = {
    'api_key': 'YOUR_API_KEY_HERE',
    'api_url': 'https://api.deepseek.com/v1/chat/completions',
    'model': 'deepseek-chat',
    'max_tokens': 1000,
    'temperature': 0.7
}

config = default_config

def read_config():
    """读取配置文件"""
    global config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        # 如果配置文件不存在，创建默认配置
        import os
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        config = default_config
    except Exception as e:
        print(f'读取配置文件失败: {e}')

def send_deepseek_request(prompt):
    """发送请求到DeepSeek API"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {config["api_key"]}'
    }
    
    data = {
        'model': config['model'],
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': config.get('max_tokens', 1000),
        'temperature': config.get('temperature', 0.7)
    }
    
    try:
        response = requests.post(config['api_url'], headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content'].strip()
        else:
            return 'API返回格式错误'
    except requests.exceptions.RequestException as e:
        return f'请求API时发生错误: {str(e)}'
    except Exception as e:
        return f'发生未知错误: {str(e)}'

def handle_deepseek_request_for_player(server: ServerInterface, source, message):
    """处理玩家的DeepSeek请求"""
    # 检查命令源是否是玩家
    if not source.is_player:
        source.reply('§c此命令只能由玩家执行')
        return
    
    player = source.player
    if not config['api_key'] or config['api_key'] == 'your_deepseek_api_key_here':
        server.tell(player, '§c[DeepSeek] 错误: 未配置API密钥，请在config/deepseek_config.json中设置')
        return
    
    def request_thread():
        server.tell(player, '§e[DeepSeek] 正在处理您的请求...')
        try:
            result = send_deepseek_request(message)
            if result.startswith('请求API时发生错误') or result.startswith('发生未知错误'):
                server.tell(player, f'§c[DeepSeek] {result}')
            else:
                server.tell(player, f'§b[DeepSeek] {result}')
        except Exception as e:
            server.tell(player, f'§c[DeepSeek] 处理请求时发生错误: {str(e)}')
    
    # 在新线程中处理API请求，避免阻塞服务器
    thread = threading.Thread(target=request_thread)
    thread.daemon = True  # 设置为守护线程
    thread.start()

def on_load(server: ServerInterface, old):
    """插件加载时的初始化"""
    read_config()
    server.logger.info('DeepSeek Chat插件已加载')
    
    # 注册命令
    server.register_command(
        Literal('!!ds').
        runs(lambda src, ctx: handle_help(src)).
        then(
            GreedyText('message').
            runs(lambda src, ctx: handle_deepseek_request_for_player(server, src, ctx['message']))
        )
    )
    
    server.logger.info('DeepSeek Chat命令已注册: !!ds <聊天内容>')

def handle_help(source: CommandSource):
    """显示帮助信息"""
    help_message = '''
§b--------- DeepSeek AI 聊天插件 ---------
§e!!ds <消息内容> §f- 向DeepSeek AI发送消息并获取回复
§b--------------------------------
    '''.strip()
    
    if source.is_player:
        source.reply(help_message)
    else:
        source.reply('DeepSeek Chat Plugin - 命令: !!ds <聊天内容>')

def on_server_start(server: ServerInterface):
    """服务器启动时"""
    server.logger.info('DeepSeek Chat插件已就绪')

def on_info(server: ServerInterface, info: Info):
    """处理服务器信息"""
    if info.content.startswith('!!ds ') and info.is_player:
        # 阻止命令在服务器日志中显示完整消息
        pass