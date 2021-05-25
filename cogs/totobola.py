import discord
from discord.ext import commands
import pymongo
import sys
import json
import asyncio
import re
import logging

PATH = "/home/eduardo/HDD/Development/Totobola"
logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

sys.path.append(f"{PATH}/utils")

from utils import is_admin, is_comp, is_comp_not
from results import calculate, finish_matchday

async def database_exists(ctx):
    database = pymongo.MongoClient(port = 27017)

    if "totobola" in database.list_database_names() : return False

    return True

class Totobola(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
        
        file_handler = logging.FileHandler("logs/totobola.log")
        file_handler.setFormatter(formatter)
        self.logger.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)

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
            await msg.clear_reactions()

        else:
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.pages(ctx=ctx, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.pages(ctx=ctx, msg=msg, start=start+1, per_page=per_page, max=max)

    @commands.command(brief = "**Cancela um jogo!**", description = "**Utilização:** `td!cancel [id jogo]`")
    @commands.check( is_admin )
    async def cancel(self, ctx, id_jogo):
        database = pymongo.MongoClient(port = 27017)

        jornada = database["totobola"]["jornadas"].find_one_and_update( {"estado" : "ATIVA", "jogos.id_jogo" : int(id_jogo)},
                                                                        {"$set" : {"jogos.$.estado" : "PROCESSED"}, "$unset" : {"jogos.$.h2hHome" : 1, "jogos.$.h2hAway" : 1}},
                                                                        projection = {"id_jornada" : 1})

        if jornada is not None:
            print(jornada["id_jornada"])
            
            database["totobola"][jornada["id_jornada"]].update_many({"joker.id_jogo" : int(id_jogo)}, {"$set" : {"joker.processed" : 0}})

            if (database["totobola"]["jornadas"].count_documents({"id_jornada" : jornada["id_jornada"], "jogos" : {"$elemMatch" : {"estado" : {"$ne" : "PROCESSED"}}}}) == 0):
                await finish_matchday(self.client, jornada)
            else:
                await ctx.send(":x: **Jogo cancelado com sucesso!**")
        else:
            await ctx.send(":x: **Jogo não encontrado!**")
    
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

    @commands.command(brief = "**Atribui prognóstico de um jogo!**", description = "**Utilização:** `td!prog [jogador] [id_jogo] [resultado]`")
    @commands.check(is_admin)
    async def prog(self, ctx, player : discord.User, id_jogo, *resultado):
        # Verificar se player é uma menção
        
        if ctx.message.mentions is not None:
            database = pymongo.MongoClient(port = 27017)

            jornada = database["totobola"]["jornadas"].find_one( {"estado" : "ATIVA", "jogos.id_jogo" : int(id_jogo)}, {"_id" : 0, "id_jornada" : 1, "jogos.$" : 1})

            new_result = "".join(resultado)
            tendency = None

            if len(re.findall(r'\d+', new_result.lower())) == 2:
                goals = re.findall(r'\d+', new_result.lower())

                if goals[0] > goals[1] : tendency = "homeWin"
                elif goals[1] > goals[0] : tendency = "awayWin"
                else : tendency = "draw"                

                difference = int(goals[0]) - int(goals[1])

                res = f"{goals[0]}-{goals[1]}"
            else:
                await ctx.send(":x: Resultado inválido!")
                return
            
            if jornada is not None:
                curr_bet = database["totobola"][jornada["id_jornada"]].find_one( {"player_id" : ctx.message.mentions[0].id}, {"_id" : 0})
                
                embed = discord.Embed(title = "Alteração de Resultado", colour = discord.Colour.dark_red())
                embed.set_footer(text = "Totobola Discordiano", icon_url = logo)
                embed.set_author(name = ctx.message.author.display_name, icon_url = ctx.message.author.avatar_url)
                embed.set_thumbnail(url = ctx.message.mentions[0].avatar_url)
                embed.add_field(name = "Jogador", value = ctx.message.mentions[0].display_name)

                if "*" in new_result and curr_bet["joker"]["processed"] != 1:
                    database["totobola"][jornada["id_jornada"]].update_one({"player_id" : ctx.message.mentions[0].id, "apostas.id_jogo" : int(id_jogo)}, {"$set" : {"joker.id_jogo" : int(id_jogo), "apostas.$.resultado" : res, "apostas.$.tendencia" : tendency, "apostas.$.difference" : difference}})
                    embed.description = f":soccer: **{jornada['jogos'][0]['id_jogo']}: {jornada['jogos'][0]['homeTeam']}** `{res}` **{jornada['jogos'][0]['homeTeam']}** :black_joker:"
                    await ctx.send(embed = embed)
                    self.logger.info(f"\n[prog] Admin {ctx.message.author.display_name} -- ({ctx.message.mentions[0].display_name}) Jogo {id_jogo} alterado para {res} com joker!")
                else:
                    database["totobola"][jornada["id_jornada"]].update_one({"player_id" : ctx.message.mentions[0].id, "apostas.id_jogo" : int(id_jogo)}, {"$set" : {"apostas.$.resultado" : res, "apostas.$.tendencia" : tendency, "apostas.$.difference" : difference}})
                    embed.description = f":soccer: **{jornada['jogos'][0]['id_jogo']}: {jornada['jogos'][0]['homeTeam']}** `{res}` **{jornada['jogos'][0]['homeTeam']}**"
                    await ctx.send(embed = embed)
                    self.logger.info(f"\n[prog] Admin {ctx.message.author.display_name} -- ({ctx.message.mentions[0].display_name}) Jogo {id_jogo} alterado para {res}!")

                if curr_bet["status"] == "INATIVA":
                    database["totobola"][jornada["id_jornada"]].update_one({"player_id" : ctx.message.mentions[0].id}, {"$set" : {"status" : "ATIVA"}})
            
            else:
                await ctx.send(":x: Não existe nenhuma jornada ativa com esse jogo!")
        
        else:
            await ctx.send(":x: Precisas de mencionar um jogador!")

def setup(client):
    client.add_cog(Totobola(client))