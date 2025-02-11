import React, { useState } from "react";
import axios from "axios";
import "./App.css";

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const sendMessage = async () => {
    if (input.trim() === "") return;

    const userMessage = { text: input, sender: "user" };
    setMessages([...messages, userMessage]);

    try {
      const response = await axios.post("http://localhost:5000/chat", { message: input });
      const botMessage = { text: response.data.reply, sender: "bot" };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error fetching response", error);
    }

    setInput("");
  };

  return (
    <div className="App">
      {/* Show burger menu only when sidebar is closed */}
      {!sidebarOpen && (
        <button className="burger-menu" onClick={() => setSidebarOpen(true)}>
          ☰
        </button>
      )}

      {/* Sidebar for Chat History */}
      <div className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <button className="close-menu" onClick={() => setSidebarOpen(false)}>✖</button>
        <h2>Chat History</h2>
        <div className="chat-history">
          {messages.length === 0 ? (
            <p>No chat history yet.</p>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className="chat-item">
                {msg.sender === "user" ? "➜ " : "[bot] "}
                {msg.text}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className={`main-content ${sidebarOpen ? "shift" : ""}`}>
        <h1 className="chat-title">BetAI Chatbot</h1>
        <div className="terminal-container">
          {messages.map((msg, index) => (
            <div key={index} className={`terminal-message ${msg.sender}-message`}>
              {msg.text}
            </div>
          ))}
        </div>
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a command..."
            onKeyPress={(e) => e.key === "Enter" && sendMessage()}
          />
        </div>
      </div>
    </div>
  );
};

export default Chatbot;