import { useState, useEffect, useRef } from 'react';
import './TaskAgentChatbox.css';

const API_URL = 'https://purple-pond-030ad401e.2.azurestaticapps.net/data-api/api/Tasks';

export default function TaskAgentChatbox() {
  const [messages, setMessages] = useState([
    { sender: 'agent', text: 'Hi! I can help you manage your tasks. Type "list" to see all tasks, "add <task>" to add, or "remove <id>" to delete.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleUserInput = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMsg = { sender: 'user', text: input };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput('');
    setLoading(true);
    await handleAgentResponse(input);
    setLoading(false);
  };

  const handleAgentResponse = async (input) => {
    const [command, ...rest] = input.trim().split(' ');
    if (command.toLowerCase() === 'list') {
      try {
        const res = await fetch(API_URL);
        const data = await res.json();
        if (Array.isArray(data.value)) {
          if (data.value.length === 0) {
            setMessages((msgs) => [...msgs, { sender: 'agent', text: 'No tasks found.' }]);
          } else {
            const list = data.value.map(t => `#${t.Id}: ${t.TaskText} [${t.Completed ? 'Done' : 'Pending'}]`).join('\n');
            setMessages((msgs) => [...msgs, { sender: 'agent', text: `Here are your tasks:\n${list}` }]);
          }
        } else {
          setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Unexpected response from API.' }]);
        }
      } catch (err) {
        setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Failed to fetch tasks.' }]);
      }
    } else if (command.toLowerCase() === 'add') {
      const taskText = rest.join(' ');
      if (!taskText) {
        setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Please provide a task description.' }]);
        return;
      }
      try {
        const res = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ TaskText: taskText, Completed: false, UserId: 'user' })
        });
        if (res.ok) {
          setMessages((msgs) => [...msgs, { sender: 'agent', text: `Task added: "${taskText}"` }]);
        } else {
          setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Failed to add task.' }]);
        }
      } catch (err) {
        setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Error adding task.' }]);
      }
    } else if (command.toLowerCase() === 'remove') {
      const id = rest[0];
      if (!id || isNaN(Number(id))) {
        setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Please provide a valid task id to remove.' }]);
        return;
      }
      try {
        const res = await fetch(`${API_URL}/${id}`, { method: 'DELETE' });
        if (res.ok) {
          setMessages((msgs) => [...msgs, { sender: 'agent', text: `Task #${id} removed.` }]);
        } else {
          setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Failed to remove task.' }]);
        }
      } catch (err) {
        setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Error removing task.' }]);
      }
    } else {
      setMessages((msgs) => [...msgs, { sender: 'agent', text: 'Sorry, I did not understand. Use "list", "add <task>", or "remove <id>".' }]);
    }
  };

  return (
    <div className="task-agent-chatbox">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.sender}`}>{msg.text.split('\n').map((line, idx) => <div key={idx}>{line}</div>)}</div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <form className="chat-input" onSubmit={handleUserInput}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type a command..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
