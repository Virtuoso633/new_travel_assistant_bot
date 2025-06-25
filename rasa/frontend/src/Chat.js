
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './Chat.css';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const handleRasaRequest = async (messageText) => {
    if (!messageText) return;

    setIsLoading(true);

    try {
      const rasaServerUrl = process.env.REACT_APP_RASA_SERVER_URL || 'http://localhost:5005';
      const response = await axios.post(`${rasaServerUrl}/webhooks/rest/webhook`, {
        sender: 'user',
        message: messageText
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        withCredentials: false,
        timeout: 5000 // 5 second timeout
      });

      if (response.data && response.data.length > 0) {
        const newBotMessages = response.data.map(msg => ({
          text: msg.text,
          sender: 'bot',
          buttons: msg.buttons || []
        }));
        setMessages(prev => [...prev, ...newBotMessages]);
      } else {
        setMessages(prev => [...prev, { 
          text: "I'm not sure how to respond to that.", 
          sender: 'bot' 
        }]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { 
        text: "Sorry, I'm having trouble connecting right now. Please try again later.", 
        sender: 'bot' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    const message = inputMessage.trim();
    if (!message) return;

    setMessages(prev => [...prev, { text: message, sender: 'user' }]);
    setInputMessage('');
    handleRasaRequest(message);
  };

  const handleButtonClick = (title, payload) => {
    setMessages(prev => [...prev, { text: title, sender: 'user' }]);
    handleRasaRequest(payload);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h3>Travel Assistant</h3>
        <span>Online</span>
      </div>
      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {msg.text}
            {msg.buttons && msg.buttons.length > 0 && (
              <div className="button-container">
                {msg.buttons.map((button, btnIndex) => (
                  <button
                    key={btnIndex}
                    className="chat-button"
                    onClick={() => handleButtonClick(button.title, button.payload)}
                  >
                    {button.title}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message bot">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form className="chat-input-form" onSubmit={handleFormSubmit}>
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Type a message..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          Send
        </button>
      </form>
    </div>
  );
};

export default Chat;