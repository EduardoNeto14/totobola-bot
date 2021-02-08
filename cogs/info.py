import discord
from discord.ext import commands
import pymongo
import asyncio
import logging
import re

logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

class Info(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
        
        file_handler = logging.FileHandler("logs/info.log")
        file_handler.setFormatter(formatter)
        self.logger.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
    
    @commands.command(brief = "**Informação sobre um jogador!**", description = "**Utilização:** `td!player (jogador)`")
    async def player(self, ctx, *args):
        database = pymongo.MongoClient(port = 27017)

        self.logger.info(f"\n[player] {ctx.message.author.display_name} - Args: [{args}]!")

        if len(args) > 0 and len(ctx.message.mentions) > 0:
            team_id = database["totobola"]["jogadores"].find_one({"player_id" : ctx.message.mentions[0].id}, {"_id" : 0, "team_id" : 1})["team_id"]
            
            team = None
            
            if team_id is not None:
                team = database["totobola"]["teams"].find_one({"team_id" : team_id}, {"_id" : 0, "name" : 1, "pontuacao" : 1, "color" : 1})
                embed = discord.Embed(title = "Informação do Jogador", colour = team["color"])

            else:
                embed = discord.Embed(title = "Informação do Jogador", colour = discord.Colour.dark_purple())
            
            competicoes = database["totobola"]["properties"].find_one({}, {"_id" : 0, "competicoes.competicao" : 1})
            
            data_to_send = ""
            
            for comp in competicoes["competicoes"]:
                info = database["totobola"][comp["competicao"]].find_one({"player_id" : ctx.message.mentions[0].id}, {"_id" : 0})
                if info is not None:
                    data_to_send += f":trophy: **{comp['competicao']}**\n"
                    position = database["totobola"][comp["competicao"]].count_documents({"pontuacao" : {"$gt" : info["pontuacao"]}})
                    data_to_send += f"**Posição:** `{position + 1}º` **Pontuação:** `{int(info['pontuacao'])}` **Apostas:** `{int(info['apostas'])}` **Vitórias:** `{int(info['vitorias'])}`\n\n"

            competicoes = database["totobola"]["total"].find_one({"player_id" : ctx.message.mentions[0].id}, {"_id" : 0})
            
            if competicoes is not None:
                data_to_send += f":trophy: **Total**\n"
                position = database["totobola"]["total"].count_documents({"pontuacao" : {"$gt" : info["pontuacao"]}})
                data_to_send += f"**Posição:** `{position + 1}º` **Pontuação:** `{competicoes['pontuacao']}\n\n`"
            
            if team is not None:
                data_to_send += f":trophy: **Equipa:** `{team['name']}` **Pontuação:** `{team['pontuacao']}`\n"

            embed.description = data_to_send
            embed.add_field(name = "Jogador", value = f"`{ctx.message.mentions[0].display_name}`")
            embed.set_thumbnail(url = ctx.message.mentions[0].avatar_url)
            embed.set_footer(text = "Totobola Discordiano", icon_url = logo) 
            await ctx.send(embed = embed)

        elif len(args) == 0:
            team_id = database["totobola"]["jogadores"].find_one({"player_id" : ctx.message.author.id}, {"_id" : 0, "team_id" : 1})["team_id"]
            
            team = None
            
            if team_id is not None:
                team = database["totobola"]["teams"].find_one({"team_id" : team_id}, {"_id" : 0, "name" : 1, "pontuacao" : 1, "color" : 1})
                embed = discord.Embed(title = "Informação do Jogador", colour = team["color"])  # TODO: alterar cor consoante a equipa

            else:
                embed = discord.Embed(title = "Informação do Jogador", colour = discord.Colour.dark_purple())  # TODO: alterar cor consoante a equipa

            competicoes = database["totobola"]["properties"].find_one({}, {"_id" : 0, "competicoes.competicao" : 1})
            # Set footer
            data_to_send = ""
            for comp in competicoes["competicoes"]:
                info = database["totobola"][comp["competicao"]].find_one({"player_id" : ctx.message.author.id}, {"_id" : 0})
                
                if info is not None:
                    data_to_send += f":trophy: **{comp['competicao']}**\n"
                    position = database["totobola"][comp["competicao"]].count_documents({"pontuacao" : {"$gt" : info["pontuacao"]}})
                    data_to_send += f"**Posição:** `{position +1}º` **Pontuação:** `{int(info['pontuacao'])}` **Apostas:** `{int(info['apostas'])}` **Vitórias:** `{int(info['vitorias'])}`\n\n"
            
            competicoes = database["totobola"]["total"].find_one({"player_id" : ctx.message.author.id}, {"_id" : 0})
            
            if competicoes is not None:
                data_to_send += f":trophy: **Total**\n"
                position = database["totobola"]["total"].count_documents({"pontuacao" : {"$gt" : competicoes["pontuacao"]}})
                data_to_send += f"**Posição:** `{position + 1}º` **Pontuação:** `{competicoes['pontuacao']}\n\n`"
                
            if team is not None:
                data_to_send += f":trophy: **Equipa:** `{team['name']}` **Pontuação:** `{team['pontuacao']}`\n"
            
            embed.description = data_to_send
            embed.add_field(name = "Jogador", value = f"`{ctx.message.author.display_name}`")
            embed.set_thumbnail(url = ctx.message.author.avatar_url)
            embed.set_footer(text = "Totobola Discordiano", icon_url = logo) 

            await ctx.send(embed = embed)
        else:
            await ctx.send(":x: **Precisas de mencionar alguém válido!**")
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
            await ctx.send(":x: **Jornada inexistente!**")

        embed = discord.Embed(title = "Jornada", colour = discord.Colour.dark_grey())
        embed.add_field(name = "ID Jornada", value = f"`{jornada['id_jornada']}`")

        jogos = ""
        for jogo in jornada["jogos"]:
            jogos += f":soccer: `{jogo['id_jogo']}`: **{jogo['homeTeam']} - {jogo['awayTeam']}**\n"

        embed.description = jogos
        embed.set_footer(text = "Totobola Discordiano", icon_url = logo)
        await ctx.send(embed = embed)

    async def pages(self, ctx, competicao, msg = None, start = 0, per_page = 10, max = None):
        database = pymongo.MongoClient(port = 27017)

        if max is None:
            max = int(database["totobola"][competicao].count_documents({}) / per_page) + 1
        
        if competicao != "total":
            players = database["totobola"][competicao].aggregate(
                [{"$lookup" : 
                            { "from" : "jogadores", "localField" : "player_id", "foreignField" : "player_id", "as" : "table"}},
                {"$sort" : {"pontuacao" : -1}},
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
                {"$sort" : {"pontuacao" : -1}},
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
                    data_to_send += f"\t\t\t:page_facing_up: **Apostas:** `{int(player['apostas'])}`\t\t\t:information_source: **Média:** `{round(player['pontuacao'] / int(player['apostas']), 2) if int(player['apostas'] != 0) else 'N.D.'}`\n\n"
                else:
                    data_to_send += "\n\n"
            else:
                data_to_send += f"`{p + 1}º` **{player['table']['player_name']}**\n:dart: **Pontuação:** `{player['pontuacao']}`"

                if competicao != "total":
                    data_to_send += f"\t\t\t:page_facing_up: **Apostas:** `{int(player['apostas'])}`\t\t\t:information_source: **Média:** `{round(player['pontuacao'] / int(player['apostas']), 2) if int(player['apostas'] != 0) else 'N.D.'}`\n\n"
                else:
                    data_to_send += "\n\n"

        embed = discord.Embed(title = f"Tabela {competicao}", colour = discord.Colour.dark_magenta())
        embed.description = data_to_send
        embed.set_footer(text = "Totobola Discordiano", icon_url = logo)
        
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
            await msg.delete()
        
        else:
            # redirect on reaction
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.pages(ctx=ctx, competicao=competicao, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.pages(ctx=ctx, competicao=competicao, msg=msg, start=start+1, per_page=per_page, max=max)

    @commands.command(brief = "**Mostra todos os vencedores das jornadas!** *por realizar*", description = "**Utilização:** `td!geraldes`")
    async def geraldes(self, ctx):
        database = pymongo.MongoClient(port = 27017)
        
        if "geraldes" not in database["totobola"].list_collection_names():
            await ctx.send(":x: **Não existem vencedores registados!**")
        else:
            pass
            #await self.win_pages(ctx)
    
    @commands.command(brief = "**Mostra todos os vencedores por jornada!**", description = "**Utilização:** `td!vencedores`")
    async def vencedores(self, ctx):
        database = pymongo.MongoClient(port = 27017)
        
        if "geraldes" not in database["totobola"].list_collection_names():
            await ctx.send(":x: **Não existem vencedores registados!**")
        else:
            await self.win_pages(ctx)

    async def pont_pages(self, ctx, id_jornada, msg = None, start = 0, per_page = 10, max = None):
        database = pymongo.MongoClient(port = 27017)

        if max is None:
            max = int(database["totobola"][id_jornada].count_documents({}) / per_page) + 1

        players = database["totobola"][id_jornada].aggregate(
            [{"$match" : {"status" : {"$ne" : "INATIVA"}}},
            {"$lookup" : 
                        { "from" : "jogadores", "localField" : "player_id", "foreignField" : "player_id", "as" : "table"}},
            {"$sort" : {"pontuacao" : -1}},
            {"$unwind" : "$table"},
            {"$project" :
                        { "player_id" : 1, "table.player_name" : 1, "pontuacao" : 1}},
            {"$limit" : per_page},
            {"$skip" : start*per_page}
        ])
        
        data_to_send = ""
        for p, player in enumerate(players):
            if p + start*per_page < 3:
                medals = [":first_place:", ":second_place:", ":third_place:"]
                data_to_send += f"{medals[p]} **{player['table']['player_name']}**\t\t-\t\t:dart: **Pontuação:** `{player['pontuacao']}`\n\n"
            else:
                data_to_send += f"`{start*per_page + p + 1}º` **{player['table']['player_name']}**\t\t-\t\t:dart: **Pontuação:** `{player['pontuacao']}`\n\n"
        embed = discord.Embed(title = f"Resultados {id_jornada}", colour = discord.Colour.dark_red())
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
            await msg.delete()
        
        else:
            # redirect on reaction
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.pont_pages(ctx=ctx, id_jornada=id_jornada, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.pont_pages(ctx=ctx, id_jornada=id_jornada, msg=msg, start=start+1, per_page=per_page, max=max)

    async def win_pages(self, ctx, msg = None, start = 0, per_page = 5, max = None):
        database = pymongo.MongoClient(port = 27017)

        if max is None:
            max = int(database["totobola"]["geraldes"].count_documents({}) / per_page) + 1

        winners = database["totobola"]["geraldes"].aggregate([
            { "$unwind" : { "path" : "$vencedores", "preserveNullAndEmptyArrays" : True}},
            { "$lookup" : {
                "from" : "jogadores",
                "localField" : "vencedores",
                "foreignField" : "player_id",
                "as" : "vencedores"
            }},
            { "$sort" : {
                "pontuacao" : -1
            }},
            { "$limit" : per_page},
            { "$skip" : start*per_page}
        ])
        
        data_to_send = ""
        for winner in winners:
            data_to_send += f":trophy: `{winner['id_jornada']}`\t\t-\t\t:dart:**Pontuação:** `{winner['pontuacao']}`\n\n"

            for vencedor in winner["vencedores"]:
                data_to_send += f":first_place: **{vencedor['player_name']}**\n"

            data_to_send += "\n"

        embed = discord.Embed(title = "Vencedores", colour = discord.Colour.dark_red())
        embed.description = data_to_send
        embed.set_thumbnail(url = logo)
        embed.set_footer(text = "Totobola Discordiano")
        
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
            await msg.delete()
        
        else:
            # redirect on reaction
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.win_pages(ctx=ctx, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.win_pages(ctx=ctx, msg=msg, start=start+1, per_page=per_page, max=max)
    
    @commands.command(brief = "**Mostra a pontuação de uma jornada!**", description = "**Utilização:** `td!pontuacao [id jornada]`")
    async def pontuacao(self, ctx, id_jornada):
        database = pymongo.MongoClient(port = 27017)
        
        if id_jornada in database["totobola"].list_collection_names():
            await self.pont_pages(ctx, id_jornada = id_jornada)

        else:
            await ctx.send(f":x: **Jornada** `{id_jornada}` **inválida!**")

    @commands.command(brief = "**Verifica os utilizadores que apostaram num determinado resultado!**", description = "**Utilização:** `td!search [id_jogo] [resultado]`")
    async def search(self, ctx, id_jogo, *res):
        database = pymongo.MongoClient(port = 27017)

        id_jogo = int(re.findall(r"\d+", id_jogo)[0])
        # Verifica se existe uma jornada ativa na competição
        jornada = database["totobola"]["jornadas"].find_one( {"estado" : "ATIVA", "jogos" : { "$elemMatch" : {"id_jogo" : id_jogo}}},
                                                            {"_id" : 0, "id_jornada" : 1})

        if jornada is None:
            await ctx.send("**O jogo que indicou não pertence a uma jornada ativa!**")
            return

        res = "".join(res)

        if len(re.findall(r"\d+", res.lower())) == 2:
            players = database["totobola"][jornada["id_jornada"]].aggregate(
                [
                {"$match" : {"apostas" : {"$elemMatch" : {"id_jogo" : int(id_jogo), "resultado" : res}}}},
                {"$lookup" : 
                            { "from" : "jogadores", "localField" : "player_id", "foreignField" : "player_id", "as" : "table"}},
                {"$unwind" : "$table"},
                {"$project" :
                            { "table.player_name" : 1}}
                ]
            )

            counter = 0

            embed = discord.Embed(title="Garotões", colour = discord.Colour.dark_green()) 
            embed.set_thumbnail(url = logo)
            embed.set_footer(text = "Totobola Discordiano")
            embed.add_field(name = "ID Jogo", value = f"`{id_jogo}`")
            embed.add_field(name = "Resultado", value = f"`{res}`")

            names = ""

            for p in players:
                counter += 1
                names += f"**{p['table']['player_name']}**\n"

            if counter == 0:
                names = "**Nenhum jogador apostou nesse resultado!**"
            
            embed.description = names
            await ctx.send(embed = embed)

        else:
            await ctx.send("**Resultado inválido!**")

def setup(client):
    client.add_cog(Info(client))