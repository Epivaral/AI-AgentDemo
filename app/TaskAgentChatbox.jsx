import { useState, useEffect, useRef } from 'react';
import './TaskAgentChatbox.css';

const BACKEND_URL = '/api/chat'; // Use relative path for Azure Static Web Apps

export default function TaskAgentChatbox() {
  const [messages, setMessages] = useState([
    { sender: 'agent', text: 'Hi! I can help you manage your tasks or just chat. Try: "Please remind me to buy milk" or "What do I need to do?"', type: 'info' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(() => localStorage.getItem('threadId') || null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleUserInput = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMsg = { sender: 'user', text: input, type: 'user' };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');
    setLoading(true);
    await handleAgentResponse(input);
    setLoading(false);
  };

  const handleAgentResponse = async (input) => {
    try {
      const res = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input, thread_id: threadId })
      });
      const data = await res.json();
      if (data.thread_id && data.thread_id !== threadId) {
        setThreadId(data.thread_id);
        localStorage.setItem('threadId', data.thread_id);
      }
      let reply = '';
      let type = 'info';
      let tasks = null;
      if (data.message) reply += data.message + '\n';
      if (data.tasks && Array.isArray(data.tasks)) {
        tasks = data.tasks;
        reply += data.tasks.join('\n') + '\n';
        type = 'tasks';
      }
      if (data.task_added) type = 'add';
      if (data.task_removed) type = 'remove';
      if (data.chat && !data.action) {
        reply += data.chat + '\n';
        type = 'chat';
      }
      if (data.suggestion) reply += '💡 ' + data.suggestion + '\n';
      if (data.help) reply += '❓ ' + data.help + '\n';
      if (data.error) reply += '⚠️ ' + data.error + '\n';
      setMessages((msgs) => [...msgs, { sender: 'agent', text: reply.trim() || 'Sorry, I did not understand.', type, tasks }]);
    } catch (err) {
      setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Error contacting assistant backend.', type: 'error' }]);
    }
  };

  return (
    <div className="task-agent-chatbox">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.sender} ${msg.type || ''}`.trim()}>
            {msg.type === 'tasks' && msg.tasks ? (
              <div>
                {msg.text.split('\n').map((line, idx) =>
                  msg.tasks.includes(line) && line.trim() !== '' ? (
                    <div key={idx}><strong>{line}</strong></div>
                  ) : (
                    <div key={idx}>{line}</div>
                  )
                )}
              </div>
            ) : (
              msg.text.split('\n').map((line, idx) => <div key={idx}>{line}</div>)
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <img src="/mascot.png" alt="Mascot" className="mascot-img" />
      <form className="chat-input" onSubmit={handleUserInput}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type anything..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
