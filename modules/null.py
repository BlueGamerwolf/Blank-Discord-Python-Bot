import discord
from discord.ext import commands

ROLE_ID = 1485086830998323260

def setup(bot):

    @bot.command(name="refreshchannel")
    async def refresh_channel(ctx, channel_id: str = None):

        # Permission check
        if not any(role.id == ROLE_ID for role in ctx.author.roles):
            return await ctx.send(
                "❌ You do not have permission to use this command.",
                delete_after=10
            )

        if channel_id is None:
            return await ctx.send(
                "❌ Usage: `!refreshchannel <channel_id>`",
                delete_after=10
            )

        try:
            # Handle channel mentions like <#123456789>
            channel_id = channel_id.replace("<#", "").replace(">", "")

            old_channel = ctx.guild.get_channel(int(channel_id))

            if old_channel is None:
                return await ctx.send(
                    "❌ Channel not found.",
                    delete_after=10
                )

            # Clone channel (copies permissions/settings)
            new_channel = await old_channel.clone(
                reason=f"Channel refreshed by {ctx.author}"
            )

            # Keep original position/category
            try:
                await new_channel.edit(
                    position=old_channel.position,
                    category=old_channel.category
                )
            except Exception:
                pass

            # Delete old channel
            await old_channel.delete(
                reason=f"Channel refreshed by {ctx.author}"
            )

            # Notify if channel supports messages
            try:
                await new_channel.send(
                    f"✅ Channel refreshed by {ctx.author.mention}"
                )
            except Exception:
                pass

            try:
                await ctx.send(
                    f"✅ Successfully refreshed `{new_channel.name}`",
                    delete_after=10
                )
            except Exception:
                pass

        except ValueError:
            await ctx.send(
                "❌ Invalid channel ID.",
                delete_after=10
            )

        except discord.Forbidden:
            await ctx.send(
                "❌ I don't have permission to manage that channel.",
                delete_after=10
            )

        except Exception as e:
            await ctx.send(
                f"❌ Error: `{e}`",
                delete_after=10
            )