import threading
import asyncio
import logging

logger = logging.getLogger("bot")

CHANNEL_ID = 1488915721743237281

def start_console(bot):
    def console_loop():
        async def send_message(content):
            try:
                # 🔥 Try cache first
                channel = bot.get_channel(CHANNEL_ID)

                # 🔥 Fallback to API fetch (fixes "Channel not found")
                if channel is None:
                    channel = await bot.fetch_channel(CHANNEL_ID)

                if channel is None:
                    logger.error("Channel not found: %s", CHANNEL_ID)
                    return

                await channel.send(content)
                logger.info("Console message sent: %s", content)

            except Exception as e:
                logger.error("Failed to send console message: %s", e)

        while True:
            try:
                msg = input("> ").strip()

                if not msg:
                    continue

                # 🔥 Optional command system (you’ll want this)
                if msg.lower() == "exit":
                    logger.info("Console exiting...")
                    break

                # 🔥 Thread-safe execution into Discord loop
                asyncio.run_coroutine_threadsafe(
                    send_message(msg),
                    bot.loop
                )

            except Exception as e:
                logger.error("Console loop error: %s", e)

    thread = threading.Thread(target=console_loop, daemon=True)
    thread.start()