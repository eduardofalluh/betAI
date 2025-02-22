import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatEndRef = useRef(null);

  const sendMessage = async () => {
    if (input.trim() === "") return;

    const userMessage = { text: input, sender: "user" };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await axios.post("http://localhost:5000/chat", { message: input });
      const botMessage = { text: response.data.reply, sender: "bot" };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error fetching response", error);
      setMessages((prev) => [...prev, { text: "Error: Couldn’t process your request.", sender: "bot" }]);
    }

    setInput("");
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="App">
      {!sidebarOpen && (
        <button className="burger-menu" onClick={() => setSidebarOpen(true)}>
          ☰
        </button>
      )}

      <div className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <button className="close-menu" onClick={() => setSidebarOpen(false)}>✖</button>
        <h2>Betting History</h2>
        <div className="chat-history">
          {messages.length === 0 ? (
            <p>No betting history yet.</p>
          ) : (
            messages.map((msg, index) => (
              <div key={index} className="chat-item">
                {msg.sender === "user" ? "➜ " : "[BetAI] "} {msg.text}
              </div>
            ))
          )}
        </div>
      </div>

      <div className={`main-content ${sidebarOpen ? "shift" : ""}`}>
        <h1 className="chat-title">BetAI Chatbot</h1>
        <div className="terminal-container">
          {messages.map((msg, index) => (
            <div key={index} className={`terminal-message ${msg.sender}-message`}>
              {msg.text}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a bet (e.g., 'Should I bet on Team A vs Team B?')"
            onKeyPress={(e) => e.key === "Enter" && sendMessage()}
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;