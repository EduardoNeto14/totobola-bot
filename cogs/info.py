import discord
from discord.ext import commands
import pymongo

class Info(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def player(self, ctx, *args):
        pass

    @commands.command()
    async def jornadas(self, ctx, competicao):
        database = pymongo.MongoClient(port = 27017)
        jornadas = database["totobola"]["jornadas"].find({"competicao" : competicao}, {"_id" : 0, "id_jornada" : 1})

        if competicao not in database["totobola"].list_collection_names():
            await ctx.send(":x: Competição inválida!")
            return

        str_jornadas = f"Jornadas: **{competicao}**\n\n"
        
        for jornada in jornadas:
            str_jornadas += f":ticket: `{jornada['id_jornada']}`\n"
        
        await ctx.send(str_jornadas)

    @commands.command()
    async def table(self, ctx, competicao):
        pass

    @commands.command()
    async def jogos(self, ctx, competicao):
        database = pymongo.MongoClient(port = 27017)
        jornada = database["totobola"]["jornadas"].find_one( {"estado" : "ATIVA", "competicao" : competicao}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})

        if jornada is None:
            await ctx.send("Jornada inexistente!")

        jogos = f"ID Jornada: `{jornada['id_jornada']}`\n\n"

        for jogo in jornada["jogos"]:
            jogos += f":soccer: `{jogo['id_jogo']}`: **{jogo['homeTeam']} - {jogo['awayTeam']}**\n"

        await ctx.send(jogos)

def setup(client):
    client.add_cog(Info(client))