import discord
from discord.ext import commands
import time

AUTHORIZED_DEVS = {
    1255287940775678048
}

dev_mode_users = set()
cooldowns = {}

def setup(bot: commands.Bot):

    @bot.command()
    async def devmode(ctx, mode: str):
        user_id = ctx.author.id

        if user_id not in AUTHORIZED_DEVS:
            await ctx.send("❌ You are not authorized to use dev mode.")
            return

        if mode.lower() == "on":
            dev_mode_users.add(user_id)
            await ctx.send("🛠️ Dev mode enabled. Go fight those bugs.")

        elif mode.lower() == "off":
            dev_mode_users.discard(user_id)
            await ctx.send("✅ Dev mode disabled. Welcome back to society.")

        else:
            await ctx.send("Use `!$devmode on` or `!$devmode off`")

async def handle_devmode(message: discord.Message):
    if message.author.bot:
        return False

    triggered_dev = None

    for user in message.mentions:
        if user.id in dev_mode_users:
            triggered_dev = user
            break

    if not triggered_dev and message.reference:
        try:
            replied_msg = await message.channel.fetch_message(
                message.reference.message_id
            )
            if replied_msg.author.id in dev_mode_users:
                triggered_dev = replied_msg.author
        except:
            pass

    if triggered_dev:
        now = time.time()

        if (
            triggered_dev.id in cooldowns
            and now - cooldowns[triggered_dev.id] < 10
        ):
            return True

        cooldowns[triggered_dev.id] = now

        await message.reply(
            "⚔️ They are currently fighting a war against bugs and won't be seen for a few hours..."
        )

        try:
            await triggered_dev.send(
                f"📩 You were pinged/replied to by {message.author} in {message.guild.name}:\n\n"
                f"{message.content}"
            )
        except:
            pass

        return True

    return False