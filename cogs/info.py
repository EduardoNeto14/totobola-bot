import discord
from discord.ext import commands

class Info(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def player(self, ctx, *args):
        pass

    #@commands.command()
    #async def aposta(self, ctx, id_jornada):
    #    pass

    @commands.command()
    async def jornadas(self, ctx, competicao):
        pass
    
    @commands.command()
    async def table(self, ctx, competicao):
        pass

    @commands.command()
    async def jogos(self, ctx, competicao):
        pass

def setup(client):
    client.add_cog(Info(client))