import React, { useState, useEffect, useRef } from 'react';
import './ChatWidget.css';

const ChatWidget = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { sender: 'ai', text: 'Hello! How can I help you explore your memories today?' }
    ]);
    const [inputText, setInputText] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const toggleChat = () => {
        setIsOpen(!isOpen);
    };

    const handleInputChange = (e) => {
        setInputText(e.target.value);
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (inputText.trim() === '') return;

        const userMessage = { sender: 'user', text: inputText.trim() };
        setMessages(prevMessages => [...prevMessages, userMessage]);
        setInputText('');

        // Simulate AI response / API call to n8n workflow (query_chat_interface.json)
        // TODO: Replace with actual API call
        setMessages(prevMessages => [...prevMessages, {sender: 'ai', text: 'Thinking...'}]); // Intermediate thinking message

        try {
            const n8nBaseUrl = process.env.REACT_APP_N8N_BASE_URL || '';
            const response = await fetch(`${n8nBaseUrl}/webhook-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMessage.text, user_id: "lifeboard_user" })
            });

            // Remove "Thinking..." message
            setMessages(prevMessages => prevMessages.filter(msg => msg.text !== 'Thinking...'));

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const aiResponseData = await response.json();

            let aiTextResponse;
            if (aiResponseData.status === "success" && aiResponseData.reply) {
                aiTextResponse = aiResponseData.reply;
            } else if (aiResponseData.results && Array.isArray(aiResponseData.results)) { // Fallback if LLM part failed but search worked
                aiTextResponse = "I found some memories that might be relevant: \n" + aiResponseData.results.map(r => JSON.stringify(r.payload || r.text)).join("\n");
            } else {
                aiTextResponse = "Sorry, I had trouble processing that. " + (aiResponseData.message || "");
            }
            const aiMessage = { sender: 'ai', text: aiTextResponse };
            setMessages(prevMessages => [...prevMessages, aiMessage]);

        } catch (error) {
            console.error("Failed to send message or get AI response:", error);
             // Remove "Thinking..." message if it's still there on error
            setMessages(prevMessages => prevMessages.filter(msg => msg.text !== 'Thinking...'));
            const errorMessage = { sender: 'ai', text: "Sorry, I couldn't connect to the AI. Please try again." };
            setMessages(prevMessages => [...prevMessages, errorMessage]);
        }
    };

    return (
        <div className="chat-widget-container">
            {isOpen && (
                <div className="chat-window">
                    <div className="chat-header">
                        Lifeboard AI Assistant
                        <button onClick={toggleChat} className="close-chat-button">✕</button>
                    </div>
                    <div className="chat-messages">
                        {messages.map((msg, index) => (
                            <div key={index} className={`message ${msg.sender}`}>
                                {msg.text}
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                    <form className="chat-input-form" onSubmit={handleSendMessage}>
                        <input
                            type="text"
                            value={inputText}
                            onChange={handleInputChange}
                            placeholder="Ask about your life..."
                        />
                        <button type="submit">Send</button>
                    </form>
                </div>
            )}
            <button onClick={toggleChat} className="chat-toggle-button">
                {isOpen ? 'Close Chat' : 'Chat with Life AI'}
            </button>
        </div>
    );
};

export default ChatWidget;
