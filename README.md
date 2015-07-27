# A Basic PyTorch Discord Bot

This project is used for a Python-based Discord bot that can generate images locally using PyTorch via the \`!generate\` command. By pinging it as a @mention and sending an embedded file, it will run img2img. It's rather basic, and really just a learning experience on interacting with PyTorch and Discord, to polish async development and Python skills.

## Features

- Generate images locally using PyTorch via the \`!generate\` command
- Generate images by pinging the bot as a @mention and sending an embedded file, it will run img2img
- Images are hosted by the imgur API, allowing for a 25MiB file size for images instead of the default 8M for Discord
- Configuration settings can be found in \`diffusion_discord_bot/config/config.json\`, which can be copied from \`...config/example.json\` from the same directory

## Getting Started

1. Clone the repository
2. Install dependencies using \`pip install -r requirements.txt\`
3. Copy the example configuration file \`config/example.json\` to \`diffusion_discord_bot/config/config.json\` and modify the settings as necessary. Be sure to acquire and fill in all of the API tokens, or it likely won't work.
