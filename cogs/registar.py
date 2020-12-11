import discord
from discord.ext import commands

import pymongo

class Registar(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def registar(self, ctx, *args):
        user = await self.client.fetch_user(ctx.author.id)
        await user.send("Registado!")
        #await ctx.send(ctx.author.id)


def setup(client):
    client.add_cog(Registar(client))