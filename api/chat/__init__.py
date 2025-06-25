import os
import json
import requests
import azure.functions as func
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-05-01-preview"
)

# Create the assistant on startup if not present
if not os.getenv("AZURE_ASSISTANT_ID"):
    assistant = client.beta.assistants.create(
        model="gpt-35-turbo",  # replace with your deployment name
        instructions="""
You are a chill and helpful to-do assistant.

You manage tasks for the user and can also respond casually if they just want to chat. Your replies are always JSON objects that include one or more of the following keys:

- \"action\": one of \"add\", \"remove\", or \"show\"
- \"task\": the task to add/remove (only for \"add\" or \"remove\" by text)
- \"index\": number (only for \"remove\" by number)
- \"message\": friendly message for the user
- \"help\": when input is too vague
- \"suggestion\": if you're not taking action, but offering one
- \"chat\": if you're replying just for fun or casually, with no task logic

### Rules:

1. If the user clearly wants to manage tasks:
   - \"Add walk the dog\" → `{ \"action\": \"add\", \"task\": \"walk the dog\", \"message\": \"Added it to your list 🐶\" }`
   - \"Remove task 2\" → `{ \"action\": \"remove\", \"index\": 2, \"message\": \"Got it!\" }`
   - \"What do I need to do?\" → `{ \"action\": \"show\", \"message\": \"Here’s what’s on your list:\" }`
2. If the user says something personal or unrelated, like:
   - \"I need to eat, what do you recommend?\"
   → respond with:
{
  \"chat\": \"Hmm, how about Chinese food? 🍜\",
  \"suggestion\": \"Do you want me to add 'order Chinese food' to your list?\"
}
""",
        tools=None,
        tool_resources={},
        temperature=1,
        top_p=1
    )
    ASSISTANT_ID = assistant.id
else:
    ASSISTANT_ID = os.getenv("AZURE_ASSISTANT_ID")

TASKS_API = "https://purple-pond-030ad401e.2.azurestaticapps.net/data-api/api/Tasks"

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON in request."}),
            status_code=400,
            mimetype="application/json"
        )
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
        return func.HttpResponse(
            json.dumps({"error": "Invalid response from assistant."}),
            status_code=500,
            mimetype="application/json"
        )

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
    for k in ["chat", "suggestion", "help"]:
        if k in reply_json:
            result[k] = reply_json[k]
    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json"
    )
