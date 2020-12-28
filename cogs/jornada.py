import discord
from discord.ext import commands
import uuid
import os
import pymongo
import json
import sys
import re
import asyncio

PATH = "/home/eduardo/HDD/Development/Totobola"
sys.path.append(f"{PATH}/utils/")

from utils import is_admin
from api import check_games, get_h2h, get_jornada, get_num_jornada

class Jornada(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.task = None
    
    @commands.command()
    @commands.check( is_admin )
    async def jornada( self, ctx, comp: str, *jogos: str):
        database = pymongo.MongoClient(port = 27017)
        competicoes = None
        competicoes = database["totobola"]["properties"].find_one({"competicoes.competicao" : comp})

        if competicoes is not None:
            
            if database["totobola"]["jornadas"].count_documents({"competicao" : comp, "estado" : "ATIVA"}) > 0:
                await ctx.send(":x: Já existe uma jornada ativa nessa competição!")
                return
            
            jornada_id = comp + ":" + str(uuid.uuid4())[:6]
            
            while jornada_id in database["totobola"].list_collection_names():
                jornada_id = comp + ":" + str(uuid.uuid4())[:6]
            
            for competicao in competicoes["competicoes"]:
                if competicao["competicao"] == comp and competicao["link"] is not None:
                    
                    num = get_num_jornada(competicao["link"])

                    jornada = {
                        "id_jornada"    : jornada_id,
                        "num_jornada"   : int(num),
                        "competicao"    : comp,
                        "link"          : competicao["link"],
                        "estado"        : "ATIVA",
                        "jogos"         : []
                    }

                    request = get_jornada(competicao["link"], num)
                    
                    if len(request["matches"]) == 0:
                        await ctx.send("Não encontrei jogos! Tenta outra jornada...")
                        return

                    await ctx.send(":clock1: A recolha dos jogos vai demorar um bocado... Obrigado!")
                    for match in request["matches"]:
                        
                        h2h_home, h2h_away = await get_h2h(match)

                        jornada["jogos"].append({
                            "id_jogo" : match["id"],
                            "estado"  : "SCHEDULED",                # SCHEDULED - LIVE - STATIC - PROCESSED
                            "resultado" : None,
                            "tendencia" : None,
                            "homeTeam"  : match["homeTeam"]["name"],
                            "awayTeam"  : match["awayTeam"]["name"],
                            "h2hHome" : h2h_home,
                            "h2hAway" : h2h_away
                        })
                    
                    database["totobola"]["jornadas"].insert_one(jornada)
                    await self.send_to_players(database, jornada)
                    
                elif (competicao["competicao"] == comp and competicao["link"] is None) and len(jogos) == 0:
                    await ctx.send(":link: Esta competição não está conectada a nenhuma liga. Utiliza **td!get [ligas]** para ver os jogos disponíveis das ligas indicadas!\n\n*Nota: Se já o fizeste, podes ver os jogos disponíveis através de td!games [liga]*")

                elif (competicao["competicao"] == comp and competicao["link"] is None) and len(jogos) != 0:
                    if not os.path.isfile(f"{PATH}/temp/jornada.json"):
                        await ctx.send(":goggles: Não tenho informação de nenhum jogo. Executa o comando **td!get [ligas]** para obter essa informação!")
                        return
                    
                    jogos = list(jogos)
                    await ctx.send(":clock1: A recolha dos jogos vai demorar um bocado... Obrigado!")

                    with open(f"{PATH}/temp/jornada.json", "r") as leagues_info:
                        leagues_info = json.load(leagues_info)

                    jornada = {
                            "id_jornada" : jornada_id,
                            "num_jornada" : None,
                            "competicao" : comp,
                            "link" : [],
                            "estado" : "ATIVA",
                            "jogos" : []
                    }

                    link = set()
                    
                    for league, info in leagues_info.items():
                        for jogo in info["jogos"]:
                            if str(jogo["id_jogo"]) in jogos: 
                                
                                h2h_home, h2h_away = await get_h2h(jogo)

                                jornada["jogos"].append({
                                    "id_jogo" : jogo["id_jogo"],
                                    "estado"  : "SCHEDULED",                # SCHEDULED - LIVE - STATIC - PROCESSED
                                    "resultado" : None,
                                    "tendencia" : None,
                                    "homeTeam"  : jogo["homeTeam"]["name"],
                                    "awayTeam"  : jogo["awayTeam"]["name"],
                                    "h2hHome" : h2h_home,
                                    "h2hAway" : h2h_away
                                })

                                jogos.remove(str(jogo["id_jogo"]))
                                link.add(league)

                    if len(jogos) > 0:
                        await ctx.send(f":x: Jogos *{' '.join(jogos)}* incorretos!")

                    else:
                        jornada["link"] = list(link)

                        database["totobola"]["jornadas"].insert_one(jornada)
                        await self.send_to_players(database, jornada)

        else:
            await ctx.send(":octagonal_sign: A competição indicada não existe!")

    @commands.command()
    @commands.check( is_admin )
    async def load(self, ctx):
        print("load")
        self.task = self.client.loop.create_task(check_games())
    
    @commands.command()
    @commands.check( is_admin )
    async def unload(self, ctx):
        print("unload")
        self.task.cancel()
        self.task = None

    @commands.command()
    @commands.check( is_admin )
    async def get(self, ctx, *ligas):
        with open(f"{PATH}/football/leagues.json", "r") as leagues:
            leagues = json.load(leagues)
        
        ids = []
        names = []
        msg = ""

        for liga in ligas:
            if liga.upper() not in leagues:
                await ctx.send(f":x: O código {liga} está incorreto! Verifica o comando **td!ligas** para saber mais...")
                return
            
            ids.append(leagues[liga.upper()]["id"])
            names.append(leagues[liga.upper()]["name"])
            msg += f":soccer: `{leagues[liga.upper()]['id']}` - **{leagues[liga.upper()]['name']}**\n"

        await ctx.send(f"Ligas encontradas:\n{msg}\n\n:timer: A procurar informação dessas ligas...")
    
        n_jornadas = []
        info_ligas = {}

        for n, _id in enumerate(ids):
            jogos = []
            
            n_jornadas.append(get_num_jornada(_id))
            await asyncio.sleep(10)
            jornada = get_jornada(_id, n_jornadas[n])

            for j,jogo in enumerate(jornada["matches"]):
                jogos.append({
                    "id_jogo" : jogo["id"],
                    "homeTeam" : {
                        "id" : jogo["homeTeam"]["id"],
                        "name" : jogo["homeTeam"]["name"]},
                    "awayTeam" : {
                        "id" : jogo["awayTeam"]["id"],
                        "name" : jogo["awayTeam"]["name"]}
                })
            
            info_ligas[ligas[n].upper()] = {
                    "name" : names[n],
                    "id" : _id,
                    "num" : n_jornadas[n],
                    "jogos" : jogos
            }

        with open(f"{PATH}/temp/jornada.json", "w") as info:
            json.dump(info_ligas, info)

        await ctx.send(":point_right: Informação recolhida. Podes aceder aos jogos através de **td!games [liga]**!")

    @commands.command()
    @commands.check(is_admin)
    async def games(self, ctx, liga: str):
        if not os.path.isfile(f"{PATH}/temp/jornada.json"):
            await ctx.send(":x: Não foram recolhidos nenhuns jogos!")
            return
        
        with open(f"{PATH}/temp/jornada.json", "r") as info_ligas:
            info_ligas = json.load(info_ligas)

        if liga.upper() not in info_ligas:
            await ctx.send(":x: Não foram recolhidos nenhuns jogos dessa competição!")
            return
        
        jogos = '\n'.join([f':soccer: `{jogo["id_jogo"]}`: {jogo["homeTeam"]["name"]} - {jogo["awayTeam"]["name"]}' for jogo in info_ligas[liga.upper()]["jogos"]])
        await ctx.send(f"**{info_ligas[liga.upper()]['name']}**\n\n{jogos}")
        
    @commands.command()
    async def clean(self, ctx, id_jornada: str):
        database = pymongo.MongoClient(port = 27017)
        database["totobola"][id_jornada].drop()
        database["totobola"]["jornadas"].delete_one({"id_jornada" : id_jornada})

    @staticmethod
    async def embed(ctx, competicao = "__Por definir__", jornada = "__Por definir__", jogos = []):

        embedMessage = discord.Embed()
        embedMessage.title = "Criação de Jornada"
        embedMessage.add_field(name = "Competição", value = competicao)
        embedMessage.add_field(name = "Jornada", value = jornada)
        embedMessage.description = "```n - Cancelar\ns - Sucesso```"
        
        for j, jogo in enumerate(jogos):
            embedMessage.add_field(name = f"Jogo {j+1}", value = jogo, inline = False)

        await ctx.author.send(embed = embedMessage)

    async def send_to_players(self, database, jornada):
        jogador = {
            "player_id"  : None,
            "message_id" : None,   
            "status" : "INATIVA",
            "current" : jornada["jogos"][0]["id_jogo"],
            "pontuacao" : 0,
            "joker" : {"id_jogo": None, "processed" : 0},
            "apostas" : [{"id_jogo" : jogo["id_jogo"], "resultado" : None, "tendencia" : None} for jogo in jornada["jogos"]]
        }
        
        jogos = "\n".join([f":soccer: `{jogo['id_jogo']}` **{jogo['homeTeam']}** - **{jogo['awayTeam']}**" for jogo in jornada["jogos"]])

        embed = discord.Embed(title = "Jornada", colour = discord.Colour.green())
        embed.add_field(name = "Competição", value=jornada["competicao"])
        embed.add_field(name = "ID", value = jornada["id_jornada"])
        embed.description = jogos + "\n\n" + "Para postar basta clicar em :page_facing_up:"
        embed.set_footer(text = "Totobola Discordiano", icon_url = "https://media.discordapp.net/attachments/786651440528883745/788119312489381928/totoo.png")
        
        for _user in database["totobola"]["jogadores"].find({}, {"_id" : 0}):
            user = await self.client.fetch_user(_user["player_id"])
            
            jogador["player_id"] = _user["player_id"] 
            
            embed.set_thumbnail(url = user.avatar_url)
            
            message = await user.send(embed = embed)
            
            await message.add_reaction("📄")
            await message.pin()

            jogador["message_id"] = message.id 
            database["totobola"][jornada["id_jornada"]].insert_one(jogador)

def setup(client):
    client.add_cog(Jornada(client))