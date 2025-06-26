# Task Agent Chatbox (AI-AgentDemo)

A full-stack AI-powered to-do/chat agent web app using React, Azure Static Web Apps, Azure Functions (Python), Azure OpenAI (Assistants API), and Azure Data API Builder (DAB) with a SQL-backed Tasks table.

## What this app does
- Lets users manage tasks using natural language (e.g., "remind me to buy milk", "remove task 2", "what do I need to do?").
- Supports add, remove, list, and complete actions on a shared to-do list.
- Handles casual chat and suggestions, not just task management.
- All task data is stored in a SQL database and accessed via a RESTful Data API.
- The AI agent interprets user input and manages tasks via the backend.
- Shows a floating notification every 15 seconds (for 5 seconds) with the number of pending tasks, styled as a modern email alert in the top-right corner.
- Task lists are displayed as a table (ID, Task, Status) inside the chatbox for better readability.

## How it works
- **Frontend:** React app with a modern chatbox UI, color-coded bubbles for different actions, persistent chat context, and a floating notification for pending tasks.
- **Backend:** Azure Functions (Python) exposes an `/api/chat` endpoint. It:
  - Receives user messages and (optionally) a thread ID.
  - Uses Azure OpenAI Assistants API to interpret the message and maintain conversation context.
  - Handles task actions by calling the Azure Data API Builder REST API for the SQL Tasks table.
  - Returns the AI's reply, task results, and the thread ID for context.
- **Database:** Azure SQL Database with a `Tasks` table (`Id`, `UserId`, `TaskText`, `Completed`).
- **Data API:** Azure Data API Builder exposes REST endpoints for CRUD operations on the Tasks table.
- **Infra/Hosting:**
  - Azure Static Web Apps hosts the frontend and backend together.
  - Azure Functions runs the Python API.
  - Azure SQL Database stores tasks.
  - Azure OpenAI provides the AI assistant.

---

## How to use

Interact with the chatbox using natural language. Here are some example commands you can use:

- **Add a task:**
  - `remind me to buy milk`
  - `add walk the dog`
- **Remove a task:**
  - `remove task 2`
- **Show your tasks:**
  - `what do I need to do?`
  - `list my tasks`
- **Mark a task as completed:**
  - `mark task 2 as done`
  - `complete task 3`
- **Chat or ask for suggestions:**
  - `what should I eat for lunch?`
  - `tell me a joke`

You will see a floating notification in the top-right corner every 15 seconds (for 5 seconds) showing how many tasks are still pending, with an email icon.
When you ask to "show" or "list" your tasks, they will be displayed as a table (ID, Task, Status) for easy reading.

The agent will understand your intent, manage your tasks, and keep the conversation context-aware.

---

## Step-by-step: How to build this app from scratch

### 1. Set up the database and Data API
- **Create an Azure SQL Database** and define a `Tasks` table:
  ```sql
  CREATE TABLE dbo.Tasks (
      Id INT IDENTITY(1,1) PRIMARY KEY,
      UserId NVARCHAR(50),
      TaskText NVARCHAR(255),
      Completed BIT DEFAULT 0
  );
  ```
- **Deploy Azure Data API Builder (DAB)** to expose REST endpoints for your SQL tables.
- Configure DAB to expose the `Tasks` table with full CRUD permissions.

### 2. Set up Azure OpenAI and create an Assistant
- **Provision an Azure OpenAI resource** in your Azure subscription.
- Deploy a model (e.g., `gpt-35-turbo`).
- In Azure OpenAI Studio (or via API), create an Assistant with instructions to always reply in JSON and handle task management logic. Example instructions:
  - Always reply in JSON with keys: `action`, `message`, and (if relevant) `id`, `task`, or `tasks`.
  - Supported actions: `add`, `remove`, `show`, `complete`, `chat`, `suggestion`, `help`.
  - For `show`, return a list of all tasks with their IDs, text, and completion status.
  - For `add`, include the new task text.
  - For `remove` or `complete`, include the task ID.
  - For `chat`, `suggestion`, or `help`, include a helpful message.
- Note the Assistant ID for use in your backend.

### 3. Build the backend (Azure Functions Python API)
- **Create an Azure Functions Python app** with an HTTP-triggered function at `/api/chat`.
- Install dependencies: `azure-functions`, `openai`, `requests`.
- Implement the function to:
  - Accept POST requests with a `message` and optional `thread_id`.
  - Use the OpenAI Assistants API to send/receive messages, maintaining thread context.
  - Parse the assistant's JSON reply to determine the action (add, remove, show, complete, chat, etc).
  - For task actions, call the DAB REST API to add, remove, complete, or list tasks in SQL.
  - Return the assistant's reply, any task results, and the thread ID to the frontend.
- Set environment variables for your OpenAI endpoint, API key, and Assistant ID.

### 4. Build the frontend (React)
- **Create a React app** for the chat UI.
- Implement a chatbox component that:
  - Displays messages with color-coded bubbles (blue for add, green for remove, purple for list, etc).
  - Stores and sends the `thread_id` with each request to maintain chat context.
  - Handles user input, sends it to `/api/chat`, and displays the agent's response.
  - Shows instructions and a modern, responsive layout.
  - Renders the task list as a table (ID, Task, Status) for better readability.
  - Includes a floating notification component that polls the backend every 15 seconds and shows the number of pending tasks for 5 seconds in the top-right corner.
- Style the chatbox and page using CSS for a clean, modern look.

### 5. Deploy as an Azure Static Web App
- **Deploy the React frontend and Azure Functions backend together** as an Azure Static Web App.
- Configure environment variables (OpenAI keys, Assistant ID, DAB endpoint, etc) in the Azure portal.
- Ensure your Data API and Function endpoints are accessible from the Static Web App.

### 6. Test and iterate
- Open your deployed app in a browser.
- Try commands like "add walk the dog", "remove 2", "what do I need to do?", or "mark task 2 as done".
- The agent should manage your tasks and chat with you, with context preserved across messages.
- Confirm that the floating notification appears and the task list is shown as a table.
- Debug and improve as needed (e.g., error handling, UI tweaks, assistant instructions).

---

## Infra used
- **Azure Static Web Apps** (frontend + backend hosting)
- **Azure Functions (Python)** (API logic)
- **Azure SQL Database** (task storage)
- **Azure Data API Builder** (REST API for SQL)
- **Azure OpenAI (Assistants API)** (AI agent)

---

This project demonstrates a modern, full-stack AI agent experience on Azure, combining conversational AI, serverless APIs, and cloud database integration. You can use this as a template for your own AI-powered productivity or chat apps!
