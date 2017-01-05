import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os
import asyncio


default_greeting = "**Welcome {0.mention} to {1.name}!** :smiley:"
default_leave = "**{0.name} has left {1.name}!** :frowning:"
default_settings = {"GREETING": default_greeting, "LEAVEMSG": default_leave, "ON": False, "CHANNEL": None, "WHISPER" : False}

class Welcome:
    """Welcomes new members to the server in the default channel"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/welcome/settings.json", "load")


    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def welcomeset(self, ctx):
        """Sets welcome module settings"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO("data/welcome/settings.json","save",self.settings)
        if ctx.invoked_subcommand is None:
            msg = discord.Embed(description="""?welcomeset

Sets welcome module settings

Commands:
  channel  Sets the channel to send the welcome message
  greeting Sets the welcome message format for the server.
  toggle   Turns on/off welcoming new users to the server
  whisper  Sets whether or not a DM is sent to the new user""", colour=discord.Colour.blue())
            msg.add_field(name="Settings", value="GREETING: {}\nLEAVEMSG: {}\nCHANNEL: #{}\nON: {}\nWHISPER: {}\n".format(self.settings[server.id]["GREETING"], self.settings[server.id]["LEAVEMSG"], self.get_welcome_channel(server), self.settings[server.id]["ON"], self.settings[server.id]["WHISPER"]), inline=False)
            await self.bot.say(embed=msg)

    @welcomeset.command(pass_context=True)
    async def greeting(self, ctx, *, format_msg):
        """Sets the welcome message format for the server.

        {0} is user
        {1} is server
        Default is set to: 
            Welcome {0.name} to {1.name}!

        Example formats:
            {0.mention}.. What are you doing here?
            {1.name} has a new member! {0.name}#{0.discriminator} - {0.id}
            Someone new joined! Who is it?! D: IS HE HERE TO HURT US?!
        """
        server = ctx.message.server
        self.settings[server.id]["GREETING"] = format_msg
        fileIO("data/welcome/settings.json","save",self.settings)
        await self.bot.say("Welcome message set for the server.")
        await self.send_testing_msg(ctx)

    @welcomeset.command(pass_context=True)
    async def leavemsg(self, ctx, *, format_msg):
        """Sets the leave msg for users that leave the server.

        {0} is user
        {1} is server
        Default is set to: 
            {0.name}  has left {1.name}!

        Example formats:
            {1.name} has lost a member! {0.name}#{0.discriminator} - {0.id}!"""
        server = ctx.message.server
        self.settings[server.id]["LEAVEMSG"] = format_msg
        fileIO("data/welcome/settings.json","save",self.settings)
        await self.bot.say("Leave message set for the server.")
        await self.send_testing_msg2(ctx)

    @welcomeset.command(pass_context=True)
    async def toggle(self, ctx):
        """Turns on/off welcoming\leaving new users to the server"""
        server = ctx.message.server
        self.settings[server.id]["ON"] = not self.settings[server.id]["ON"]
        if self.settings[server.id]["ON"]:
            await self.bot.say("I will now welcome new users and annouce leaving users to the server.")
            await self.send_testing_msg(ctx)
            await self.send_testing_msg2(ctx)
        else:
            await self.bot.say("I will no longer welcome new users.")
        fileIO("data/welcome/settings.json", "save", self.settings)

    @welcomeset.command(pass_context=True)
    async def channel(self, ctx, channel : discord.Channel=None): 
        """Sets the channel to send the welcome message

        If channel isn't specified, the server's default channel will be used"""
        server = ctx.message.server
        if channel == None:
            channel = ctx.message.server.default_channel
        if not server.get_member(self.bot.user.id).permissions_in(channel).send_messages:
            await self.bot.say("I do not have permissions to send messages to {0.mention}".format(channel))
            return
        self.settings[server.id]["CHANNEL"] = channel.id
        fileIO("data/welcome/settings.json", "save", self.settings)
        channel = self.get_welcome_channel(server)
        await self.bot.send_message(channel,"I will now send welcome messages to {0.mention}".format(channel))
        await self.send_testing_msg(ctx)

    @welcomeset.command(pass_context=True)
    async def whisper(self, ctx, choice : str=None): 
        """Sets whether or not a DM is sent to the new user
        
        Options:
            off - turns off DMs to users
            only - only send a DM to the user, don't send a welcome to the channel
            both - send a message to both the user and the channel

        If Option isn't specified, toggles between 'off' and 'only'"""
        options = {"off": False, "only": True, "both": "BOTH"}
        server = ctx.message.server
        if choice == None:
            self.settings[server.id]["WHISPER"] = not self.settings[server.id]["WHISPER"]
        elif choice.lower() not in options:
            await send_cmd_help(ctx)
            return
        else:
            self.settings[server.id]["WHISPER"] = options[choice.lower()]
        fileIO("data/welcome/settings.json", "save", self.settings)
        channel = self.get_welcome_channel(server)
        if not self.settings[server.id]["WHISPER"]:
            await self.bot.say("I will no longer send DMs to new users")
        elif self.settings[server.id]["WHISPER"] == "BOTH":
            await self.bot.send_message(channel,"I will now send welcome messages to {0.mention} as well as to the new user in a DM".format(channel))
        else:
            await self.bot.send_message(channel,"I will now only send welcome messages to the new user as a DM".format(channel))
        await self.send_testing_msg(ctx)


    async def member_join(self, member):
        server = member.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO("data/welcome/settings.json","save",self.settings)
        if not self.settings[server.id]["ON"]:
            return
        if server == None:
            print("Server is None. Private Message or some new fangled Discord thing?.. Anyways there be an error, the user was {}".format(member.name))
            return
        channel = self.get_welcome_channel(server)
        if channel is None:
            print('welcome.py: Channel not found. It was most likely deleted. User joined: {}'.format(member.name))
            return
        if self.settings[server.id]["WHISPER"]:
            await self.bot.send_message(member, self.settings[server.id]["GREETING"].format(member, server))
        if self.settings[server.id]["WHISPER"] != True and self.speak_permissions(server):
            await self.bot.send_message(channel, self.settings[server.id]["GREETING"].format(member, server))
        else:
            print("Permissions Error. User that joined: {0.name}".format(member))
            print("Bot doesn't have permissions to send messages to {0.name}'s #{1.name} channel".format(server,channel))

    async def member_remove(self, member):
        server = member.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            self.settings[server.id]["CHANNEL"] = server.default_channel.id
            fileIO("data/welcome/settings.json","save",self.settings)
        if not self.settings[server.id]["ON"]:
            return
        if server == None:
            print("Server is None. Private Message or some new fangled Discord thing?.. Anyways there be an error, the user was {}".format(member.name))
            return
        channel = self.get_welcome_channel(server)
        if channel is None:
            print('welcome.py: Channel not found. It was most likely deleted. User joined: {}'.format(member.name))
            return
        if self.settings[server.id]["WHISPER"]:
            await self.bot.send_message(member, self.settings[server.id]["LEAVEMSG"].format(member, server))
        if self.settings[server.id]["WHISPER"] != True and self.speak_permissions(server):
            await self.bot.send_message(channel, self.settings[server.id]["LEAVEMSG"].format(member, server))
        else:
            print("Permissions Error. User that joined: {0.name}".format(member))
            print("Bot doesn't have permissions to send messages to {0.name}'s #{1.name} channel".format(server,channel))

    def get_welcome_channel(self, server):
        try:
            return server.get_channel(self.settings[server.id]["CHANNEL"])
        except:
            return None

    def speak_permissions(self, server):
        channel = self.get_welcome_channel(server)
        if channel is None:
            return False
        return server.get_member(self.bot.user.id).permissions_in(channel).send_messages

    async def send_testing_msg(self, ctx):
        server = ctx.message.server
        channel = self.get_welcome_channel(server)
        if channel is None:
            await self.bot.send_message(ctx.message.channel, "I can't find the specified channel. It might have been deleted.")
            return
        await self.bot.send_message(ctx.message.channel, "`Sending a testing message to `{0.mention}".format(channel))
        if self.speak_permissions(server):
            if self.settings[server.id]["WHISPER"]:
                await self.bot.send_message(ctx.message.author, self.settings[server.id]["GREETING"].format(ctx.message.author,server))
            if self.settings[server.id]["WHISPER"] != True:
                await self.bot.send_message(channel, self.settings[server.id]["GREETING"].format(ctx.message.author,server))
        else: 
            await self.bot.send_message(ctx.message.channel,"I do not have permissions to send messages to {0.mention}".format(channel))

    async def send_testing_msg2(self, ctx):
        server = ctx.message.server
        channel = self.get_welcome_channel(server)
        if channel is None:
            await self.bot.send_message(ctx.message.channel, "I can't find the specified channel. It might have been deleted.")
            return
        await self.bot.send_message(ctx.message.channel, "`Sending a testing message to `{0.mention}".format(channel))
        if self.speak_permissions(server):
            if self.settings[server.id]["CHANNEL"] != True:
                await self.bot.send_message(channel, self.settings[server.id]["LEAVEMSG"].format(ctx.message.author,server))
        else: 
            await self.bot.send_message(ctx.message.channel,"I do not have permissions to send messages to {0.mention}".format(channel))
        

def check_folders():
    if not os.path.exists("data/welcome"):
        print("Creating data/welcome folder...")
        os.makedirs("data/welcome")

def check_files():
    f = "data/welcome/settings.json"
    if not fileIO(f, "check"):
        print("Creating welcome settings.json...")
        fileIO(f, "save", {})
    else: #consistency check
        current = fileIO(f, "load")
        for k,v in current.items():
            if v.keys() != default_settings.keys():
                for key in default_settings.keys():
                    if key not in v.keys():
                        current[k][key] = default_settings[key]
                        print("Adding " + str(key) + " field to welcome settings.json")
        fileIO(f, "save", current)

def setup(bot):
    check_folders()
    check_files()
    n = Welcome(bot)
    bot.add_listener(n.member_join,"on_member_join")
    bot.add_listener(n.member_remove, "on_member_remove")
    bot.add_cog(n)
