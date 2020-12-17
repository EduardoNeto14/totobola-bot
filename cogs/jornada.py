import discord
from discord.ext import commands
import uuid
import os
import pymongo
import json
import sys
import requests
import re

PATH = "/home/eduardo/HDD/Development/Totobola"
sys.path.append(f"{PATH}/utils/")

from utils import is_admin

class Jornada(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_reaction_add( self, reaction: discord.Reaction, user: discord.User ):
        database = pymongo.MongoClient(port = 27017)
        
        if user.bot:
            return
        
        if reaction.message.guild is not None:
            return

        if database["totobola"]["jornadas"].count_documents({"estado" : "ATIVA"}) == 0:
            await user.send(":pencil2: Não existem jornadas ativas!")
            return

        jornadas = database["totobola"]["jornadas"].find({"estado" : "ATIVA"}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})
        
        if jornadas.count() == 0: return
        
        jornada_ativa = False
        j = None
        a = None

        for jornada in jornadas:
            aposta = database["totobola"][jornada["id_jornada"]].find_one({"player_id" : user.id}, {"_id" : 0, "message_id" : 1, "status" : 1, "current" : 1})
            
            if aposta["message_id"] == reaction.message.id:
                j = jornada
                a = aposta
            
            if aposta["status"] == "ATIVA":
                jornada_ativa = True
        
        del jornada
        del aposta
        
        if jornada_ativa:
            await user.send(":lock: Já tens uma jornada ativa! Termina a tua aposta...")
            return
        
        position = database["totobola"]["jornadas"].aggregate( [ { "$match" : {"id_jornada" : j["id_jornada"]}}, 
                                                                { "$project" : { "index" : { "$indexOfArray" : ["$jogos.id_jogo", a["current"]]} } }])
            
        try:
            position = position.next()
            
            while j["jogos"][position["index"]]["estado"] != "SCHEDULED" and position["index"] < len(j["jogos"]) - 1:
                position["index"] += 1

            await user.send(f":soccer: {j['jogos'][position['index']]['id_jogo']}: {j['jogos'][position['index']]['homeTeam']} - {j['jogos'][position['index']]['awayTeam']}")
            
            database["totobola"][j["id_jornada"]].update({"player_id" : user.id}, {"$set" : {"current" : j["jogos"][position["index"]]['id_jogo'], "status" : "ATIVA"}})
    
        except StopIteration:
            print("[Jornada - Erro] Posição não encontrada!")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # TODO: Verificar se message.author.id tem uma aposta ativa -> DONE
        #print(message.guild is None and not message.author.bot)
        if message.author == self.client.user: 
            return
        
        elif message.guild is None:
            database = pymongo.MongoClient(port = 27017)

            if database["totobola"]["jornadas"].count_documents({"estado" : "ATIVA"}) == 0:
                await message.author.send(":pencil2: Não existem jornadas ativas!")
                return

            jornadas = database["totobola"]["jornadas"].find({"estado" : "ATIVA"}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})
            
            bet = None

            for jornada in jornadas:
                aposta = database["totobola"][jornada["id_jornada"]].find_one({"player_id" : message.author.id}, {"_id" : 0, "message_id" : 1, "status" : 1, "current" : 1, "joker" : 1})

                if aposta["status"] == "ATIVA":
                    bet = aposta
                    break

            del aposta

            if bet is None:
                await message.author.send(":pencil2: Tens que ativar a jornada antes de apostares!")
                return

            position = database["totobola"]["jornadas"].aggregate( [ { "$match" : {"id_jornada" : jornada["id_jornada"]}}, 
                                                            { "$project" : { "index" : { "$indexOfArray" : ["$jogos.id_jogo", bet["current"]]} } }])

            try:
                position = position.next()
                
                blocked = False

                while jornada["jogos"][position["index"]]["estado"] != "SCHEDULED" and position["index"] < len(jornada["jogos"]) - 1:
                    blocked = True
                    position["index"] += 1

                if blocked:
                    await message.author.send(":lock: O jogo em que tentaste apostar já não se encontra ativo!")
                    database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id} , { "$set" : {"current" : jornada["jogos"][position["index"]]["id_jogo"]}})
                    message = await message.author.send(f":soccer: {jornada['jogos'][position['index']]['id_jogo']}: {jornada['jogos'][position['index']]['homeTeam']} - {jornada['jogos'][position['index']]['awayTeam']}")
                    return

                if len(re.findall(r"\s*(x)\s*-\s*(x)\s*", message.content.lower())) > 0:        # x-x : Não quer apostar
                    position["index"] += 1
                
                    if position["index"] > len(jornada["jogos"]) - 1: 
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id}, {"$set" : {"status" : "TERMINADA"}})

                    else: 
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id}, {"$set" : {"current" : jornada["jogos"][position["index"]]["id_jogo"]}})
                
                elif len(re.findall(r'\d+', message.content.lower())) == 2:                     # 2-2 : Aposta válida
                    #position["index"] += 1
                    joker = bet["joker"]

                    if "*" in message.content.lower(): joker = jornada["jogos"][position["index"]]["id_jogo"]                                        # Joker

                    res = re.findall(r'\d+', message.content.lower())
                    
                    tendencia = None

                    if int(res[0]) > int(res[1]) : tendencia = "homeWin"
                    elif int(res[0]) == int(res[1]) : tendencia = "draw"
                    elif int(res[0]) < int(res[1]) : tendencia = "awayWin"
                    
                    result = res
                    res = f"{res[0]}-{res[1]}"

                    if position["index"] == len(jornada["jogos"]) - 1:
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id, "apostas.id_jogo" : jornada["jogos"][position["index"]]["id_jogo"]},
                                                                                {"$set" : {"status" : "TERMINADA", "apostas.$.tendencia" : tendencia, "joker" : joker, "apostas.$.resultado" : res}})
                    
                        await message.author.send(f":soccer: {jornada['jogos'][position['index']]['id_jogo']}: {jornada['jogos'][position['index']]['homeTeam']} {result[0]}-{result[1]} {jornada['jogos'][position['index']]['awayTeam']}")
                        await message.author.send(":fireworks: Aposta terminada!")

                    else:
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id, "apostas.id_jogo" : jornada["jogos"][position["index"]]["id_jogo"]},
                                                                                {"$set" : {"current" : jornada["jogos"][position["index"] + 1]["id_jogo"], "apostas.$.tendencia" : tendencia, "joker" : joker, "apostas.$.resultado" : res}})

                        await message.author.send(f":soccer: {jornada['jogos'][position['index']]['id_jogo']}: {jornada['jogos'][position['index']]['homeTeam']} {result[0]}-{result[1]} {jornada['jogos'][position['index']]['awayTeam']}")
                        await message.author.send(f":soccer: {jornada['jogos'][position['index'] + 1]['id_jogo']}: {jornada['jogos'][position['index'] + 1]['homeTeam']} - {jornada['jogos'][position['index'] + 1]['awayTeam']}")                        
                else:
                    await message.author.send(":x: Resultado inválido!")
                    return

            except StopIteration:
                pass
        
        else:
            return

        
        # TODO: Verificar se o jogo atual ainda permanece "SCHEDULED" -> DONE
        
        # TODO: Verificar se a aposta está correta -> DONE
        
        # TODO: Verificar se utilizou JOKER -> DONE

        # TODO: Calcular tendência do resultado (winHome - draw - winAway) -> DONE
        
        # TODO: Guardar a aposta -> DONE

        # TODO: Atualizar o jogo atual -> DONE

        # TODO: Se for o último jogo, terminar aposta -> DONE

        # TODO: Melhorar mensagem 
        
        # TODO: Add cos

    @commands.command()
    @commands.check( is_admin )
    async def jornada( self, ctx, comp: str, num: int, *jogos: str):
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
                    
                    jornada = {
                        "id_jornada"    : jornada_id,
                        "num_jornada"   : int(num),
                        "competicao"    : comp,
                        "estado"        : "ATIVA",
                        "jogos"         : []
                    }

                    with open(f"{PATH}/api-token.txt", "rb") as token:
                        token = token.readline()
                    
                    print(competicao)

                    request = requests.get(f"http://api.football-data.org/v2/competitions/{competicao['link']}/matches",
                                            params = {"matchday" : num, "status" : "SCHEDULED"},
                                            headers = {"X-Auth-Token" : token})
                    
                    request = request.json()

                    if len(request["matches"]) == 0:
                        await ctx.send("Não encontrei jogos!")
                        return

                    for match in request["matches"]:
                        jornada["jogos"].append({
                            "id_jogo" : match["id"],
                            "estado"  : "SCHEDULED",
                            "resultado" : None,
                            "tendencia" : None,
                            "homeTeam"  : match["homeTeam"]["name"],
                            "awayTeam"  : match["awayTeam"]["name"]
                        })
                    
                    database["totobola"]["jornadas"].insert_one(jornada)
                    
                    jogador = {
                        "player_id"  : None,
                        "message_id" : None,   
                        "status" : "INATIVA",
                        "current" : jornada["jogos"][0]["id_jogo"],
                        "pontuacao" : 0,
                        "joker" : None,
                        "apostas" : [{"id_jogo" : jogo["id_jogo"], "resultado" : None, "tendencia" : None} for jogo in jornada["jogos"]]
                    }
                    
                    for _user in database["totobola"]["jogadores"].find({}, {"_id" : 0}):
                        user = await self.client.fetch_user(_user["player_id"])
                        jogador["player_id"] = _user["player_id"] 
                        
                        message = await user.send(f":on: Jornada {jornada['num_jornada']} : {jornada['competicao']} ativa")
                        await message.add_reaction("📄")
                        await message.pin()

                        jogador["message_id"] = message.id 
                        database["totobola"][jornada["id_jornada"]].insert_one(jogador)
                
                else:
                    print("Verificar os jogos!")
        
        else:
            await ctx.send(":octagonal_sign: A competição indicada não existe!")

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

def setup(client):
    client.add_cog(Jornada(client))