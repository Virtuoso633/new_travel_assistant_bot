// ------------------------------------
// Chat.js (Modern Design Version with Session Management)
// ------------------------------------
import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './Chat.css';

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    // Generate a unique session ID when the component is first mounted
    const [sessionId] = useState(() => 'user_' + Math.random().toString(36).substring(2, 15));
    
    // Use environment variable with fallback
    // const rasaServerUrl = process.env.REACT_APP_RASA_SERVER_URL || 'http://localhost:5005';
    //const rasaServerUrl = 'http://64.227.156.174:5005';
    const rasaServerUrl = 'http://localhost:5005';
    
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    // Focus input after each message
    useEffect(() => {
        inputRef.current?.focus();
    }, [messages]);

    // Reset conversation function
    const resetConversation = useCallback(async () => {
        setMessages([]);
        setIsLoading(true);
        try {
            // First send a reset intent to clear the server-side context
            await axios.post(
                `${rasaServerUrl}/webhooks/rest/webhook`,
                {
                    sender: sessionId,
                    message: "/restart"
                }
            );
            
            // Then send the greet message
            const response = await axios.post(
                `${rasaServerUrl}/webhooks/rest/webhook`,
                {
                    sender: sessionId,
                    message: "/greet"
                }
            );

            if (response.data && response.data.length > 0) {
                const botMessages = response.data.map(msg => ({
                    text: msg.text || "",
                    sender: 'bot',
                    timestamp: new Date().toISOString()
                }));
                
                setMessages(botMessages);
            }
        } catch (error) {
            console.error('Error resetting conversation:', error);
            setMessages([{
                text: "Sorry, I'm having trouble connecting right now. Please check the server status and your network connection.",
                sender: 'bot',
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
        }
    }, [rasaServerUrl, sessionId]);


    const handleRasaRequest = useCallback(async (messageText) => {
        if (!messageText) return;

        setIsLoading(true);

        try {
            const response = await axios.post(
                `${rasaServerUrl}/webhooks/rest/webhook`,
                {
                    sender: sessionId, // Use the unique session ID
                    message: messageText
                }
            );

            if (response.data && response.data.length > 0) {
                // Add a small delay between messages for natural conversation feel
                const messages = response.data;
                
                // Process messages one by one with delay
                for (let i = 0; i < messages.length; i++) {
                    const msg = messages[i];
                    
                    // Artificial delay for more natural conversation
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    const newBotMessage = {
                        text: msg.text || "",
                        sender: 'bot',
                        timestamp: new Date().toISOString()
                    };
                    
                    setMessages(prev => [...prev, newBotMessage]);
                }
            } else {
                // Handle empty response - show fallback message
                setMessages(prev => [...prev, { 
                    text: "I'm not sure how to respond to that. Try asking about weather or packing for a specific city.",
                    sender: 'bot',
                    timestamp: new Date().toISOString()
                }]);
            }
        } catch (error) {
            console.error('Error connecting to Rasa server:', error);
            setMessages(prev => [...prev, { 
                text: "Sorry, I'm having trouble connecting right now. Please check the server status and your network connection.", 
                sender: 'bot',
                timestamp: new Date().toISOString()
            }]);
        } finally {
            setIsLoading(false);
        }
    }, [rasaServerUrl, sessionId]);

    useEffect(() => {
        resetConversation();
    }, [resetConversation]);

    useEffect(scrollToBottom, [messages]);

    const handleFormSubmit = (e) => {
        e.preventDefault();
        const message = inputMessage.trim();
        if (!message) return;

        setMessages(prev => [...prev, { 
            text: message, 
            sender: 'user',
            timestamp: new Date().toISOString()
        }]);
        setInputMessage('');
        handleRasaRequest(message);
    };

    return (
        <div className="chat-wrapper">
            <div className="chat-container">
                <div className="chat-header">
                    <div className="chat-header-info">
                        <h3>Travel Assistant</h3>
                        <div className="online-indicator">
                            <span className="online-dot"></span>
                            <span className="online-text">Online</span>
                        </div>
                    </div>
                    <div className="chat-header-actions">
                        <button 
                            className="reset-btn" 
                            aria-label="Reset Conversation"
                            onClick={resetConversation}
                            disabled={isLoading}
                        >
                            <span className="reset-icon">↻</span>
                        </button>
                        <button className="minimize-btn" aria-label="Minimize">
                            <span className="minimize-icon">—</span>
                        </button>
                    </div>
                </div>
                
                <div className="chat-messages">
                    <div className="message-day-divider">
                        <span>Today</span>
                    </div>
                    
                    {messages.map((msg, index) => (
                        <div key={index} className={`message-wrapper ${msg.sender}`}>
                            {msg.sender === 'bot' && (
                                <div className="avatar bot-avatar">
                                    <span>🧳</span>
                                </div>
                            )}
                            <div className={`message ${msg.sender}`}>
                                <div 
                                    className="message-content"
                                    dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br />') }} 
                                />
                                <div className="message-time">
                                    {new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                </div>
                            </div>
                            {msg.sender === 'user' && (
                                <div className="avatar user-avatar">
                                    <span>👤</span>
                                </div>
                            )}
                        </div>
                    ))}
                    
                    {isLoading && (
                        <div className="message-wrapper bot">
                            <div className="avatar bot-avatar">
                                <span>🧳</span>
                            </div>
                            <div className="message bot typing">
                                <div className="typing-indicator">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                
                <div className="chat-footer">
                    <form className="chat-input-form" onSubmit={handleFormSubmit}>
                        <input
                            ref={inputRef}
                            type="text"
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            placeholder="Type your message here..."
                            disabled={isLoading}
                        />
                        <button type="submit" disabled={isLoading} className="send-button">
                            <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </form>
                    <div className="powered-by">
                        Powered by AI Travel Assistant
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Chat;