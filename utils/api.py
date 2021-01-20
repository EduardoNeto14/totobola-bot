import asyncio
import pymongo
import requests
import logging

from results import calculate

PATH = "/home/eduardo/HDD/Development/Totobola"

result_to_team = {
    "AWAY_TEAM": "awayTeam",
    "HOME_TEAM": "homeTeam"
}

logger = logging.getLogger(__name__)

formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

file_handler = logging.FileHandler("logs/info.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

logger.addHandler(file_handler)

async def check_games(client):
    database = pymongo.MongoClient(port = 27017)
    active = True

    #merge IDS from competitions
    while active:
        active_matchday = set()

        jornadas = database["totobola"]["jornadas"].find({"estado" : "ATIVA"}, {"_id" : 0, "link" : 1, "jogos.id_jogo" : 1, "jogos.estado" : 1})
        
        for jornada in jornadas:
            if isinstance(jornada["link"], int):
                active_matchday.update([jornada["link"]])
            else:
                active_matchday.update(jornada["link"])
        
        active_matchday = map(str, active_matchday)
        active_matchday = ",".join(active_matchday)

        logger.info(f"\n\n[CHECKING API]\n\n")
        logger.info(f"\n[Active Matchdays] {active_matchday}")
        with open(f"{PATH}/api-token.txt", "rb") as token:
            token = token.readline()
        
            request = requests.get(f"http://api.football-data.org/v2/matches/",
                                    params = {"competitions" : active_matchday},
                                    headers = {"X-Auth-Token" : token}).json()
        
        for match in request["matches"]:
            if match["status"] == "SCHEDULED":
                logger.info(f"{match['id']} -> SCHEDULED")
                # Não tem que se fazer nada, pois o jogo ainda não começou
            elif match["status"] == "LIVE" or match["status"] == "IN_PLAY":
                logger.info(f"{match['id']} -> LIVE")
                # Atualizar o estado do jogo na base de dados, para que o jogo fique bloqueado
                database["totobola"]["jornadas"].update({"jogos.id_jogo" : match["id"]}, {"$set" : {"jogos.$.estado" : "LIVE"}})
                
                for jornada in jornadas:
                    for jogo in jornada["jogos"]:
                        if match["id"] == jogo["id_jogo"]:
                            database["totobola"][jornada["id_jornada"]].update({"joker.id_jogo" : match["id"]}, {"$set" : {"joker.$.processed" : 1}})
                            break

                # Talvez atualizar resultado?
            elif match["status"] == "FINISHED":
                logger.info(f"{match['id']} -> FINISHED")
                await calculate(match, client)
                # Verificar se o jogo foi processado. Se sim, passar à frente. Se não, calcular pontos.
            else:
                logger.warning(f"{match['id']} -> {match['status']}")
        
        if (database["totobola"]["jornadas"].count_documents({"estado" : "ATIVA"})) == 0:
            logger.info(f"\n[DONE] No active matchdays!")
            active = False
        
        await asyncio.sleep(60)
        
async def get_h2h(match):
    with open(f"{PATH}/api-token.txt", "rb") as token:
        api_token = token.readline()
    
    logger.info(f"\n\n[CHECING H2H]\n\n")
    id_home = match["homeTeam"]["id"]
    logger.info(match["homeTeam"])
    id_away = match["awayTeam"]["id"]
    logger.info(match["awayTeam"])
    ids = [id_home, id_away]
    
    home = []
    away = []
    result = [home, away]

    for i, _id in enumerate(ids):
        data = requests.get(f"http://api.football-data.org/v2/teams/{_id}/matches/",
                     params={"status" : "FINISHED", "limit" : 5},
                     headers={"X-Auth-Token" : api_token}).json()

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

            result[i].append(f"{icon} `{m['score']['fullTime']['homeTeam']}-{m['score']['fullTime']['awayTeam']} vs {other}`")
    
    await asyncio.sleep(15)
    
    return result[0], result[1]

def get_jornada(code, n_jornada):
    with open(f"{PATH}/api-token.txt", "rb") as token:
        token = token.readline()

    logger.info(f"\n\n[CHECKING MATCHDAY] {code}\n\n") 
    request = requests.get(f"http://api.football-data.org/v2/competitions/{code}/matches",
                            params = {"matchday" : n_jornada, "status" : "SCHEDULED"},
                            headers = {"X-Auth-Token" : token}).json()

    return request

def get_num_jornada(code):
    with open(f"{PATH}/api-token.txt", "rb") as token:
        token = token.readline()

    logger.info(f"\n\n[CHECKING MATCHDAY NUMBER] {code}\n\n") 
    request = requests.get(f"http://api.football-data.org/v2/competitions/{code}",
                            headers = {"X-Auth-Token" : token}).json()

    return request["currentSeason"]["currentMatchday"]