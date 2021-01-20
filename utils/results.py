import pymongo
import asyncio
import discord
import logging

api_to_db = {
    "AWAY_TEAM" : "awayWin",
    "HOME_TEAM" : "homeWin",
    "DRAW" : "draw"
}

ranking_teams = [
    25,
    20,
    18,
    15,
    10,
    5,
    4,
    3,
    2,
    1
]

TOP = 10

logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"
logger = logging.getLogger(__name__)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

file_handler = logging.FileHandler("logs/info.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

logger.addHandler(file_handler)

async def calculate(game, client):
    database = pymongo.MongoClient(port = 27017)

    logger.info(f"[calculate] {game}")
    ''' Check if the id of the game belongs to an active matchday and if it wasn't already processed! '''
    jornada = database["totobola"]["jornadas"].find_one({"estado" : "ATIVA", "jogos.id_jogo" : game["id"], "jogos.$.estado" : {"$ne" : "PROCESSED"}},
                                                        {"_id" : 0, "id_jornada": 1, "competicao" : 1})

    ''' If the previous query returns nothing, than it must mean that the game was already processed and we shouldn't need to do anything!'''
    if jornada is None: return

    ''' Otherwise we retrieve every bet that has a valid value (not None)! '''
    apostas = database["totobola"][jornada["id_jornada"]].find({"apostas.id_jogo" : game["id"], "apostas.resultado" : {"$ne" : None}},
                                                                {"_id" : 0, "player_id" :1, "joker" : 1, "pontuacao" : 1, "apostas" : {"$elemMatch" : {"id_jogo" : game["id"]}}})

    ''' The result of the game! '''
    result = f"{game['score']['fullTime']['homeTeam']}-{game['score']['fullTime']['awayTeam']}"

    ''' For every bet ... '''
    for aposta in apostas:
        pontuacao = 0

        ''' If the result of the bet is equal to the actual result, 3 points are attributed! '''
        ''' If the user guessed the tendency of the game, 1 point is attributed! '''
        if aposta["apostas"][0]["resultado"] == result:
            pontuacao = 3
        elif aposta["apostas"][0]["tendencia"] == api_to_db[game["score"]["winner"]]:
            pontuacao = 1

        ''' If the user used the joker, the points are doubled! '''
        if aposta["joker"]["id_jogo"] == game["id"]:
            aposta["joker"]["processed"] = 1
            pontuacao *= 2

        if pontuacao != 0:
            ''' Increment the score in the corresponding bet! '''
            database["totobola"][jornada["id_jornada"]].update_one(
                                                                {"player_id" : aposta["player_id"]},
                                                                { "$set" : {"joker" : aposta["joker"], "pontuacao" : aposta["pontuacao"] + pontuacao}} )
            
            ''' Increment the score in the corresponding competition! '''
            database["totobola"][jornada["id_jornada"].split(":")[0]].update_one({"player_id" : aposta["player_id"]},
                                                                                 {"$inc" : {"pontuacao" : pontuacao}})
            
            ''' Increment the score in the overall table! '''
            database["totobola"]["total"].update_one({"player_id": aposta["player_id"], "p_competicoes.competicao" : jornada["competicao"]},
                                                     { "$inc" : {"pontuacao" : pontuacao, "p_competicoes.$.pontuacao" : pontuacao}})

    ''' Set the game as PROCESSED! '''
    database["totobola"]["jornadas"].update_one({"id_jornada" : jornada["id_jornada"], "jogos.id_jogo" : game["id"]},
                                            { "$set" : { "jogos.$.estado" : "PROCESSED", "jogos.$.resultado": result, "jogos.$.tendencia" : api_to_db[game["score"]["winner"]]},
                                            "$unset" : {"jogos.$.h2hHome" : 1, "jogos.$.h2hAway" : 1}})

    ''' If it's the last game in the matchday... '''
    if (database["totobola"]["jornadas"].count_documents({"id_jornada" : jornada["id_jornada"], "jogos" : {"$elemMatch" : {"estado" : {"$ne" : "PROCESSED"}}}}) == 0):
        await finish_matchday(client, jornada)
    
    # Otherwise...
    else:
        ''' Get the match info... '''
        jogo = database["totobola"]["jornadas"].find_one({"id_jornada" : jornada["id_jornada"]},{"_id" : 0, "jogos" : {"$elemMatch" : {"id_jogo" : game["id"]}}})

        ''' Send the result to the channel... '''
        resultado = f"**{jogo['jogos'][0]['homeTeam']}** `{jogo['jogos'][0]['resultado']}` **{jogo['jogos'][0]['awayTeam']}**"

        embed = discord.Embed(title = "Resultado", colour = discord.Colour.greyple())
        embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`")
        embed.description = resultado
        embed.set_thumbnail(url = logo)
        embed.set_footer(text = "Totobola Discordiano")
        channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
        channel = client.get_channel(channel["channel"])

        await channel.send(embed = embed)

async def finish_matchday(client, jornada):
    database = pymongo.MongoClient(port = 27017)
    
    ''' Set the status of the matchday as TERMINATED! '''
    database["totobola"]["jornadas"].update_one( { "id_jornada" : jornada["id_jornada"] },
                                                        {"$set" : {"estado" : "TERMINADA"}} )

    ''' Get all the scores... '''
    pontuacoes = database["totobola"][jornada["id_jornada"]].find({"estado" : {"$ne" : "INATIVA"}}, {"_id" : 0, "player_id" : 1, "pontuacao" : 1})

    position = 1
    last_pont = None

    ''' For every score... '''
    for p, pontuacao in enumerate(pontuacoes):
        
        ''' Only the TOP have bonus points '''
        if position > TOP:
            break
        
        ''' Basically, we want to know the actual position in the matchday of certain user...
            For that we follow this rule:

                Points   Position
                  15        1
                  15        1
                  14        3
                  11        4
                  10        5
                  10        5
                  10        5
                  -----------
        '''
        if last_pont is None:
            last_pont = pontuacao["pontuacao"]
        elif last_pont != pontuacao["pontuacao"]:
            position = p + 1
        
        ''' Check if the player has a team! '''
        team_id = database["totobola"]["jogadores"].find_one({"player_id" : pontuacao["player_id"]}, {"_id" : 0, "team_id" : 1})["team_id"]

        ''' If it has a team, we increment the team's score according to the user's position! '''
        if team_id is not None:
            database["totobola"]["teams"].update_one({"team_id" : team_id}, {"$inc" : {"pontuacao" : ranking_teams[position - 1]}})
    
    channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
    channel = client.get_channel(channel["channel"])

    embed = discord.Embed(title = "Jornada", colour = discord.Colour.blurple())
    embed.add_field(name = "Jornada", value = f"`{jornada['id_jornada']}`")
    
    ''' Show every game and its result of the matchday! '''
    jogos = database["totobola"]["jornadas"].find_one({"id_jornada" : jornada["id_jornada"]}, {"_id" : 0 , "jogos" : 1})

    data_to_send = ""
    for jogo in jogos["jogos"]:
        if jogo["resultado"] is not None:
            data_to_send += f"**{jogo['homeTeam']}** `{jogo['resultado']}` **{jogo['awayTeam']}**\n"
        else:
            data_to_send += f"~~{jogo['homeTeam']} - {jogo['awayTeam']}~~\n"
    
    data_to_send += f"\n*Utilize `td!pontuacao {jornada['id_jornada']}` para verificar a pontuação!*"
    embed.set_thumbnail(url = logo)

    ''' Calculate the winners of the matchday... '''
    maximum = database["totobola"][jornada["id_jornada"]].find_one({}, {"_id": 0, "pontuacao" : 1}, sort = [("pontuacao", pymongo.DESCENDING)], limit = 1)

    vencedores = database["totobola"][jornada["id_jornada"]].find({"pontuacao" : {"$gte" : maximum["pontuacao"]}}, {"_id": 0, "pontuacao" : 1, "player_id" : 1})

    winners = []

    for winner in vencedores:
        winners.append(winner["player_id"])
        database["totobola"][jornada["id_jornada"].split(":")[0]].update_one({"player_id" : winner["player_id"]}, {"$inc" : {"vitorias" : 1}}) 
    
    winners = {
        "id_jornada" : jornada["id_jornada"],
        "vencedores" : winners,
        "pontuacao" : maximum["pontuacao"]
    }
    
    database["totobola"]["geraldes"].insert_one(winners)

    vencedores = database["totobola"]["geraldes"].aggregate([
        {"$match" : {"id_jornada" : jornada["id_jornada"]}},
        { "$unwind" : { "path" : "$vencedores", "preserveNullAndEmptyArrays" : True}},
        { "$lookup" : {
            "from" : "jogadores",
            "localField" : "vencedores",
            "foreignField" : "player_id",
            "as" : "vencedores"
        }},
        {"$project" : {
            "vencedores.player_name" : 1
        }}
    ])

    str_winners = ""
    for vencedor in vencedores:
        str_winners += f"**{vencedor['vencedores'][0]['player_name']}**"
    
    embed.description = data_to_send
    
    embed.add_field(name = "Vencedores", value = str_winners)
    embed.add_field(name = "Pontuação", value = f"`{maximum['pontuacao']}`")
    embed.set_footer(text = "Totobola Discordiano")

    await channel.send(embed = embed)