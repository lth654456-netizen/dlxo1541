# Rules

## @local Command Handling
When the user includes the `@local` keyword in their request (e.g., `@local <prompt>`), the agent must:
1. Parse the user's prompt or request.
2. Send the prompt to the local Ollama API server configured in [antgraviti.config.json](file:///c:/Users/a0103/OneDrive/Desktop/안티그레비티/dlxo1541/antgraviti.config.json) (Base URL: `http://localhost:11434/v1`, Model: `gemma4:e2b`).
3. To query this local API, the agent should run a temporary helper Python script or use a curl command in PowerShell.
4. Retrieve the local model's response and use it as context/instruction to perform the development work requested by the user.

## Google OAuth Desktop App Configuration
When configuring Google OAuth2 for Desktop (installed) applications in this repository:
1. Always use a fixed redirect port (e.g., `8080`) to ensure predictable redirect behavior on `http://localhost:8080/`.
2. Ensure the Google Cloud project's OAuth user type is set to `External` (not `Internal`) to allow personal `@gmail.com` accounts to authenticate.
3. Cache authorization tokens locally (e.g. `token.pickle`) to avoid prompting the user for browser authentication on every execution.

