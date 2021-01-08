import discord
from discord.ext import commands
import pymongo
import sys
import json
import asyncio
import re

PATH = "/home/eduardo/HDD/Development/Totobola"
logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

sys.path.append(f"{PATH}/utils")

from utils import is_admin, is_comp, is_comp_not
from results import calculate

async def database_exists(ctx):
    database = pymongo.MongoClient(port = 27017)

    if "totobola" in database.list_database_names() : return False

    return True

class Totobola(commands.Cog):

    def __init__(self, client):
        self.client = client
    
    @commands.command(brief = "**Inicia o Totobola Discordiano!**", description = "**Utilização:** `td!totobola (competições)`")
    @commands.check(database_exists)
    async def totobola(self, ctx, *args):
        database = pymongo.MongoClient(port = 27017)
        
        properties = {
                        "admin" : [ctx.message.author.id],
                        "channel" : None,
                        "competicoes" : []
                     }

        for arg in args:
            properties["competicoes"].append({"competicao" : arg, "link" : None, "name" : None})
            
        print(properties)
        totobola = database["totobola"]
        totobola["properties"].insert_one(properties)

        # TODO : Melhorar mensagem #
        embed = discord.Embed(title = "Registo", colour = discord.Colour.dark_gold())
        embed.set_thumbnail(url = logo)
        embed.description = f"Para te registares na prova, basta clicares no :writing_hand:.\n\n*Utiliza o comando td!canal para anexares o bot a um canal!*\n"
        embed.set_footer(text = "Totobola Discordiano")

        message = await ctx.send(embed = embed)
        
        await message.add_reaction("✍")
        await message.pin()

        totobola["registo"].insert_one({
            "message_id" : message.id
        })

        await ctx.invoke(self.client.get_command("canal"))

    @commands.command(brief = "**Adiciona um administrador!**", description = "**Utilização:** `td!admin [jogador]`")
    @commands.check(is_admin)
    async def admin(self, ctx, mention):
        database = pymongo.MongoClient(port= 27017)
        properties = database["totobola"]["properties"]
        
        p = properties.find_one()
        properties.update_one({"_id" : p["_id"]}, {"$push" : {"admin" : ctx.message.mentions[0].id}})

        embed = discord.Embed(title="Administrador", colour = discord.Colour.magenta())
        embed.set_footer(text = "Totobola Discordiano", icon_url = logo)
        embed.set_thumbnail(url = ctx.message.mentions[0].avatar_url)
        embed.add_field(name = "Admin", value = f"```{ctx.message.mentions[0].display_name}```")
        embed.add_field(name = "Estado", value = "```Ativo```")

        await ctx.send(embed = embed)

    @commands.command(brief = "**Adiciona uma competição!**", description = "**Utilização:** `td!add [competição]`")
    @commands.check(is_admin)
    @commands.check(is_comp)
    async def add(self, ctx, comp):
        database = pymongo.MongoClient(port = 27017)
        database["totobola"]["properties"].update(database["totobola"]["properties"].find_one({}, {"_id": 1}), {"$push" : {"competicoes" : {"competicao" : comp, "link" : None, "name" : None}}})

        for player in database["totobola"]["jogadores"].find({} , {"player_id" : 1, "_id" : 0}):
            database["totobola"][comp].insert_one({"player_id" : player["player_id"], "pontuacao" : 0, "apostas" : 0, "vitorias" : 0})
            database["totobola"]["total"].update_one({"player_id" : player["player_id"]}, {"$push" : {"p_competicoes" : {"competicao" : comp, "pontuacao" : 0 }}})

        await ctx.send(f":trophy: **Competição {comp} adicionada com sucesso!**")

    @commands.command(brief = "**Relaciona uma competição com uma liga!**", description = "**Utilização:** `td!link [competição] [liga]`")
    @commands.check(is_admin)
    @commands.check(is_comp_not)
    async def link(self, ctx, comp, link):
        with open(f"{PATH}/football/leagues.json", "r") as leagues:
            leagues = json.load(leagues)

        if link.upper() in leagues:
            database = pymongo.MongoClient(port = 27017)
            database["totobola"]["properties"].update({"competicoes.competicao" : comp}, { "$set" : {"competicoes.$.link" : leagues[link.upper()]['id'], "competicoes.$.name" : leagues[link.upper()]['name']}})

            await ctx.send(f":link: **{comp}** conectado a **{leagues[link.upper()]['name']}**!")

        else:
            await ctx.send(":x: O código dessa competição não existe!")

    @commands.command(brief = "**Verifica as ligas disponíveis!**", description = "**Utilização:** `td!ligas`")
    @commands.check(is_admin)
    async def ligas(self, ctx):
        with open(f"{PATH}/football/leagues.json", "r") as leagues:
            leagues = json.load(leagues)

        l = ""
        for code, league in leagues.items():
            l += f":soccer: **{code}** - {league['name']}\n"
        
        await ctx.send(l)

    @commands.command(brief = "**Verifica as competições existentes no Totobola!**", description = "**Utilização:** `td!competicoes`")
    @commands.check(is_admin)
    async def competicoes(self, ctx):
        database = pymongo.MongoClient(port = 27017)
        
        competicoes = database["totobola"]["properties"].find_one({}, {"_id" : 0, "competicoes" : 1})
        comps = ""

        for competicao in competicoes["competicoes"]:
            print(competicao)
            comps += f":soccer: **{competicao['competicao']}** - {competicao['name']}\n"

        await ctx.send(comps)

    @commands.command(brief = "**Liga o bot a um canal. Utilizar no canal pretendido!**", description = "**Utilização:** `td!canal`")
    @commands.check(is_admin)
    async def canal(self, ctx):
        database = pymongo.MongoClient(port = 27017)
        database["totobola"]["properties"].update({}, {"$set" : {"channel" : ctx.channel.id}})

        if (database["totobola"]["properties"].count_documents({"channel" : ctx.channel.id}) > 0):
            await ctx.send(":white_check_mark: Canal adicionado com sucesso!")

    @commands.command(brief = "**Mostra todos os comandos!**", description = "**Utilização:** `td!help (comando)`")
    async def help(self, ctx):
        await self.pages(ctx = ctx)

    async def pages(self, ctx, msg = None, start = 0, per_page = 5, max = None):
        if max is None:
            max = int(len(self.client.commands) / per_page) + 1

        data_to_send = ""
        for c, command in enumerate(self.client.commands):
            if c >= start*per_page and c < start*per_page + per_page:
                data_to_send += f":reminder_ribbon:\t\ttd!{command.name}\n{command.brief}\n{command.description}\n\n"
        
        embed = discord.Embed(title = "Comandos", colour = discord.Colour.lighter_grey())
        embed.description = data_to_send

        if msg is not None:
            await msg.edit(embed = embed)
            if not isinstance(msg.channel, discord.abc.PrivateChannel):
                await msg.clear_reactions()
        else:
            msg = await ctx.send(embed = embed)

        if start > 0:
            await msg.add_reaction('⏪')
        if start < max - 1:
            await msg.add_reaction('⏩')

        def check(reaction, user):
            return True if user != self.client.user and str(reaction.emoji) in ['⏪', '⏩'] and reaction.message.id == msg.id else False

        try:
            reaction, user = await self.client.wait_for("reaction_add", timeout = 120, check = check)
        except asyncio.TimeoutError:
            pass

        else:
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.pages(ctx=ctx, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.pages(ctx=ctx, msg=msg, start=start+1, per_page=per_page, max=max)

    # TODO:
    @commands.command(brief = "**Cancela um jogo!**", description = "**Utilização:** `td!cancel [id jogo]`")
    @commands.check( is_admin )
    async def cancel(self, ctx, id_jogo):
        database = pymongo.MongoClient(port = 27017)

        jornada = database["totobola"]["jornadas"].find_one_and_update( {"jornada" : "ATIVA", "jogos.id_jogo" : id_jogo},
                                                                        {"jogos.$.estado" : "PROCESSED", "$unset" : {"jogos.$.h2hHome" : 1, "jogos.$.h2hAway" : 1}},
                                                                        projection = {"id_jornada" : 1})
        
        if jornada is not None:
            print(jornada["id_jornada"])

            if (database["totobola"]["jornadas"].count_documents({"id_jornada" : jornada["id_jornada"], "jogos" : {"$elemMatch" : {"estado" : {"$ne" : "PROCESSED"}}}}) == 0):
                database["totobola"]["jornadas"].update_one( { "id_jornada" : jornada["id_jornada"] },
                                                             {"$set" : {"estado" : "TERMINADA"}} )
                                                             #verificar se todos os jogos estão processed e, se sim, terminar jornada.

        else:
            await ctx.send(":x: **Jogo não encontrado!**")
    
    # TODO:
    @commands.command(brief = "**Atribui um resultado a um jogo!**", description = "**Utilização:** `td!resultado [id_jogo] [resultado]`")
    @commands.check( is_admin )
    async def resultado(self, ctx, id_jogo, resultado):
        database = pymongo.MongoClient(port = 27017)

        if database["totobola"]["jornadas"].count_documents({"estado" : "ATIVA", "jogos.id_jogo" : int(id_jogo)}) > 0: 
        
            if len(re.findall(r'\d+', resultado.lower())) == 2:
                print("Resultado!")
                res = re.findall(r'\d+', resultado.lower())

                game = {
                    "id" : int(id_jogo),
                    "score" : {
                        "winner" : None,
                        "fullTime" : {
                            "homeTeam" : res[0],
                            "awayTeam" : res[1]
                        }
                    }
                }

                if (res[0] > res[1]) : game["score"]["winner"] = "HOME_TEAM"
                elif (res[0] < res[1]) : game["score"]["winner"] = "AWAY_TEAM"
                else : game["score"]["winner"] = "DRAW"

                await calculate(game, self.client)
        else:
            await ctx.send(":x: **Jogo não encontrado!**")

def setup(client):
    client.add_cog(Totobola(client))