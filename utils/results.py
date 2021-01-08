import pymongo
import asyncio
import discord

api_to_db = {
    "AWAY_TEAM" : "awayWin",
    "HOME_TEAM" : "homeWin",
    "DRAW" : "draw"
}

logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

async def calculate(game, client):
    print("Calculating!")
    database = pymongo.MongoClient(port = 27017)

    jornada = database["totobola"]["jornadas"].find_one({"estado" : "ATIVA", "jogos.id_jogo" : game["id"], "jogos.$.estado" : {"$ne" : "PROCESSED"}},
                                                        {"_id" : 0, "id_jornada": 1, "competicao" : 1})

    if jornada is None: return

    apostas = database["totobola"][jornada["id_jornada"]].find({"apostas.id_jogo" : game["id"], "apostas.resultado" : {"$ne" : None}},
                                                                {"_id" : 0, "player_id" :1, "joker" : 1, "pontuacao" : 1, "apostas" : {"$elemMatch" : {"id_jogo" : game["id"]}}})

    #print(apostas)
    result = f"{game['score']['fullTime']['homeTeam']}-{game['score']['fullTime']['awayTeam']}"

    for aposta in apostas:
        print(aposta)
        pontuacao = 0
        
        if aposta["apostas"][0]["resultado"] == result:
            pontuacao = 3
        elif aposta["apostas"][0]["tendencia"] == api_to_db[game["score"]["winner"]]:
            pontuacao = 1

        # Talvez meter isto qunado o jogo começar
        if aposta["joker"]["id_jogo"] == game["id"]:
            aposta["joker"]["processed"] = 1
            pontuacao *= 2

        if pontuacao != 0:
            database["totobola"][jornada["id_jornada"]].update_one(
                                                                {"player_id" : aposta["player_id"]},
                                                                { "$set" : {"joker" : aposta["joker"], "pontuacao" : aposta["pontuacao"] + pontuacao}} )
            
            database["totobola"][jornada["id_jornada"].split(":")[0]].update_one({"player_id" : aposta["player_id"]},
                                                                                 {"$inc" : {"pontuacao" : pontuacao}})
            database["totobola"]["total"].update_one({"player_id": aposta["player_id"], "p_competicoes.competicao" : jornada["competicao"]},
                                                     { "$inc" : {"pontuacao" : pontuacao, "p_competicoes.$.pontuacao" : pontuacao}})

    database["totobola"]["jornadas"].update_one({"id_jornada" : jornada["id_jornada"], "jogos.id_jogo" : game["id"]},
                                            { "$set" : { "jogos.$.estado" : "PROCESSED", "jogos.$.resultado": result, "jogos.$.tendencia" : api_to_db[game["score"]["winner"]]},
                                            "$unset" : {"jogos.$.h2hHome" : 1, "jogos.$.h2hAway" : 1}})

    if (database["totobola"]["jornadas"].count_documents({"id_jornada" : jornada["id_jornada"], "jogos" : {"$elemMatch" : {"estado" : {"$ne" : "PROCESSED"}}}}) == 0):
        database["totobola"]["jornadas"].update_one( { "id_jornada" : jornada["id_jornada"] },
                                                     {"$set" : {"estado" : "TERMINADA"}} )
        
        # Calcular cena de equipa
        # Calcular vencedores

        channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
        channel = client.get_channel(channel["channel"])

        embed = discord.Embed(title = "Jornada", colour = discord.Colour.blurple())
        embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`")
        
        jogos = database["totobola"]["jornadas"].find_one({"id_jornada" : jornada["id_jornada"]}, {"_id" : 0 , "jogos" : 1})

        data_to_send = ""
        for jogo in jogos["jogos"]:
            data_to_send += f"**{jogo['homeTeam']}** `{jogo['resultado']}` **{jogo['awayTeam']}**\n"
        
        data_to_send += f"\n*Utilize `td!pontuacao {jornada['id_jornada']}` para verificar a pontuação!*"
        embed.description = data_to_send
        embed.set_thumbnail(url = logo)

        maximum = database["totobola"][jornada["id_jornada"]].find_one({}, {"_id": 0, "pontuacao" : 1}, sort = [("pontuacao", pymongo.DESCENDING)], limit = 1)
        vencedores = database["totobola"][jornada["id_jornada"]].find({"pontuacao" : {"$gte" : maximum["pontuacao"]}}, {"_id": 0, "pontuacao" : 1, "player_id" : 1})

        winners = []

        for winner in vencedores:
            winners.append(winner["player_id"])
            database["totobola"][jornada["id_jornada"].split(":")[0]].update_one({"player_id" : winner["player_id"]}, {"$inc" : {"vitorias" : 1}}) 
        
        winners = {
            "id_jornada" : jornada["id_jornada"],
            "vencedores" : winners,
            "pontuacao" : maximum
        }
        
        database["totobola"]["geraldes"].insert_one(winners)

        await channel.send(embed = embed)
        
    else:
        jogo = database["totobola"]["jornadas"].find_one({"id_jornada" : jornada["id_jornada"]},{"_id" : 0, "jogos" : {"$elemMatch" : {"id_jogo" : game["id"]}}})

        resultado = f"**{jogo['jogos'][0]['homeTeam']}** `{jogo['jogos'][0]['resultado']}` **{jogo['jogos'][0]['awayTeam']}**"

        embed = discord.Embed(title = "Resultado", colour = discord.Colour.greyple())
        embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`")
        embed.description = resultado
        embed.set_thumbnail(url = logo)
        
        channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
        channel = client.get_channel(channel["channel"])

        await channel.send(embed = embed)