import { useState, useEffect, useRef } from 'react';
import './TaskAgentChatbox.css';

const BACKEND_URL = '/api/chat'; // Use relative path for Azure Static Web Apps
const TASKS_API = '/data-api/api/Tasks'; // DAB endpoint for tasks

// Notification component for pending tasks
function PendingTasksNotification() {
  const [pendingCount, setPendingCount] = useState(null);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef();

  useEffect(() => {
    let intervalId;
    async function fetchPending() {
      try {
        const res = await fetch(TASKS_API);
        const data = await res.json();
        if (data && Array.isArray(data.value)) {
          const count = data.value.filter(t => !t.Completed).length;
          setPendingCount(count);
          setVisible(true);
          clearTimeout(timerRef.current);
          timerRef.current = setTimeout(() => setVisible(false), 5000);
        }
      } catch {
        // ignore errors
      }
    }
    fetchPending(); // initial fetch
    intervalId = setInterval(fetchPending, 15000);
    return () => {
      clearInterval(intervalId);
      clearTimeout(timerRef.current);
    };
  }, []);

  if (!visible || pendingCount === null) return null;
  return (
    <div className="pending-tasks-notification">
      <span className="email-icon" aria-label="pending tasks">✉️</span>
      <span className="pending-text">
        {pendingCount === 1
          ? 'You have 1 pending task to complete'
          : `You have ${pendingCount} pending tasks to complete`}
      </span>
    </div>
  );
}

export default function TaskAgentChatbox() {
  // Always reset threadId on app load
  useEffect(() => {
    localStorage.removeItem('threadId');
  }, []);

  const [messages, setMessages] = useState([
    { sender: 'agent', text: 'Hi! I can help you manage your tasks or just chat. Try: "Please remind me to buy milk" or "What do I need to do?"', type: 'info' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [initialTasks, setInitialTasks] = useState(null); // null = not loaded, [] = loaded but empty
  const [showInitialLoading, setShowInitialLoading] = useState(true);
  const chatEndRef = useRef(null);

  // Load task list on page load and show loading screen until ready
  useEffect(() => {
    let isMounted = true;
    async function fetchTasksWithRetry(retries = 10, delay = 2000) {
      for (let i = 0; i < retries; i++) {
        try {
          const res = await fetch(TASKS_API);
          if (!res.ok) throw new Error('DAB not ready');
          const data = await res.json();
          if (isMounted) {
            setInitialTasks(data.value || []);
            setShowInitialLoading(false);
          }
          return;
        } catch {
          if (i === retries - 1 && isMounted) {
            setInitialTasks([]);
            setShowInitialLoading(false);
          }
          await new Promise(r => setTimeout(r, delay));
        }
      }
    }
    fetchTasksWithRetry();
    return () => { isMounted = false; };
  }, []);

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
      if (data.task_completed) type = 'complete';
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

  // Helper to parse task string: "#2: Buy milk [Pending]"
  function parseTaskString(taskStr) {
    const match = taskStr.match(/^#(\d+):\s(.+)\s\[(Done|Pending)\]$/);
    if (!match) return null;
    return { id: match[1], text: match[2], status: match[3] };
  }

  // Render loading screen if DAB is not ready
  if (showInitialLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <div className="loading-message">Loading task data, please wait while the database API wakes up...</div>
      </div>
    );
  }

  return (
    <div className="task-agent-chatbox">
      <PendingTasksNotification />
      {/* Optionally show the initial task list here, e.g. as a table or summary */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.sender} ${msg.type || ''}`.trim()}>
            {msg.type === 'tasks' && msg.tasks ? (
              <table className="task-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Task</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {msg.tasks.map((taskStr, idx) => {
                    const parsed = parseTaskString(taskStr);
                    return parsed ? (
                      <tr key={idx}>
                        <td>{parsed.id}</td>
                        <td>{parsed.text}</td>
                        <td>{parsed.status}</td>
                      </tr>
                    ) : (
                      <tr key={idx}><td colSpan="3">{taskStr}</td></tr>
                    );
                  })}
                </tbody>
              </table>
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
