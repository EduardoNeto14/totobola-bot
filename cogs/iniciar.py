import discord
from discord.ext import commands

import pymongo

class Iniciar(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def iniciar(self, ctx, *args):
        database = pymongo.MongoClient(port = 27017)

        if "totobola" not in database.list_database_names():
            totobola = database["totobola"]

            jogadores = totobola["jogadores"]
            
            jogadores.insert_one({
                "user_id" : ctx.author.id,
                "username" : ctx.author.name
            })

        print(database.list_database_names())
        #print(jogadores.list_collection_names())
        

def setup(client):
    client.add_cog(Iniciar(client))