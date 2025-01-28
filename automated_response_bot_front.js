import React, { useState } from 'react';
import './AutomatedResponseBot.css';

function AutomatedResponseBot() {
    const [userInput, setUserInput] = useState('');
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!userInput.trim()) return;

        // 添加用户消息到聊天记录
        setMessages(prev => [...prev, { 
            type: 'user', 
            content: userInput 
        }]);
        setIsLoading(true);

        try {
            // 调用后端API
            const response = await fetch('http://localhost:5000/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: userInput })
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // 添加AI理解和机器人响应到聊天记录
            setMessages(prev => [
                ...prev,
                { 
                    type: 'ai-understanding', 
                    content: data.ai_understanding 
                },
                { 
                    type: 'bot', 
                    content: data.response 
                }
            ]);
        } catch (error) {
            console.error('Error:', error);
            setMessages(prev => [...prev, { 
                type: 'error', 
                content: error.message || '抱歉，发生错误，请稍后重试。' 
            }]);
        }

        setIsLoading(false);
        setUserInput('');
    };

    return (
        <div className="chat-container">
            <div className="chat-header">
                <h2>仓库查询助手</h2>
            </div>
            
            <div className="chat-messages">
                {messages.map((message, index) => (
                    <div key={index} className={`message ${message.type}`}>
                        {message.type === 'user' && (
                            <>
                                <strong>您：</strong>
                                <div className="message-content">{message.content}</div>
                            </>
                        )}
                        {message.type === 'ai-understanding' && (
                            <>
                                <em>AI理解为：</em>
                                <div className="message-content">{message.content}</div>
                            </>
                        )}
                        {message.type === 'bot' && (
                            <>
                                <strong>助手：</strong>
                                <div className="message-content">
                                    {message.content.split('\n').map((line, i) => (
                                        <div key={i}>{line}</div>
                                    ))}
                                </div>
                            </>
                        )}
                        {message.type === 'error' && (
                            <div className="message-content error-message">
                                {message.content}
                            </div>
                        )}
                    </div>
                ))}
                {isLoading && (
                    <div className="loading">
                        <div className="loading-spinner"></div>
                        <div>正在处理您的请求...</div>
                    </div>
                )}
            </div>

            <form onSubmit={handleSubmit} className="chat-input-form">
                <input
                    type="text"
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    placeholder="请输入您的问题，例如：查询 MH-1211-42 的库存"
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading}>
                    {isLoading ? '处理中...' : '发送'}
                </button>
            </form>
        </div>
    );
}

export default AutomatedResponseBot;