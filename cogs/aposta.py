import discord
from discord.ext import commands
import re
import pymongo
import sys
import logging

PATH = "/home/eduardo/HDD/Development/Totobola"
sys.path.append(f"{PATH}/utils/")
logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

from utils import is_comp, is_comp_not

class Aposta(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)
        
        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
        
        file_handler = logging.FileHandler("logs/info.log")
        file_handler.setFormatter(formatter)
        self.logger.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)

    @commands.Cog.listener()
    async def on_reaction_add( self, reaction: discord.Reaction, user: discord.User ):
        database = pymongo.MongoClient(port = 27017)
        
        if user.bot:
            return
        
        if reaction.message.guild is not None:
            return

        if database["totobola"]["jornadas"].count_documents({"estado" : "ATIVA"}) == 0:
            await user.send(":pencil2: Não existem jornadas ativas!")
            self.logger.warning(f"\n[on_reaction_add] {user.display_name} -> Nenhuma jornada ativa!")
            return

        jornadas = database["totobola"]["jornadas"].find({"estado" : "ATIVA"}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1, "competicao" : 1})
        
        #if jornadas.count() == 0: return
        
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
            self.logger.warning(f"\n[on_reaction_add] {user.display_name} -> Tentou iniciar uma aposta com outra ativa!")
            return
        
        position = database["totobola"]["jornadas"].aggregate( [ { "$match" : {"id_jornada" : j["id_jornada"]}}, 
                                                                { "$project" : { "index" : { "$indexOfArray" : ["$jogos.id_jogo", a["current"]]} } }])
            
        try:
            position = position.next()
            
            while j["jogos"][position["index"]]["estado"] != "SCHEDULED" and position["index"] < len(j["jogos"]) - 1:
                position["index"] += 1
            
            embed = discord.Embed(title = "Aposta", colour = discord.Colour.green())
            embed.set_thumbnail(url = user.avatar_url)
            
            embed.add_field(name = "Jornada", value = f"`{j['id_jornada']}`")
            
            embed.add_field(name = f"{j['jogos'][position['index']]['homeTeam']} - {j['jogos'][position['index']]['awayTeam']}", value = f"`{j['jogos'][position['index']]['id_jogo']}`")

            h2hHome = "\n".join(j['jogos'][position['index']]["h2hHome"])
            h2hAway = "\n".join(j['jogos'][position['index']]["h2hAway"])
            
            embed.add_field(name = f"H2H {j['jogos'][position['index']]['homeTeam']}", value = f"{h2hHome}", inline = False)
            embed.add_field(name = f"H2H {j['jogos'][position['index']]['awayTeam']}", value = h2hAway)
            
            await user.send(embed = embed)
            await reaction.message.unpin()
            
            database["totobola"][j["id_jornada"]].update({"player_id" : user.id}, {"$set" : {"current" : j["jogos"][position["index"]]['id_jogo'], "status" : "ATIVA"}})
            database["totobola"][j["competicao"]].update_one({"player_id" : user.id}, {"$inc" : {"apostas" : 1}})

            self.logger.info(f"\n[on_reaction_add] {user.display_name} -> Iniciou jornada {j['id_jornada']}")
            
        except StopIteration:
            self.logger.error(f"\n[on_reaction_add] {user.display_name} -> Nenhum jogo ativo!")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        ''' Check if the user is the bot, and if it is, return '''
        if message.author == self.client.user: 
            return
        
        elif message.guild is None:
            ''' Check if it is a DM channel '''
            database = pymongo.MongoClient(port = 27017)

            ''' Check if there are active matchdays '''
            if database["totobola"]["jornadas"].count_documents({"estado" : "ATIVA"}) == 0:
                await message.author.send(":pencil2: Não existem jornadas ativas!")
                self.logger.warning(f"\n[on_message] {message.author.display_name} -> Não existe uma jornada ativa!")
                return

            jornadas = database["totobola"]["jornadas"].find({"estado" : "ATIVA"}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})
            
            bet = None

            ''' Iterate through active matchdays '''
            for jornada in jornadas:
                aposta = database["totobola"][jornada["id_jornada"]].find_one({"player_id" : message.author.id}, {"_id" : 0, "message_id" : 1, "status" : 1, "current" : 1, "joker" : 1})

                ''' Check for active bets '''
                if aposta["status"] == "ATIVA":
                    bet = aposta
                    break

            del aposta

            ''' If there isn't an active bet, just return '''
            if bet is None:
                await message.author.send(":pencil2: Tens que ativar a jornada antes de apostares!")
                self.logger.warning(f"\n[on_message] {message.author.display_name} -> Não tem nenhuma aposta ativa!")
                return

            ''' Each matchday has an array that describes each game from that matchday. In this query, we get the index in that array of the current game from the user's bet '''
            
            position = database["totobola"]["jornadas"].aggregate( [ { "$match" : {"id_jornada" : jornada["id_jornada"]}}, 
                                                            { "$project" : { "index" : { "$indexOfArray" : ["$jogos.id_jogo", bet["current"]]} } }])

            try:
                ''' The previous query returns a pymongo.cursor. The goal is to try to get the value retrieved, and if there isn't a match, then an exception is raised. '''
                position = position.next()
                
                blocked = False

                ''' Iterate through the matchday's games and check if the match is still SCHEDULED. If it '''
                while jornada["jogos"][position["index"]]["estado"] != "SCHEDULED" and position["index"] < len(jornada["jogos"]) - 1:
                    blocked = True              #If the current game of the user's bet is not SCHEDULED anymore, than blocked becomes True
                    position["index"] += 1
                
                ''' If the said flag is True, than the prognostic for that game is not valid. We then update the current game of the users's bet '''
                if blocked:
                    await message.author.send(":lock: O jogo em que tentaste apostar já não se encontra ativo!")
                    self.logger.info(f"\n[on_message] {message.author.display_name} -> Tentou apostar no jogo ({jornada['jogos'][position['index']]['id_jogo']}) mas este já não se encontra ativo!")
                    embed = discord.Embed(title = "Aposta", colour = discord.Colour.green())
                    embed.set_thumbnail(url = message.author.avatar_url)
                    
                    embed.description = f"**Próximo jogo:**\n:soccer:`{jornada['jogos'][position['index']]['id_jogo']}`: {jornada['jogos'][position['index']]['homeTeam']} - {jornada['jogos'][position['index']]['awayTeam']}\n\n"

                    embed = self.show_h2h(jornada, position, embed)
                    joker = bet["joker"]
                    embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`", inline = False)
                    embed.add_field(name = "Joker", value = f"`{joker['id_jogo']}`")

                    await message.author.send(embed = embed)
                    database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id} , { "$set" : {"current" : jornada["jogos"][position["index"]]["id_jogo"]}})
                    message = await message.author.send(f":soccer: {jornada['jogos'][position['index']]['id_jogo']}: {jornada['jogos'][position['index']]['homeTeam']} - {jornada['jogos'][position['index']]['awayTeam']}")
                    return

                ''' Otherwise, we check if the bet as a valid value
                    x-x -> Doesn't wanna bet
                    1-1 -> Valid
                    *   -> Joker
                    Everything else is not valid              
                '''
                if len(re.findall(r"\s*(x)\s*-\s*(x)\s*", message.content.lower())) > 0:        # x-x : Não quer apostar
                    position["index"] += 1
                
                    if position["index"] > len(jornada["jogos"]) - 1:
                        self.logger.info(f"\n[on_message] {message.author.display_name} apostou x-x no jogo ({jornada['jogos'][position['index'] - 1]['id_jogo']}) e a jornada terminou!") 
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id}, {"$set" : {"status" : "TERMINADA"}})

                    else: 
                        self.logger.info(f"\n[on_message] {message.author.display_name} apostou x-x no jogo ({jornada['jogos'][position['index'] - 1]['id_jogo']})!") 
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id}, {"$set" : {"current" : jornada["jogos"][position["index"]]["id_jogo"]}})
                
                elif len(re.findall(r'\d+', message.content.lower())) == 2:                     # 2-2 : Aposta válida
                    joker = bet["joker"]

                    if "*" in message.content.lower() and joker["processed"] == 0: joker["id_jogo"] = jornada["jogos"][position["index"]]["id_jogo"]                                        # Joker

                    res = re.findall(r'\d+', message.content.lower())
                    
                    tendencia = None

                    if int(res[0]) > int(res[1]) : tendencia = "homeWin"
                    elif int(res[0]) == int(res[1]) : tendencia = "draw"
                    elif int(res[0]) < int(res[1]) : tendencia = "awayWin"
                    
                    result = res
                    res = f"{res[0]}-{res[1]}"

                    self.logger.info(f"\n[on_message] {message.author.display_name} apostou {res} ({message.content}) no jogo ({jornada['jogos'][position['index'] - 1]['id_jogo']})!") 
                    
                    if position["index"] == len(jornada["jogos"]) - 1:
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id, "apostas.id_jogo" : jornada["jogos"][position["index"]]["id_jogo"]},
                                                                                {"$set" : {"status" : "TERMINADA", "apostas.$.tendencia" : tendencia, "joker" : joker, "apostas.$.resultado" : res}})
                    
                        #TODO: Melhorar mensagem #
                        
                        embed = discord.Embed(title = "Aposta", colour = discord.Colour.green())
                        embed.set_thumbnail(url = message.author.avatar_url)
                        
                        embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`")
                        embed.add_field(name = "Joker", value = f"`{joker['id_jogo']}`")
                        embed.description = f"**{jornada['jogos'][position['index']]['homeTeam']} `{result[0]}-{result[1]}` {jornada['jogos'][position['index']]['awayTeam']}**"
                        
                        await message.author.send(embed = embed)
                        
                        #TODO: enviar para canal#
                        await message.author.send(":fireworks: Aposta terminada!")

                        channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
                        channel = self.client.get_channel(channel["channel"])
                        
                        await self.show_bet(channel, message.author, jornada)

                    else:
                        database["totobola"][jornada["id_jornada"]].update({"player_id" : message.author.id, "apostas.id_jogo" : jornada["jogos"][position["index"]]["id_jogo"]},
                                                                                {"$set" : {"current" : jornada["jogos"][position["index"] + 1]["id_jogo"], "apostas.$.tendencia" : tendencia, "joker" : joker, "apostas.$.resultado" : res}})

                        #TODO: Melhorar message#
                        embed = discord.Embed(title = "Aposta", colour = discord.Colour.green())
                        embed.set_thumbnail(url = message.author.avatar_url)
                        
                        embed.description = f"**{jornada['jogos'][position['index']]['homeTeam']} `{result[0]}-{result[1]}` {jornada['jogos'][position['index']]['awayTeam']}**\n\n**Próximo jogo:**\n:soccer:`{jornada['jogos'][position['index'] + 1]['id_jogo']}`: {jornada['jogos'][position['index'] + 1]['homeTeam']} - {jornada['jogos'][position['index'] + 1]['awayTeam']}\n\n"

                        embed = self.show_h2h(jornada, position, embed)
                        
                        embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`", inline = False)
                        embed.add_field(name = "Joker", value = f"`{joker['id_jogo']}`")
 
                        await message.author.send(embed = embed)
                        
                else:
                    self.logger.warning(f"\n[on_message] {message.author.display_name} apostou ({message.content}) no jogo ({jornada['jogos'][position['index'] - 1]['id_jogo']}) e este não é válido!") 
                    await message.author.send(":x: Resultado inválido!")
                    return

            except StopIteration:
                self.logger.error(f"\n[on_message] {message.author.display_name} -> Não existe nenhum jogo para apostar!")
                pass
        
        else:
            return

    @commands.command(brief = "**Atualizar um determinado jogo!**", description = "**Utilização:** `td!update [id jogo] [resultado]`")
    @commands.check(is_comp_not)
    async def update(self, ctx, id_jogo: str, *res):
        database = pymongo.MongoClient(port = 27017)

        id_jogo = int(re.findall(r"\d+", id_jogo)[0])
        # Verifica se existe uma jornada ativa na competição
        jornada = database["totobola"]["jornadas"].find_one( {"estado" : "ATIVA", "jogos" : { "$elemMatch" : {"id_jogo" : id_jogo, "estado" : "SCHEDULED"}}},
                                                            {"_id" : 0, "id_jornada" : 1, "competicao" : 1, "jogos" : {"$elemMatch" : {"id_jogo" : id_jogo}}})

        self.logger.info(f"\n(1) [update] Jogador: {ctx.message.author.display_name} - ID Jogo: {id_jogo} - Resultado: {res}") 
        
        if jornada is None:
            self.logger.warning(f"\n(2) [update] Jogador: {ctx.message.author.display_name} - ID Jogo: {id_jogo} -> Impossível apostar no jogo!")
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
            embed.add_field(name = "ID", value=f"`{jornada['id_jornada']}`")
            embed.add_field(name = "Jogo", value=f"`{jornada['jogos'][0]['homeTeam']} - {jornada['jogos'][0]['awayTeam']}`")
            embed.add_field(name = "Antigo", value=f"`{bet['apostas'][0]['resultado']}`")
            embed.add_field(name = "Novo", value=f"`{res}`")
            embed.add_field(name = "Joker", value=f"`{bet['joker']['id_jogo']}`")

            await ctx.send(embed = embed)
            self.logger.info(f"\n(2) [update] Jogador: {ctx.message.author.display_name} - ID Jogo: {id_jogo} - Resultado: {res} -> Sucesso!")
        
        else:
            self.logger.warning(f"\n(2) [update] Jogador: {ctx.message.author.display_name} - ID Jogo: {id_jogo} -> Insucesso!")
            await ctx.send(":x: Aposta inválida!")

    def show_h2h(self, jornada, position, embed):
        h2hHome = "\n".join(jornada['jogos'][position['index']+1]["h2hHome"])
        h2hAway = "\n".join(jornada['jogos'][position['index']+1]["h2hAway"])
        
        embed.add_field(name = f"H2H {jornada['jogos'][position['index'] + 1]['homeTeam']}", value = h2hHome, inline = False)
        embed.add_field(name = f"H2H {jornada['jogos'][position['index'] + 1]['awayTeam']}", value = h2hAway, inline = False)
        
        return embed

    async def show_bet(self, channel, user, jornada):
        database = pymongo.MongoClient(port = 27017)
        bet = database["totobola"][jornada["id_jornada"]].find_one({"player_id" : user.id}, {"_id" : 0, "apostas" : 1, "joker" : 1, })

        str_jogos = "\n"
        for j, jogo in enumerate(jornada["jogos"]):
            if bet["apostas"][j]["resultado"] is not None:
                str_jogos += f":soccer: `{jogo['id_jogo']}`: **{jogo['homeTeam']}** `{bet['apostas'][j]['resultado'][: bet['apostas'][j]['resultado'].index('-')]}-{bet['apostas'][j]['resultado'][bet['apostas'][j]['resultado'].index('-')+1 :]}` **{jogo['awayTeam']}**\n"

        embed = discord.Embed(title = "Aposta", colour = discord.Colour.dark_theme())
        embed.add_field(name = "ID", value = f'`{jornada["id_jornada"]}`')
        embed.add_field(name = "Joker", value = f'`{bet["joker"]["id_jogo"]}`')
        embed.description = str_jogos
        embed.set_thumbnail(url = user.avatar_url)
        embed.add_field(name = "Jogador", value = f"`{user.display_name}`")
        embed.set_footer(text = "Totobola Discordiano", icon_url = logo)

        await channel.send(embed = embed)
    
    def send_bet(self, user, jornada):
            database = pymongo.MongoClient(port = 27017)
                    
            if jornada is not None:
                bet = database["totobola"][jornada["id_jornada"]].find_one({"player_id" : user.id, "status" : {"$ne" : "INATIVA"}}, {"_id" : 0, "apostas" : 1, "joker" : 1, "pontuacao" : 1})
                
                if bet is not None:
                    embed = discord.Embed(title = "Aposta", colour = discord.Colour.dark_blue())
                    embed.set_thumbnail(url = user.avatar_url)
                    embed.add_field(name = "Jogador", value = user.display_name)
                    embed.add_field(name = "Pontuação", value = bet["pontuacao"])
                    embed.set_footer(text = "Totobola Discordiano", icon_url = logo)
                    games = ""

                    for j, jogo in enumerate(bet["apostas"]):
                        if jogo["resultado"] is None:
                            pass
                        else:
                            games += f":soccer: `{jogo['id_jogo']}` **{jornada['jogos'][j]['homeTeam']} {jogo['resultado']} {jornada['jogos'][j]['awayTeam']}**"
                            
                            if bet["joker"]["id_jogo"] == jogo["id_jogo"]:
                                games += " :black_joker:\n"
                            else:
                                games += "\n"
                    
                    embed.description = games
                
                    return embed
                else:
                    return -2
            else:
                return -1
    
    @commands.command(brief = "**Verificar aposta numa jornada ativa de uma competição!**", description ="**Utilização:** `td!aposta [competicao] (jogador)`")
    async def aposta(self, ctx, competicao, *args):
        database = pymongo.MongoClient(port = 27017)
        jornada = database["totobola"]["jornadas"].find_one({"competicao" : competicao, "estado" : "ATIVA"}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})
        
        if len(args) == 0:
            embed = self.send_bet(ctx.author, jornada)
            if embed not in [-1, -2]:
                await ctx.send(embed = embed)
            elif embed == -1:
                await ctx.send("Não existe uma jornada ativa!")
            elif embed == -2:
                await ctx.send("Jogador ainda não apostou!")

        elif len(args) == 1:
            if ctx.message.mentions is not None:
                embed = self.send_bet(ctx.message.mentions[0], jornada)
                if embed not in [-1, -2]:
                    await ctx.send(embed = embed)
                elif embed == -1:
                    await ctx.send("Não existe uma jornada ativa!")
                elif embed == -2:
                    await ctx.send("Jogador ainda não apostou!")

            else:
                await ctx.send("Precisas de mencionar alguém!")
        else:
            await ctx.send("Demasiados argumentos. O comando deve ser utilizado da seguinte forma: **td!aposta [competição] @(opcional)**")

    @commands.command(brief = "**Verificar aposta em jornadas terminadas!**", description = "**Utilização:** `td!apostada [id jornada] (jogador)`")
    async def apostada(self, ctx, id_jornada, *args):
        database = pymongo.MongoClient(port = 27017)
        jornada = database["totobola"]["jornadas"].find_one({"id_jornada" : id_jornada, "estado" : "TERMINADA"}, {"_id" : 0, "id_jornada" : 1, "jogos" : 1})
        
        if len(args) == 0:
            embed = self.send_bet(ctx.author, jornada)
            if embed not in [-1, -2]:
                await ctx.send(embed = embed)
            elif embed == -1:
                await ctx.send("**Jornada não encontrada!**")
            elif embed == -2:
                await ctx.send("**Jogador não apostou na jornada!**")

        elif len(args) == 1:
            if ctx.message.mentions is not None:
                embed = self.send_bet(ctx.message.mentions[0], jornada)
                if embed not in [-1, -2]:
                    await ctx.send(embed = embed)
                elif embed == -1:
                    await ctx.send("**Jornada não encontrada!**")
                elif embed == -2:
                    await ctx.send("**Jogador não apostou na jornada!**")

            else:
                await ctx.send("**Precisas de mencionar alguém!**")
        else:
            await ctx.send("Demasiados argumentos. O comando deve ser utilizado da seguinte forma: **td!aposta [competição] @(opcional)**")
        
def setup(client):
    client.add_cog(Aposta(client))