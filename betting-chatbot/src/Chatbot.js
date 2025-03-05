import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import "./App.css";

const Chatbot = () => {
  const [chats, setChats] = useState([]); // Stores saved chat summaries
  const [currentMessages, setCurrentMessages] = useState([]); // Stores messages for current chat
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatEndRef = useRef(null);

  // Load chat history from local storage
  useEffect(() => {
    const savedChats = JSON.parse(localStorage.getItem("chatHistory")) || [];
    setChats(savedChats);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentMessages]);

  // Function to generate a chat title based on message analysis
  const generateChatTitle = (messages) => {
    if (messages.length === 0) return "New Chat";

    const keywords = messages
      .filter((msg) => msg.sender === "user")
      .map((msg) => msg.text)
      .join(" ")
      .toLowerCase();

    if (keywords.includes("nba") || keywords.includes("basketball")) return "NBA Betting Insights";
    if (keywords.includes("soccer") || keywords.includes("football")) return "Soccer Betting Strategies";
    if (keywords.includes("odds")) return "Odds Comparison & Analysis";
    if (keywords.includes("bet") || keywords.includes("gamble")) return "Betting Advice Session";
    return "General Chat";
  };

  const sendMessage = async () => {
    if (input.trim() === "") return;

    const userMessage = { text: input, sender: "user" };
    const updatedMessages = [...currentMessages, userMessage];

    setCurrentMessages(updatedMessages);

    try {
      const response = await axios.post("http://localhost:5000/chat", { message: input });
      const botMessage = { text: response.data.reply.replace(/\\n/g, "\n"), sender: "bot" }; // Ensure proper line breaks
      setCurrentMessages([...updatedMessages, botMessage]);
    } catch (error) {
      console.error("Error fetching response", error);
      setCurrentMessages([...updatedMessages, { text: "⚠️ Error: Couldn’t process your request.", sender: "bot" }]);
    }

    setInput("");
  };

  const startNewChat = () => {
    if (currentMessages.length > 0) {
      const chatTitle = generateChatTitle(currentMessages);
      const newChats = [...chats, { title: chatTitle, messages: currentMessages }];
      setChats(newChats);
      localStorage.setItem("chatHistory", JSON.stringify(newChats)); // Save to local storage
    }
    setCurrentMessages([]);
  };

  const loadChat = (chatIndex) => {
    setCurrentMessages(chats[chatIndex].messages);
    setSidebarOpen(false);
  };

  return (
    <div className="App">
      <motion.button 
        className="burger-menu"
        onClick={() => setSidebarOpen(true)}
        whileHover={{ scale: 1.2 }}
        whileTap={{ scale: 0.9 }}
      >
        ☰
      </motion.button>

      {/* Sidebar for Chat History */}
      <motion.div
        className={`sidebar ${sidebarOpen ? "open" : ""}`}
        initial={{ x: "-100%" }}
        animate={{ x: sidebarOpen ? 0 : "-100%" }}
        transition={{ duration: 0.3 }}
      >
        <button className="close-menu" onClick={() => setSidebarOpen(false)}>✖</button>
        <h2>Chat History</h2>
        <button className="new-chat-btn" onClick={startNewChat}>➕ Start New Chat</button>
        <div className="chat-history">
          {chats.length === 0 ? (
            <p>No chat history yet.</p>
          ) : (
            chats.map((chat, index) => (
              <div key={index} className="chat-item" onClick={() => loadChat(index)}>
                ➜ {chat.title}
              </div>
            ))
          )}
        </div>
      </motion.div>

      {/* Main Chat Interface - Enlarged */}
      <div className={`main-content ${sidebarOpen ? "shift" : ""}`}>
        <motion.h1 
          className="chat-title"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          BetAI Chatbot
        </motion.h1>
        
        <motion.div 
          className="terminal-container"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
        >
          {currentMessages.map((msg, index) => (
            <motion.div
              key={index}
              className={`terminal-message ${msg.sender}-message`}
              initial={{ opacity: 0, x: msg.sender === "user" ? 50 : -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              {msg.text.split("\n").map((line, idx) => (
                <span key={idx}>
                  {line}
                  <br />
                </span>
              ))}
            </motion.div>
          ))}
          <div ref={chatEndRef} />
        </motion.div>

        {/* Input Container - Fixed at Bottom */}
        <motion.div 
          className="input-container"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a bet (e.g., 'Should I bet on Team A vs Team B?')"
            onKeyPress={(e) => e.key === "Enter" && sendMessage()}
          />
          <motion.button 
            onClick={sendMessage}
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            Send
          </motion.button>
        </motion.div>
      </div>
    </div>
  );
};

export default Chatbot;