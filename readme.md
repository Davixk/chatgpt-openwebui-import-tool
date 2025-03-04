# ChatGPT-OpenWebUI Import Tool

A simple Python tool to **import data exported from ChatGPT** (currently only "memories") and sync them with [OpenWebUI](https://github.com/OpenLLMAI/OpenWebUI).

---

## Features

- **Extract ChatGPT memories** from the official export `.json`.
- **Compare & sync**: detects which memories to add or delete on OpenWebUI.
- Works with multi-threading for faster processing.

---

## Prerequisites

- **Python 3.9+** (might work with older versions, but 3.9+ is recommended).
- [pip](https://pip.pypa.io/en/stable/) to install dependencies.

### Dependencies

```
pip install requests tqdm python-dotenv pydantic
```

---

## Setup

1. **Export your ChatGPT data**:
   - Go to **ChatGPT** → **Settings** → **Data controls** → **Export all data**.
   - You will receive an email from OpenAI with a download link to a `.zip`.
   - Extract the `.zip` – locate the `conversations.json` file.

2. **Create a `.env` file** in the project folder (or set them as environment variables). The file should contain:
   ```
   OPEN_WEBUI_URL=http://your-open-webui-url
   USER_ID=your_user_id
   JWT_TOKEN=your_jwt_token
   ```

   - **OPEN_WEBUI_URL**: Base URL to your OpenWebUI instance (e.g. `http://localhost:8080`).
   - **USER_ID**: Your user ID in OpenWebUI.
   - **JWT_TOKEN**: Your OpenWebUI JWT auth token.

3. **Place** your `conversations.json` in the same directory as the script (or modify the script paths accordingly).

---

## Usage

1. **Install dependencies** (if not done already):

   ```bash
   pip install -r requirements.txt
   ```
   
   Or individually:
   ```bash
   pip install requests tqdm python-dotenv pydantic
   ```

2. **Run the script**:

   ```bash
   python import_tool.py
   ```
   - By default, it reads from `conversations.json` and outputs to `extracted_memories.jsonl`.

3. **What it does**:
   - **Extract** memory messages from `conversations.json`.
   - **Compare** them to the existing memories in OpenWebUI.
   - **Upload** new or out-of-date memories.
   - **Delete** older duplicates on the server if there's a newer local memory.

You’ll see console output showing progress bars and any errors.

---

## Notes

- The script currently only deals with "memories" (`recipient == "bio"`) in ChatGPT exports. Other data might be added in the future.
- Check the **`extracted_memories.jsonl`** file after running to see exactly which memories were parsed from the conversation data.

---

## Contributing

Feel free to open issues or PRs if you’d like to add features (e.g., handling different parts of the ChatGPT export besides memories). 

---

## License

This project is licensed under the [MIT License](./LICENSE).