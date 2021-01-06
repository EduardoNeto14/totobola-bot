import discord
from discord.ext import commands
import pymongo
import asyncio

class Info(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(brief = "**Informação sobre um jogador!**", description = "**Utilização:** `td!player (jogador)`")
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
                    data_to_send += f"**Posição:** `1º` **Pontuação:** `{info['pontuacao']}` **Apostas:** `{int(info['apostas'])}`\n\n"

            competicoes = database["totobola"]["total"].find_one({"player_id" : ctx.message.mentions[0].id}, {"_id" : 0})
            
            if competicoes is not None:
                data_to_send += f":trophy: **Total**\n"
                data_to_send += f"**Posição:** `1º` **Pontuação:** `{competicoes['pontuacao']}\n\n`"
            
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
                    data_to_send += f"**Posição:** `1º` **Pontuação:** `{info['pontuacao']}` **Apostas:** `{int(info['apostas'])}`\n\n"
            
            competicoes = database["totobola"]["total"].find_one({"player_id" : ctx.message.author.id}, {"_id" : 0})
            
            if competicoes is not None:
                data_to_send += f":trophy: **Total**\n"
                data_to_send += f"**Posição:** `1º` **Pontuação:** `{competicoes['pontuacao']}\n\n`"

            embed.description = data_to_send
            embed.add_field(name = "Jogador", value = f"`{ctx.message.author.display_name}`")
            embed.set_thumbnail(url = ctx.message.author.avatar_url)

            await ctx.send(embed = embed)
        else:
            await ctx.send("meh")
        pass

    @commands.command(brief = "**Mostra todas as jornadas de uma competição!**", description = "**Utilização:** `td!jornadas [competição]`")
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

    @commands.command(brief = "**Mostra a tabela de uma determinada competição!**", description = "**Utilização:** `td!table [competição]`")
    async def table(self, ctx, competicao):
        database = pymongo.MongoClient(port = 27017)

        if competicao in database["totobola"].list_collection_names():
            await self.pages(ctx = ctx, competicao = competicao)
        else:
            await ctx.send(":x: Competição não existe!")

    @commands.command(brief = "**Mostra os jogdos de uma jornada ativa de uma competição!**", description = "**Utilização:** `td!jogos [competição]`")
    async def jogos(self, ctx, competicao):
        database = pymongo.MongoClient(port = 27017)
        jornada = database["totobola"]["jornadas"].find_one( {"estado" : "ATIVA", "competicao" : competicao}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})

        if jornada is None:
            await ctx.send("Jornada inexistente!")

        jogos = f"ID Jornada: `{jornada['id_jornada']}`\n\n"

        for jogo in jornada["jogos"]:
            jogos += f":soccer: `{jogo['id_jogo']}`: **{jogo['homeTeam']} - {jogo['awayTeam']}**\n"

        await ctx.send(jogos)

    async def pages(self, ctx, competicao, msg = None, start = 0, per_page = 10, max = None):
        database = pymongo.MongoClient(port = 27017)

        if max is None:
            max = int(database["totobola"][competicao].count_documents({}) / per_page) + 1
        
        if competicao != "total":
            players = database["totobola"][competicao].aggregate(
                [{"$lookup" : 
                            { "from" : "jogadores", "localField" : "player_id", "foreignField" : "player_id", "as" : "table"}},
                {"$sort" : {"pontuacao" : 1}},
                {"$unwind" : "$table"},
                {"$project" :
                            { "player_id" : 1, "table.player_name" : 1, "pontuacao" : 1, "apostas" : 1}},
                {"$limit" : per_page},
                {"$skip" : start*per_page}
            ])
        else:
            players = database["totobola"][competicao].aggregate(
                [{"$lookup" : 
                            { "from" : "jogadores", "localField" : "player_id", "foreignField" : "player_id", "as" : "table"}},
                {"$sort" : {"pontuacao" : 1}},
                {"$unwind" : "$table"},
                {"$project" :
                            { "player_id" : 1, "table.player_name" : 1, "pontuacao" :1}},
                {"$limit" : per_page},
                {"$skip" : start*per_page}
            ])

        data_to_send = ""
        for p, player in enumerate(players):
            if p + start*per_page < 3:
                medals = [":first_place:", ":second_place:", ":third_place:"]
                data_to_send += f"{medals[p]} **{player['table']['player_name']}**\n:dart: **Pontuação:** `{player['pontuacao']}`"

                if competicao != "total":
                    data_to_send += f"\t\t\t:page_facing_up: **Apostas:** `{int(player['apostas'])}`\n"
                else:
                    data_to_send += "\n"
            else:
                data_to_send += f"`{p + 1}º` **{player['table']['player_name']}**\n:dart: **Pontuação:** `{player['pontuacao']}`"

                if competicao != "total":
                    data_to_send += f"\t\t\t:page_facing_up: **Apostas:** `{int(player['apostas'])}`\n"
                else:
                    data_to_send += "\n"

        embed = discord.Embed(title = f"Tabela {competicao}", colour = discord.Colour.dark_magenta())
        embed.description = data_to_send

        if msg is not None:
            await msg.edit(embed=embed)
            if not isinstance(msg.channel, discord.abc.PrivateChannel):
                await msg.clear_reactions()
        else:
            msg = await ctx.send(embed=embed)
        
        if start > 0:
            await msg.add_reaction('⏪')
        if start < max - 1:
            await msg.add_reaction('⏩')

        # wait for reactions (2 minutes)
        def check(reaction, user):
            return True if user != self.client.user and str(reaction.emoji) in ['⏪', '⏩'] and reaction.message.id == msg.id else False
        
        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=120, check=check)
        except asyncio.TimeoutError:
            pass
        
        else:
            # redirect on reaction
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.pages(ctx=ctx, competicao=competicao, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.pages(ctx=ctx, competicao=competicao, msg=msg, start=start+1, per_page=per_page, max=max)

    @commands.command(brief = "**Mostra todos os vencedores da jornada!**", description = "**Utilização:** `td!geraldes`")
    async def geraldes(self, ctx):
        print("Mostrar os vencedores!")

def setup(client):
    client.add_cog(Info(client))