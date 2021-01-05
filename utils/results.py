import pymongo
import asyncio

api_to_db = {
    "AWAY_TEAM" : "awayWin",
    "HOME_TEAM" : "homeWin",
    "DRAW" : "draw"
}

async def calculate(game, client):
    database = pymongo.MongoClient(port = 27017)

    jornada = database["totobola"]["jornadas"].find_one({"estado" : "ATIVA", "jogos.id_jogo" : game["id"], "jogos.$.estado" : {"$ne" : "PROCESSED"}},
                                                        {"_id" : 0, "id_jornada": 1, "competicao" : 1})

    if jornada is None: return

    apostas = database["totobola"][jornada["id_jornada"]].find({"apostas.id_jogo" : game["id"], "apostas.resultado" : {"$ne" : None}},
                                                                {"_id" : 0, "player_id" :1, "joker" : 1, "pontuacao" : 1, "apostas" : {"$elemMatch" : {"id_jogo" : game["id"]}}})

    #print(apostas)
    result = f"{game['score']['fullTime']['homeTeam']}-{game['score']['fullTime']['awayTeam']}"
    print(result)

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
            
            database["totobola"]["total"].update_one({"player_id": aposta["player_id"], "p_competicoes.competicao" : jornada["competicao"]},
                                                     { "$inc" : {"pontuacao" : pontuacao, "p_competicoes.$.pontuacao" : pontuacao}})

    database["totobola"]["jornadas"].update_one({"id_jornada" : jornada["id_jornada"], "jogos.id_jogo" : game["id"]},
                                            { "$set" : { "jogos.$.estado" : "PROCESSED", "jogos.$.resultado": result, "jogos.$.tendencia" : api_to_db[game["score"]["winner"]]},
                                            "$unset" : {"jogos.$.h2hHome" : 1, "jogos.$.h2hAway" : 1}})

    if (database["totobola"]["jornadas"].count_documents({"id_jornada" : jornada["id_jornada"], "jogos" : {"$elemMatch" : {"estado" : {"$ne" : "PROCESSED"}}}}) == 0):
        database["totobola"]["jornadas"].update_one( { "id_jornada" : jornada["id_jornada"] },
                                                     {"$set" : {"estado" : "TERMINADA"}} )
        
        # Calcular cena de equipa
        channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
        channel = client.get_channel(channel["channel"])

        await channel.send("piu")
        # Mandar mensagem a dizer que jornada terminou