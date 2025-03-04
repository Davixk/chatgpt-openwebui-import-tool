import json
import requests
import time
import os

from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

OPEN_WEBUI_URL = os.environ.get("OPEN_WEBUI_URL")
USER_ID = os.environ.get("USER_ID")
JWT_TOKEN = os.environ.get("JWT_TOKEN")
MAX_WORKERS = 16


class Memory(BaseModel):
    content: str
    created_at: int
    updated_at: int
    weight: float | None = None
    model: str | None = None
    server_id: str | None = None

    def __eq__(self, other):
        if not isinstance(other, Memory):
            return False
        # Compare content only
        return self.content == other.content

    def __hash__(self):
        return hash(self.content)


def extract_memories(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    total_messages = sum(len(convo.get("mapping", {})) for convo in conversations)

    all_memories = []
    with tqdm(total=total_messages, desc="Extracting memories") as pbar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_convo = {
                executor.submit(process_conversation, convo): convo
                for convo in conversations
            }

            for future in as_completed(future_to_convo):
                try:
                    memories, msg_count = future.result()
                    all_memories.extend(memories)
                    pbar.update(msg_count)
                except Exception as e:
                    print(f"Error processing conversation: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        for memory in all_memories:
            f.write(memory.json() + "\n")

    return all_memories


def process_conversation(convo):
    """Process a single conversation and return (memories_list, message_count)."""
    memories = []
    mapping = convo.get("mapping", {})
    for msg_id, msg_data in mapping.items():
        if not msg_data:
            continue
        message = msg_data.get("message")
        if not message:
            continue
        recipient = message.get("recipient")
        if recipient == "bio":
            memory_content_list = message.get("content", {}).get("parts", [])
            memory_content = "\n".join(memory_content_list)
            create_time = message.get("create_time")
            update_time = message.get("update_time")
            weight = message.get("weight")
            model = message.get("metadata", {}).get("model_slug")
            try:
                memory = Memory(
                    content=memory_content,
                    created_at=int(create_time) if create_time else int(time.time()),
                    updated_at=int(update_time) if update_time else int(time.time()),
                    weight=float(weight) if weight is not None else None,
                    model=model if model else None,
                    server_id=None,
                )
                memories.append(memory)
            except ValidationError as ve:
                print(f"Validation error for memory: {ve}")
                continue
    return memories, len(mapping)


def fetch_open_webui_memories(url: str, user_id, jwt_token):
    memories_url = f"{url}/api/v1/memories/"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(memories_url, headers=headers, params={"user": user_id})
    response.raise_for_status()
    memories_data = response.json()
    memories = []
    for memory_data in memories_data:
        try:
            memory = Memory(
                content=memory_data["content"],
                created_at=memory_data.get("created_at", int(time.time())),
                updated_at=memory_data.get("updated_at", int(time.time())),
                weight=memory_data.get("weight", None),
                model=memory_data.get("model", None),
                server_id=memory_data.get("id"),
            )
            memories.append(memory)
        except (ValidationError, KeyError) as ve:
            print(f"Validation error for server memory: {ve}")
            continue
    return memories


def delete_open_webui_memory(url: str, user_id, jwt_token, memory: Memory):
    delete_url = f"{url}/api/v1/memories/{memory.server_id}"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    try:
        response = requests.delete(delete_url, headers=headers)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Error deleting memory from server: {e}")
        return False


def delete_memories(memories_to_delete, url: str, user_id, jwt_token):
    for memory in tqdm(memories_to_delete, desc="Deleting memories"):
        success = delete_open_webui_memory(url, user_id, jwt_token, memory)
        if not success:
            print(f"\nError deleting memory: {memory.content}")


def upload_memories(memories_to_upload, url: str, user_id, jwt_token):
    for memory in tqdm(memories_to_upload, desc="Uploading memories"):
        success = add_open_webui_memory(url, user_id, jwt_token, memory)
        if not success:
            print(f"\nError uploading memory: {memory.content}")


def add_open_webui_memory(url: str, user_id, jwt_token, memory: Memory):
    memories_url = f"{url}/api/v1/memories/add"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    data = {
        "user": user_id,
        "content": memory.content,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }
    try:
        response = requests.post(memories_url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Error adding memory to server: {e}")
        return False


if __name__ == "__main__":
    input_file = "conversations.json"
    output_file = "extracted_memories.jsonl"

    all_memories = extract_memories(input_file, output_file)

    existing_server_memories = fetch_open_webui_memories(
        url=OPEN_WEBUI_URL, user_id=USER_ID, jwt_token=JWT_TOKEN
    )

    server_memories_by_content = {}
    for mem in existing_server_memories:
        server_memories_by_content[mem.content] = mem

    local_memories_by_content = {}
    for mem in all_memories:
        local_memories_by_content[mem.content] = mem

    memories_to_upload = []
    memories_to_delete = []

    for content, server_mem in server_memories_by_content.items():
        local_mem = local_memories_by_content.get(content)
        if local_mem:
            if local_mem.created_at < server_mem.created_at:
                memories_to_delete.append(server_mem)
                memories_to_upload.append(local_mem)
        else:
            pass

    for content, local_mem in local_memories_by_content.items():
        if content not in server_memories_by_content:
            memories_to_upload.append(local_mem)

    if memories_to_delete:
        print(f"Total memories to delete: {len(memories_to_delete)}")
        delete_memories(memories_to_delete, OPEN_WEBUI_URL, USER_ID, JWT_TOKEN)
    else:
        print("No memories to delete.")

    if memories_to_upload:
        print(f"Total memories to upload: {len(memories_to_upload)}")
        upload_memories(memories_to_upload, OPEN_WEBUI_URL, USER_ID, JWT_TOKEN)
    else:
        print("No new memories to upload.")
