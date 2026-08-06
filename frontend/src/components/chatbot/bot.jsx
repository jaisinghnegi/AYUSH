import React, { useState, useEffect, useRef } from "react";
import "./bot.css";
import { API_BASE } from "../../lib/authApi";

const MAX_HISTORY_TURNS = 10;

const Bot = () => {
  const [visible, setVisible] = useState(false);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Namaste! I'm your Ayurveda Assistant. Ask me about Ayurveda, traditional diseases, or ICD-11 codes.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  // Show bot icon after 5 seconds with pop animation
  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(true);
    },500);
    return () => clearTimeout(timer);
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;

    const userMessage = { sender: "user", text: input };
    const history = messages
      .slice(-MAX_HISTORY_TURNS)
      .map((m) => ({ role: m.sender === "user" ? "user" : "assistant", content: m.text }));

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {
      const res = await fetch(`${API_BASE}/assistant/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.text, history }),
      });

      const data = await res.json();

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: data?.error || "Sorry, something went wrong." },
        ]);
        return;
      }

      setMessages((prev) => [...prev, { sender: "bot", text: data.reply }]);
    } catch (err) {
      console.error("Assistant chat failed:", err);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Error fetching response. Try again." },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      {visible && (
        <div className="bot-container">
          {/** Floating Icon **/}
          {!open && (
            <div className="bot-icon pop-in" onClick={() => setOpen(true)}>
              <img
                src="/assets/boticon.png"
                alt="Ayurveda Assistant"
                className="bot-icon-img"
              />
            </div>
          )}

          {/** Chat Window **/}
          {open && (
            <div className="bot-chat">
              <div className="bot-header">
                <div className="bot-title">
                  <span>Ayurveda Assistant</span>
                </div>
                <button className="close-btn" onClick={() => setOpen(false)}>
                  ✖
                </button>
              </div>
              <div className="bot-messages">
                {messages.map((msg, i) => (
                  <div key={i} className={`bot-msg ${msg.sender}`}>
                    {msg.text}
                  </div>
                ))}
                {sending && <div className="bot-msg bot">Thinking...</div>}
                <div ref={messagesEndRef} />
              </div>
              <div className="bot-input">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about symptoms, codes, diseases..."
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  disabled={sending}
                />
                <button onClick={handleSend} disabled={sending}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M2 21L23 12L2 3V10L17 12L2 14V21Z" fill="currentColor"/>
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
};

export default Bot;
