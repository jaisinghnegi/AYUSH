import React, { useState, useEffect, useRef } from "react";
import "./bot.css";

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
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    try {
      // Call Gemini API
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${
          import.meta.env.VITE_GEMINI_API_KEY
        }`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ role: "user", parts: [{ text: input }] }],
          }),
        }
      );

      const data = await res.json();
      const botReply =
        data?.candidates?.[0]?.content?.parts?.[0]?.text ||
        "Sorry, I couldn't find information on that.";

      setMessages((prev) => [...prev, { sender: "bot", text: botReply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Error fetching response. Try again." },
      ]);
    }
    setInput("");
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
                <div ref={messagesEndRef} />
              </div>
              <div className="bot-input">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about symptoms, codes, diseases..."
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                />
                <button onClick={handleSend}>
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