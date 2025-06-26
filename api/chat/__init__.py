import os
import json
import requests
import azure.functions as func
import logging  # Add logging
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-05-01-preview"
)

# Only use the existing Assistant ID from environment; do not create or update the assistant here.
ASSISTANT_ID = os.getenv("AZURE_ASSISTANT_ID")
if not ASSISTANT_ID:
    raise RuntimeError("AZURE_ASSISTANT_ID is not set! Please define it in your Azure Function configuration.")

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
    thread_id = body.get("thread_id")

    # Fetch latest tasks for context
    try:
        tasks_resp = requests.get(TASKS_API)
        tasks_data = tasks_resp.json()
        tasks_list = tasks_data.get("value", [])
        # Format as a prefix for the user message
        if tasks_list:
            task_lines = [
                f"- {t['TaskText']} [{'Done' if t['Completed'] else 'Pending'}] (ID: {t['Id']})"
                for t in tasks_list
            ]
            tasks_prefix = (
                "Here is the current list of tasks (with their status and ID):\n" + "\n".join(task_lines) + "\n\n"
            )
        else:
            tasks_prefix = "There are currently no tasks.\n\n"
    except Exception as e:
        tasks_prefix = "(Could not fetch tasks for context.)\n\n"

    try:
        # Use the Assistants API flow with persistent thread
        if thread_id:
            thread = client.beta.threads.retrieve(thread_id=thread_id)
        else:
            thread = client.beta.threads.create()
        # Add user message with tasks context prepended
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=tasks_prefix + user_message
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
                json.dumps({"error": f"Assistant run failed: {run_status.status}", "thread_id": thread.id}),
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
        if not reply or not reply.strip():
            return func.HttpResponse(
                json.dumps({"error": "Assistant returned an empty response.", "thread_id": thread.id}),
                status_code=500,
                mimetype="application/json"
            )
        # Log the raw assistant reply for debugging
        logging.info(f"Raw assistant reply: {reply}")
        # Robust JSON parsing with fallback
        try:
            reply_json = json.loads(reply)
        except Exception as e:
            # Return a user-friendly error and log the raw reply
            return func.HttpResponse(
                json.dumps({
                    "error": "Assistant returned an invalid response. Please try rephrasing your request.",
                    "raw_reply": reply,
                    "thread_id": thread.id
                }),
                status_code=500,
                mimetype="application/json"
            )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid response from assistant: {str(e)}", "raw_reply": reply if 'reply' in locals() else None, "thread_id": thread.id if 'thread' in locals() else None}),
            status_code=500,
            mimetype="application/json"
        )

    # Handle actions
    action = reply_json.get("action")
    message = reply_json.get("message", "")
    result = {"message": message, "raw_reply": reply}  # Always include raw_reply for debugging

    if action == "add":
        task = reply_json.get("task")
        if task:
            r = requests.post(TASKS_API, json={"TaskText": task, "Completed": False, "UserId": "user"})
            if r.ok:
                result["task_added"] = task
            else:
                result["error"] = "Failed to add task."
        return func.HttpResponse(
            json.dumps({**result, "thread_id": thread.id}),
            status_code=200,
            mimetype="application/json"
        )
    elif action == "remove":
        task_id = reply_json.get("id") or reply_json.get("index")
        if task_id:
            del_r = requests.delete(f"{TASKS_API}/Id/{task_id}")
            if del_r.ok:
                result["task_removed"] = task_id
            else:
                result["error"] = f"Failed to remove task. Status: {del_r.status_code}, Response: {del_r.text}"
        else:
            result["error"] = "No task ID provided for removal."
        return func.HttpResponse(
            json.dumps({**result, "thread_id": thread.id}),
            status_code=200,
            mimetype="application/json"
        )
    elif action == "show":
        r = requests.get(TASKS_API)
        data = r.json()
        if "value" in data:
            result["tasks"] = [f"#{t['Id']}: {t['TaskText']} [{'Done' if t['Completed'] else 'Pending'}]" for t in data["value"]]
        return func.HttpResponse(
            json.dumps({**result, "thread_id": thread.id}),
            status_code=200,
            mimetype="application/json"
        )
    elif action == "complete":
        task_id = reply_json.get("id") or reply_json.get("index")
        if task_id:
            patch_r = requests.patch(f"{TASKS_API}/Id/{task_id}", json={"Completed": True})
            if patch_r.ok:
                result["task_completed"] = task_id
            else:
                result["error"] = f"Failed to complete task. Status: {patch_r.status_code}, Response: {patch_r.text}"
        else:
            result["error"] = "No task ID provided for completion."
        return func.HttpResponse(
            json.dumps({**result, "thread_id": thread.id}),
            status_code=200,
            mimetype="application/json"
        )
    for k in ["chat", "suggestion", "help"]:
        if k in reply_json:
            result[k] = reply_json[k]
    result["thread_id"] = thread.id
    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json"
    )
