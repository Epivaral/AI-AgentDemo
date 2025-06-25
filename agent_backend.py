import os
import json
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI

app = FastAPI()

# Allow CORS for local dev and your deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-05-01-preview"
)

ASSISTANT_ID = os.getenv("AZURE_ASSISTANT_ID")  # Or create on startup if needed
TASKS_API = "https://purple-pond-030ad401e.2.azurestaticapps.net/data-api/api/Tasks"

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    # Send to Azure OpenAI Assistant
    response = client.chat.completions.create(
        model="gpt-35-turbo",  # Or your deployment name
        messages=[{"role": "user", "content": user_message}],
        temperature=1,
        top_p=1,
        tools=None
    )
    try:
        reply = response.choices[0].message.content
        reply_json = json.loads(reply)
    except Exception:
        return {"error": "Invalid response from assistant."}

    # Handle actions
    action = reply_json.get("action")
    message = reply_json.get("message", "")
    result = {"message": message}

    if action == "add":
        task = reply_json.get("task")
        if task:
            r = requests.post(TASKS_API, json={"TaskText": task, "Completed": False, "UserId": "user"})
            if r.ok:
                result["task_added"] = task
            else:
                result["error"] = "Failed to add task."
    elif action == "remove":
        index = reply_json.get("index")
        if index:
            # Get all tasks
            r = requests.get(TASKS_API)
            data = r.json()
            if "value" in data and len(data["value"]) >= index:
                task_id = data["value"][index-1]["Id"]
                del_r = requests.delete(f"{TASKS_API}/{task_id}")
                if del_r.ok:
                    result["task_removed"] = index
                else:
                    result["error"] = "Failed to remove task."
            else:
                result["error"] = "Task index out of range."
    elif action == "show":
        r = requests.get(TASKS_API)
        data = r.json()
        if "value" in data:
            result["tasks"] = [f"#{t['Id']}: {t['TaskText']} [{'Done' if t['Completed'] else 'Pending'}]" for t in data["value"]]
    # Pass through chat/suggestion/help if present
    for k in ["chat", "suggestion", "help"]:
        if k in reply_json:
            result[k] = reply_json[k]
    return result
