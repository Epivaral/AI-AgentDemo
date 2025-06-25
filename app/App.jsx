import React from 'react';
import TaskAgentChatbox from './TaskAgentChatbox.jsx';

function App() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '40px' }}>
      <h1>Task Agent Chatbox</h1>
      <TaskAgentChatbox />
    </div>
  );
}

export default App;
