import os
import json
import requests
import azure.functions as func
from openai import AzureOpenAI
import logging

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
    try:
        # Use the Assistants API flow
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        # Wait for the run to complete (polling)
        import time
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            time.sleep(0.5)
        if run_status.status != "completed":
            return func.HttpResponse(
                json.dumps({"error": f"Assistant run failed: {run_status.status}"}),
                status_code=500,
                mimetype="application/json"
            )
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        # Get the latest assistant message
        reply = None
        for m in messages.data:
            if m.role == "assistant":
                reply = m.content[0].text.value if m.content and hasattr(m.content[0], 'text') else None
                break
        logging.info(f"Raw assistant reply: {repr(reply)}")
        if not reply or not reply.strip():
            return func.HttpResponse(
                json.dumps({"error": "Assistant returned an empty response."}),
                status_code=500,
                mimetype="application/json"
            )
        reply_json = json.loads(reply)
    except Exception as e:
        logging.exception("Error in assistant API flow or parsing response")
        return func.HttpResponse(
            json.dumps({"error": f"Invalid response from assistant: {str(e)}", "raw_reply": reply if 'reply' in locals() else None}),
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
