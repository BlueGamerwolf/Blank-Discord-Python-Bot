import discord

def setup(bot):

    @bot.event
    async def on_message(message):

        if message.author.bot:
            return

        if message.content.lower() == "hello":
            await message.channel.send(f"Hello! {message.author.mention}")
        await bot.process_commands(message)
    
    
    @bot.event
    async def on_message(message):

        if message.author.bot:
            return

        banned_words = [
            "fuck",
            "shit",
            "bitch",
            "asshole",
            "nigga",
            "cunt",
            "faggot",
            "fag",
            "nigger",
            "retard",
            "wanker",
            "cock",
            "cocksucker",
            "prick",
            "go to hell",
            "wtf"
        ]

        if any(word in message.content.lower() for word in banned_words):
            await message.delete()

            warning = await message.channel.send(
                f"{message.author.mention}, that word is not allowed."
            )

            await warning.delete(delay=5)
            return

        await bot.process_commands(message)