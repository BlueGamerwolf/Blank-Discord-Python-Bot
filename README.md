# Blank Discord Python Bot

A beginner-friendly Discord.py bot template designed to help developers learn how Discord bots work while providing a clean foundation for building their own projects.

This repository is intentionally simple and organized so new developers can understand each part of the bot without being overwhelmed.

---

## Features

* Simple command system
* Modular command files
* Event system
* Logging system
* Environment variable support
* Beginner-friendly structure
* Easy to expand
* Well-commented examples

---

## Project Structure

```text
Blank-Discord-Python-Bot/
│
├── bot.py
├── config.py
├── requirements.txt
├── .env
├── README.md
│
├── modules/
│   ├── ping.py
│   ├── help.py
│   ├── logging.py
│   └── template.py
│
├── events/
│   ├── ready.py
│   ├── member_join.py
│   └── message.py
│
├── utils/
│   ├── embeds.py
│   ├── permissions.py
│   └── logger.py
│
├── storage/
│   ├── data.json
│   └── logs/
│
└── assets/
    └── images/
```

---

## Requirements

* Python 3.10+
* Discord Bot Token

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/BlueGamerwolf/Blank-Discord-Python-Bot.git
cd Blank-Discord-Python-Bot
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file:

```env
TOKEN=YOUR_BOT_TOKEN
PREFIX=!
```

---

## Running the Bot

```bash
python bot.py
```

If everything is configured correctly, the bot should connect and display a startup message in the console.

---

## Creating Commands

Create a new file inside the `modules` folder.

Example:

```python
from discord.ext import commands

def setup(bot):

    @bot.command()
    async def hello(ctx):
        await ctx.send("Hello World!")
```

The command can now be used:

```text
!hello
```

---

## Creating Events

Create a file inside the `events` folder.

Example:

```python
def setup(bot):

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
```

---

## Logging

The template includes a logging system that:

* Logs to the console
* Logs to files
* Stores logs in:

```text
storage/logs/
```

This makes debugging much easier.

---

## Learning Goals

This project is designed to teach:

* Discord.py basics
* Commands
* Events
* Modular programming
* Configuration management
* Logging
* File organization
* Best practices

---

## Recommended First Projects

After getting the template running, try adding:

* Moderation Commands
* Welcome Messages
* Ticket Systems
* Verification Systems
* Leveling Systems
* Music Commands
* Economy Systems
* Custom APIs

---

## Contributing

Feel free to fork this repository and build your own version.

If you improve the template and think others would benefit from it, submit a pull request.

---

## License

This project is provided as a learning resource.

Use it, modify it, and build amazing things with it.

---

## Created By

Blue Gamerwolf

GitHub:
https://github.com/BlueGamerwolf

Helping new developers learn Discord bot development one command at a time.
