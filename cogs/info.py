import discord
from discord.ext import commands
import pymongo

class Info(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def player(self, ctx, *args):
        database = pymongo.MongoClient(port = 27017)

        if len(args) > 0 and len(ctx.message.mentions) > 0:
            embed = discord.Embed(title = "Informação do Jogador", colour = discord.Colour.dark_purple())  # TODO: alterar cor consoante a equipa
            competicoes = database["totobola"]["properties"].find_one({}, {"_id" : 0, "competicoes.competicao" : 1})
            print(competicoes)
            # Ir buscar team id e cor, se tiver equipa
            # Verificar posição com count_documents e $gt
            # Set footer
            data_to_send = ""
            for comp in competicoes["competicoes"]:
                info = database["totobola"][comp["competicao"]].find_one({"player_id" : ctx.message.mentions[0].id}, {"_id" : 0})
                print(info)
                if info is not None:
                    data_to_send += f":trophy: **{comp['competicao']}**\n"
                    data_to_send += f"**Posição:** `1º` **Pontuação:** `{info['pontuacao']}` **Apostas:** `{info['apostas']}`\n\n"
            
            embed.description = data_to_send
            embed.add_field(name = "Jogador", value = f"`{ctx.message.mentions[0].display_name}`")
            embed.set_thumbnail(url = ctx.message.mentions[0].avatar_url)
            await ctx.send(embed = embed)

        elif len(args) == 0:
            embed = discord.Embed(title = "Informação do Jogador", colour = discord.Colour.dark_purple())  # TODO: alterar cor consoante a equipa
            competicoes = database["totobola"]["properties"].find_one({}, {"_id" : 0, "competicoes.competicao" : 1})
            print(competicoes)
            # Ir buscar team id e cor, se tiver equipa
            # Verificar posição com count_documents e $gt
            # Set footer
            data_to_send = ""
            for comp in competicoes["competicoes"]:
                info = database["totobola"][comp["competicao"]].find_one({"player_id" : ctx.message.author.id}, {"_id" : 0})
                print(info)
                if info is not None:
                    data_to_send += f":trophy: **{comp['competicao']}**\n"
                    data_to_send += f"**Posição:** `1º` **Pontuação:** `{info['pontuacao']}` **Apostas:** `{info['apostas']}`\n\n"
            
            embed.description = data_to_send
            embed.add_field(name = "Jogador", value = f"`{ctx.message.author.display_name}`")
            embed.set_thumbnail(url = ctx.message.author.avatar_url)
            await ctx.send(embed = embed)
        else:
            await ctx.send("meh")
        pass

    @commands.command()
    async def jornadas(self, ctx, competicao):
        database = pymongo.MongoClient(port = 27017)
        jornadas = database["totobola"]["jornadas"].find({"competicao" : competicao}, {"_id" : 0, "id_jornada" : 1, "estado" : 1})

        if competicao not in database["totobola"].list_collection_names():
            await ctx.send(":x: Competição inválida!")
            return

        str_jornadas = f"Jornadas: **{competicao}**\n\n"
        
        for jornada in jornadas:
            if jornada["estado"] == "ATIVA":
                str_jornadas += f":ticket: :green_circle: `{jornada['id_jornada']}`\n"
            elif jornada["estado"] == "TERMINADA":
                str_jornadas += f":ticket: :red_circle: `{jornada['id_jornada']}`\n"

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