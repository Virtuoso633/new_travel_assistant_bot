import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './Chat.css'; // We will create this CSS file next

const Chat = () => {
  // State for messages, input, and loading status
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null); // Ref to scroll to the bottom

  // Function to automatically scroll to the latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // useEffect hook to scroll whenever messages update
  useEffect(scrollToBottom, [messages]);

  // Function to handle sending messages to Rasa (either typed or from button payload)
  const handleRasaRequest = async (messageText) => {
    if (!messageText) return;

    setIsLoading(true);

    try {
      // Use environment variable for the server URL, with a fallback for local dev
      const rasaServerUrl = process.env.REACT_APP_RASA_SERVER_URL || 'http://localhost:5005';
      // Send message to Rasa endpoint
      const response = await axios.post(`${rasaServerUrl}/webhooks/rest/webhook`, {
        sender: 'user', // A unique ID for the user
        message: messageText // This is what's sent to Rasa (typed text or payload)
      });

      // Add bot responses to the UI
      const newBotMessages = [];
      response.data.forEach(msg => {
        if (msg.text) {
          newBotMessages.push({ text: msg.text, sender: 'bot' });
        }
        if (msg.buttons && msg.buttons.length > 0) {
          // Add a special message type for buttons
          newBotMessages.push({ type: 'buttons', buttons: msg.buttons, sender: 'bot' });
        }
      });
      setMessages(prev => [...prev, ...newBotMessages]);

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = { text: 'Sorry, I am having trouble connecting. Please try again later.', sender: 'bot' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to handle form submission for typed messages
  const handleFormSubmit = (e) => {
    e.preventDefault();
    const message = inputMessage.trim();
    if (!message) return;

    // Add user message to the UI immediately
    const newUserMessage = { text: message, sender: 'user' };
    setMessages(prev => [...prev, newUserMessage]);
    setInputMessage(''); // Clear input after sending

    handleRasaRequest(message);
  };

  // Function to handle button clicks
  const handleButtonClick = (title, payload) => {
    // Add the button's title as a user message for context
    const userClickedMessage = { text: title, sender: 'user' };
    setMessages(prev => [...prev, userClickedMessage]);
    
    // Send the payload to Rasa
    handleRasaRequest(payload);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h3>Travel Assistant</h3>
        <span>Online</span>
      </div>
      <div className="chat-messages">
        {messages.map((msg, index) => {
          if (msg.type === 'buttons') {
            return (
              <div key={index} className={`message bot button-container`}>
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
            );
          }
          return (
            <div key={index} className={`message ${msg.sender}`}>
              {msg.text}
            </div>
          );
        })}
        {isLoading && (
          <div className="message bot">
            <div className="typing-indicator">
              <span></span><span></span><span></span>
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
        <button type="submit" disabled={isLoading}>Send</button>
      </form>
    </div>
  );
};

export default Chat;