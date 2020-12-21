import discord
from discord.ext import commands
import re
import pymongo
import sys

PATH = "/home/eduardo/HDD/Development/Totobola"
sys.path.append(f"{PATH}/utils/")

from utils import is_comp, is_comp_not

class Aposta(commands.Cog):
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

                    if "*" in message.content.lower() and joker["processed"] == 0: joker["id_jogo"] = jornada["jogos"][position["index"]]["id_jogo"]                                        # Joker

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

    @commands.command()
    @commands.check(is_comp_not)
    async def update(self, ctx, comp : str, id_jogo: str, *res):
        database = pymongo.MongoClient(port = 27017)

        id_jogo = int(re.findall(r"/d+", id_jogo)[0])
        # Verifica se existe uma jornada ativa na competição
        jornada = database["totobola"]["jornadas"].find_one( {"competicao" : comp, "estado" : "ATIVA", "jogos" : { "$elemMatch" : {"id_jogo" : id_jogo, "estado" : "SCHEDULED"}}},
                                                            {"_id" : 0, "id_jornada" : 1, "competicao" : 1, "jogos" : {"$elemMatch" : {"id_jogo" : id_jogo}}})
        
        print(jornada)

        if jornada is None:
            await ctx.send(":closed_lock_with_key: Impossível apostar nesse jogo!")
            return
        
        res = "".join(res)
        
        if len(re.findall(r'\d+', res.lower())) == 2:                     # 2-2 : Aposta válida
            bet = database["totobola"][jornada["id_jornada"]].find_one({"player_id" : ctx.author.id}, {"_id" : 0, "joker" : 1, "apostas" : {"$elemMatch" : {"id_jogo" : id_jogo}}})

            if "*" in res.lower() and bet["joker"]["processed"] == 0: bet["joker"]["id_jogo"] = jornada["jogos"][0]["id_jogo"]                                        # Joker

            res = re.findall(r'\d+', res.lower())
            
            tendencia = None

            if int(res[0]) > int(res[1]) : tendencia = "homeWin"
            elif int(res[0]) == int(res[1]) : tendencia = "draw"
            elif int(res[0]) < int(res[1]) : tendencia = "awayWin"
            
            res = f"{res[0]}-{res[1]}"
            
            database["totobola"][jornada["id_jornada"]].update({"player_id" : ctx.author.id, "apostas.id_jogo" : id_jogo}, {"$set" : {"joker" : bet["joker"], "apostas.$.tendencia" : tendencia, "apostas.$.resultado" : res}})
            
            embed = discord.Embed(title = "Atualização de Jogo", colour = discord.Colour.green())
            embed.set_thumbnail(url = ctx.author.avatar_url)
            embed.add_field(name = "Competição", value=comp)
            embed.add_field(name = "ID", value=jornada["id_jornada"])
            embed.add_field(name = "Jogo", value=f"{jornada['jogos'][0]['homeTeam']} - {jornada['jogos'][0]['awayTeam']}")
            embed.add_field(name = "Antigo", value=bet["apostas"][0]["resultado"])
            embed.add_field(name = "Novo", value=res)
            embed.add_field(name = "Joker", value=bet["joker"]["id_jogo"])

            await ctx.send(embed = embed)

        else:
            await ctx.send(":x: Aposta inválida!")
        
def setup(client):
    client.add_cog(Aposta(client))