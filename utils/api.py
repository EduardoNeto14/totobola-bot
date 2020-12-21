import asyncio
import pymongo
import requests

PATH = "/home/eduardo/HDD/Development/Totobola"

result_to_team = {
    "AWAY_TEAM": "awayTeam",
    "HOME_TEAM": "homeTeam"
}

async def check_games():
    database = pymongo.MongoClient(port = 27017)

    #merge IDS from competitions
    while True:
        # TODO: Atualizar os jogos conforme a API
        # TODO: Verficar se algum jogo terminou
        # TODO: Se terminou calcular pontuação
        # TODO: Se todos os jogos estiverem STATIC, terminar jornada

        jornadas_ativas = database["totobola"]["jornadas"].find({"estado" : "ATIVA", "jogos.estado" : {"$ne" : "PROCESSED"}}, {"_id" : 0})

        for jornada in jornadas_ativas:
            print(jornada)
            #database["totobola"]["jornada"].update({"id_jornada" : jornada["id_jornada"], "jogos.id_jogo" : })
        
        await asyncio.sleep(60)

async def get_h2h(match):
    with open(f"{PATH}/api-token.txt", "rb") as token:
        api_token = token.readline()
    
    #/v2/teams/[id]/matches
    id_home = match["homeTeam"]["id"]
    print(match["homeTeam"])
    id_away = match["awayTeam"]["id"]
    print(match["awayTeam"])
    ids = [id_home, id_away]
    
    home = []
    away = []
    result = [home, away]

    for i, _id in enumerate(ids):
        data = requests.get(f"http://api.football-data.org/v2/teams/{_id}/matches/",
                     params={"status" : "FINISHED", "limit" : 5},
                     headers={"X-Auth-Token" : api_token}).json()

#        print(data)

        for m in data["matches"]:
            teams_id = [m["homeTeam"]["id"], m["awayTeam"]["id"]]
            teams_name = [m["homeTeam"]["name"], m["awayTeam"]["name"]]

            this = teams_id.index(int(_id))
            field = "homeTeam" if this == 0 else "awayTeam"

            other = teams_name[int(not this)] 
            
            if m["score"]["winner"] == "DRAW":
                icon = ":yellow_circle:"

            else:
                if result_to_team[m["score"]["winner"]] == field : icon = ":green_circle:"
                else : icon = ":red_circle:"

            result[i].append(f"{icon} {m['score']['fullTime']['homeTeam']}-{m['score']['fullTime']['awayTeam']} vs {other}")
    
    await asyncio.sleep(15)
    
    return result[0], result[1]

def get_jornada(code, n_jornada):
    with open(f"{PATH}/api-token.txt", "rb") as token:
        token = token.readline()
    
    request = requests.get(f"http://api.football-data.org/v2/competitions/{code}/matches",
                            params = {"matchday" : n_jornada, "status" : "SCHEDULED"},
                            headers = {"X-Auth-Token" : token}).json()

    return request

def get_num_jornada(code):
    with open(f"{PATH}/api-token.txt", "rb") as token:
        token = token.readline()

    request = requests.get(f"http://api.football-data.org/v2/competitions/{code}",
                            headers = {"X-Auth-Token" : token}).json()

    return request["currentSeason"]["currentMatchday"]