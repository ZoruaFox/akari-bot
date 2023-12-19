import discord

from bots.discord.client import client
from bots.discord.slash_parser import slash_parser


@client.slash_command(name="locale", description="Set the bot running languages.")
@discord.option(name="lang", default="", description="Supported language codes.")
async def locale(ctx: discord.ApplicationContext, lang: str):
    await slash_parser(ctx, lang)


@client.slash_command(name="mute", description="Make the bot stop sending message.")
async def mute(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "")


@client.slash_command(name="ping", description="Get bot status.")
async def ping(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "")


@client.slash_command(name="petal", description="Get the number of petals in the current channel.")
async def petal(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "")


@client.slash_command(name="version", description="View bot version.")
async def version(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "")


@client.slash_command(name="whoami", description="Get the ID of the user account that sent the command inside the bot.")
async def whoami(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "")


admin = client.create_group("admin", "Commands available to bot administrators.")


@admin.command(name="add", description="Set members as bot administrators.")
@discord.option(name="userid", description="The user ID.")
async def add(ctx: discord.ApplicationContext, userid: str):
    await slash_parser(ctx, f"add {userid}")


@admin.command(name="remove", description="Remove bot administrator from member.")
@discord.option(name="userid", description="The user ID.")
async def remove(ctx: discord.ApplicationContext, userid: str):
    await slash_parser(ctx, f"remove {userid}")


@admin.command(name="list", description="View all bot administrators.")
async def lst(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "list")


@admin.command(name="ban", description="Limit someone to use bot in the channel.")
@discord.option(name="userid", description="The user ID.")
async def ban(ctx: discord.ApplicationContext, userid: str):
    await slash_parser(ctx, f"ban {userid}")


@admin.command(name="unban", description="Remove limit someone to use bot in the channel.")
@discord.option(name="userid", description="The user ID.")
async def unban(ctx: discord.ApplicationContext, userid: str):
    await slash_parser(ctx, f"unban {userid}")
    

ali = client.create_group("alias", "Set custom command alias.")


@ali.command(name="add", description="Add custom command alias.")
@discord.option(name="alias", description="The custom alias.")
@discord.option(name="command", description="The command you want to refer to.")
async def add(ctx: discord.ApplicationContext, alias: str, command: str):
    await slash_parser(ctx, f"add {alias} {command}")


@ali.command(name="remove", description="Remove custom command alias.")
@discord.option(name="alias", description="The custom alias.")
async def remove(ctx: discord.ApplicationContext, alias: str):
    await slash_parser(ctx, f"remove {alias}")


@ali.command(name="list", description="View custom command alias.")
async def lst(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "list")


@ali.command(name="reset", description="Reset custom command alias.")
async def reset(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "reset")


hlp = client.create_group("help", "Get bot help.")


@hlp.command(name="list", description="View help list.")
@discord.option(name="legacy", choices=[('true', 'legacy'), ('false', '')], description="Whether to use legacy mode.")
async def lst(ctx: discord.ApplicationContext, legacy: str):
    await slash_parser(ctx, legacy)


@hlp.command(name="detail", description="View details of a module.")
@discord.option(name="module", default="", description="The module you want to know about.")
async def detail(ctx: discord.ApplicationContext, legacy: str):
    await slash_parser(ctx, legacy)


@hlp.command(name="detail", description="View details of a module.")
@discord.option(name="module", default="", description="The module you want to know about.")
async def detail(ctx: discord.ApplicationContext, module: str):
    await slash_parser(ctx, module)


m = client.create_group("module", "Set about modules.")


@m.command(name="enable", description="Enable module.")
@discord.option(name="module", description="The module name.")
async def add(ctx: discord.ApplicationContext, module: str):
    await slash_parser(ctx, f"enable {module}")


@m.command(name="disable", description="Disable module.")
@discord.option(name="module", description="The module name.")
async def add(ctx: discord.ApplicationContext, module: str):
    await slash_parser(ctx, f"disable {module}")


@m.command(name="list", description="View all available modules.")
async def lst(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "list")


p = client.create_group("prefix", "Set custom command prefix.")


@p.command(name="add", description="Add custom command prefix.")
@discord.option(name="prefix", description="The custom prefix.")
async def add(ctx: discord.ApplicationContext, prefix: str):
    await slash_parser(ctx, f"add {prefix}")


@p.command(description="Remove custom command prefix.")
@discord.option(name="remove", name="prefix", description="The custom prefix.")
async def remove(ctx: discord.ApplicationContext, prefix: str):
    await slash_parser(ctx, f"remove {prefix}")


@p.command(name="list", description="View custom command prefix.")
async def lst(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "list")


@p.command(name="reset", description="Reset custom command prefix.")
async def reset(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "reset")


setup = client.create_group("setup", "Set up bot actions.")


@setup.command(name="typing", description="Set up whether to display input prompts.")
async def typing(ctx: discord.ApplicationContext):
    await slash_parser(ctx, "typing")


@setup.command(name="timeoffset", description="Set the time offset.")
@discord.option(name="offset", description="The timezone offset.")
async def offset(ctx: discord.ApplicationContext, offset: str):
    await slash_parser(ctx, f"timeoffset {offset}")
