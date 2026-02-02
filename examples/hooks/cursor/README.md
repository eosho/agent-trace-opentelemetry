# Cursor Hook Configuration

Copy `hooks.json` to your project's `.cursor` directory:

## Location

```txt
your-project/
├── .cursor/
│   └── hooks.json    <-- Place here
├── src/
└── ...
```

## What it does

This hook runs `agent-trace` after every file edit made by Cursor's AI, recording attribution data.

## Alternative: Global configuration

For global Cursor settings, place in:

- **macOS**: `~/Library/Application Support/Cursor/User/settings.json`
- **Linux**: `~/.config/Cursor/User/settings.json`
- **Windows**: `%APPDATA%\Cursor\User\settings.json`

## Note

Cursor hook support varies by version. Check Cursor documentation for the latest hook configuration options.

```bash
curl -sSL https://usegitai.com/install.sh | bash
```
