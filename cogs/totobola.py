import discord
from discord.ext import commands
import pymongo
import sys
import json

PATH = "/home/eduardo/HDD/Development/Totobola"

sys.path.append(f"{PATH}/utils")

from utils import is_admin, is_comp, is_comp_not

async def database_exists(ctx):
    database = pymongo.MongoClient(port = 27017)

    if "totobola" in database.list_database_names() : return False

    return True

class Totobola(commands.Cog):

    def __init__(self, client):
        self.client = client
    
    @commands.command()
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
        embed.set_thumbnail(url = "https://media.discordapp.net/attachments/786651440528883745/788119312489381928/totoo.png")
        embed.description = f"Para te registares na prova, basta clicares no :writing_hand:.\n\nCompetições adicionadas:\n"
        embed.set_footer(text = "Totobola Discordiano")

        message = await ctx.send(embed = embed)
        
        await message.add_reaction("✍")
        await message.pin()

        totobola["registo"].insert_one({
            "message_id" : message.id
        })

    @commands.command()
    @commands.check(is_admin)
    async def admin(self, ctx, mention):
        database = pymongo.MongoClient(port= 27017)
        properties = database["totobola"]["properties"]
        
        p = properties.find_one()
        properties.update_one({"_id" : p["_id"]}, {"$push" : {"admin" : ctx.message.mentions[0].id}})

        embed = discord.Embed(title="Administrador", colour = discord.Colour.magenta())
        embed.set_footer(text = "Totobola Discordiano", icon_url = "https://media.discordapp.net/attachments/786651440528883745/788119312489381928/totoo.png")
        embed.set_thumbnail(url = ctx.message.mentions[0].avatar_url)
        embed.add_field(name = "Admin", value = f"```{ctx.message.mentions[0].display_name}```")
        embed.add_field(name = "Estado", value = "```Ativo```")

        await ctx.send(embed = embed)

    @commands.command()
    @commands.check(is_admin)
    @commands.check(is_comp)
    async def add(self, ctx, comp):
        database = pymongo.MongoClient(port = 27017)
        database["totobola"]["properties"].update(database["totobola"]["properties"].find_one({}, {"_id": 1}), {"$push" : {"competicoes" : {"competicao" : comp, "link" : None, "name" : None}}})

        for player in database["totobola"]["jogadores"].find({} , {"player_id" : 1, "_id" : 0}):
            database["totobola"][comp].insert_one({"player_id" : player["player_id"], "pontuacao" : 0})
            database["totobola"]["total"].update_one({"player_id" : player["player_id"]}, {"$push" : {"p_competicoes" : {"competicao" : comp, "pontuacao" : 0 }}})

        await ctx.send(f"Competição {comp} adicionada com sucesso!")


    @commands.command()
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

    @commands.command()
    @commands.check(is_admin)
    async def ligas(self, ctx):
        with open(f"{PATH}/football/leagues.json", "r") as leagues:
            leagues = json.load(leagues)

        l = ""
        for code, league in leagues.items():
            l += f":soccer: **{code}** - {league['name']}\n"
        
        await ctx.send(l)

    @commands.command()
    @commands.check(is_admin)
    async def competicoes(self, ctx):
        database = pymongo.MongoClient(port = 27017)
        
        competicoes = database["totobola"]["properties"].find_one({}, {"_id" : 0, "competicoes" : 1})
        comps = ""

        for competicao in competicoes["competicoes"]:
            print(competicao)
            comps += f":soccer: **{competicao['competicao']}** - {competicao['name']}\n"

        await ctx.send(comps)

def setup(client):
    client.add_cog(Totobola(client))