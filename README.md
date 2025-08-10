# Twitch Bot Controller

This project is a Twitch bot controller with a graphical user interface (GUI). It uses multiple Twitch accounts to post AI-generated comments in a Twitch channel, based on real-time audio from a stream.

## Features

*   **Multi-Account Support:** Control multiple Twitch bot accounts simultaneously.
*   **AI-Generated Comments:** Uses an AI model (via LM Studio) to generate context-aware and personality-driven comments.
*   **Speech-to-Text (STT):** Transcribes audio from a stream in real-time to provide context for the AI. Supports Vosk and Whisper.
*   **GUI Control:** An easy-to-use interface to start, stop, and manage the bots.
*   **Customizable Personalities:** Define different personalities for your bots in the `config.yaml` file.
*   **Hotkeys:** Use hotkeys for quick actions like sending predefined messages.

## Setup and Configuration

Follow these steps to set up and run the project.

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install dependencies

Install the required Python libraries using pip:

```bash
pip install -r requirements.txt
```

### 3. Create your Configuration File

Copy the example configuration file:

```bash
cp config.example.yaml config.yaml
```

Now, open `config.yaml` and edit it to match your setup. This file is not tracked by Git, so your changes will not be overwritten.

*   **`stt`:** Configure the speech-to-text engine.
    *   `model_path`: Path to your STT model (e.g., Vosk model).
    *   `sample_rate`: Sample rate for the audio capture.
    *   `phrase_timeout`: Timeout for detecting the end of a phrase.
*   **`behavior`:** Define the bot's behavior.
    *   `min_delay`, `max_delay`: Delays between messages.
    *   `activation_delay`: Delay between activating each bot.
*   **`ai`:** Set up the AI model.
    *   `api_url`: The API endpoint for your AI model (e.g., LM Studio).
*   **`characters`:** Define the personalities for your bots.
    *   `name`: The name of the personality.
    *   `system_prompt`: The prompt that defines the bot's character.
    *   `background`: Additional context for the bot.
    *   `examples`: Example responses.
    *   `response_params`: Parameters for the AI model's response generation.
*   **`accounts`:** Configure your Twitch bot accounts.
    *   `username`: The Twitch username of the bot.
    *   `oauth`: The OAuth token for the bot. **It is highly recommended to use environment variables for this.**
    *   `channel`: The Twitch channel to join (e.g., `#channelname`).
    *   `personality`: The personality to use for this bot.

### 4. Set up Environment Variables

For security reasons, it is recommended to store your Twitch OAuth tokens in a `.env` file in the root of the project directory.

1.  Create a file named `.env` in the root of the project.
2.  Add your OAuth tokens to this file. The name of the variable should match what you use in `config.yaml`.

```
YOUR_BOT_OAUTH_TOKEN=oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANOTHER_BOT_OAUTH_TOKEN=oauth:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

3.  In `config.yaml`, reference these variables using the `${VARIABLE_NAME}` syntax. For example:

```yaml
accounts:
  - username: "YOUR_BOT_USERNAME"
    oauth: ${YOUR_BOT_OAUTH_TOKEN}
    channel: "#TARGET_CHANNEL_NAME"
    personality: "Character_1"
```

You can get a Twitch OAuth token from [twitchapps.com/tmi/](https://twitchapps.com/tmi/).

## Usage

1.  **Run the application:**

    ```bash
    python main.py
    ```

2.  **Use the GUI:**
    *   The main window will show a list of your configured bot accounts.
    *   Select the accounts you want to use by checking the boxes next to their names.
    *   Click **"Старт"** (Start) to activate the selected bots.
    *   Click **"Стоп"** (Stop) to deactivate all bots.
    *   The status of each bot is displayed next to its name.

3.  **Hotkeys:**
    *   **F13:** Send a "+" message from all active bots.
    *   **F15:** Trigger a "laughter" event, which can be used to make the bots send laughing messages.
