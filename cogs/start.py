import discord
from discord.ext import commands
import uuid
import os
import pymongo
import json

PATH = "/home/eduardo/HDD/Development/Totobola"

class Start(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message):
        
        # Quero ter a certeza que recebi uma DM #
        if message.guild is None:
            
            # Vai acontecer no caso de estarmos a iniciar uma jornada #
            if os.path.isfile(f"{PATH}/temp/jornada.json"):
                with open(f"{PATH}/temp/jornada.json", "rb") as jornada:
                    jornada = json.load(jornada)

                # Quero ter a certeza que a pessoa que me está a enviar DMs é a mesma que iniciou jornada #
                if message.author.id == jornada["admin"]:
                    
                    # Cancelar #
                    if message.content == "n": 
                        os.remove(f"{PATH}/temp/jornada.json")
                    
                    # Sucesso #
                    elif message.content == "s":
                        print("Sucesso!\n")
                    

                    if jornada["competicao"] is None:
                        jornada["competicao"] = message.content
                        
                        embedMessage = discord.Embed()
                        embedMessage.title = "Criação de Jornada"
                        embedMessage.description = f"Competição: {jornada['competicao']}\nJornada: \n\nn - Cancelar\ns - Sucesso"
                        
                        await message.author.send(embed = embedMessage)
                    
                        with open(f"{PATH}/temp/jornada.json", "w") as create:
                            json.dump(jornada, create)
                        
                    elif jornada["jornada"] is None:
                        jornada["jornada"] = message.content
                        
                        await self.embed(message, jornada["competicao"], jornada["jornada"])
                        
                        with open(f"{PATH}/temp/jornada.json", "w") as create:
                            json.dump(jornada, create)

                    else:
                        jogos = message.content.split("\n")
                        
                        for jogo in jogos:
                            jornada["jogos"].append(jogo)
                        
                        await self.embed(message, jornada["competicao"], jornada["jornada"], jornada["jogos"])

                        with open(f"{PATH}/temp/jornada.json", "w") as create:
                            json.dump(jornada, create)                    

    @commands.command()
    async def start(self, ctx):

        if os.path.isfile(f"{PATH}/temp/jornada.json"):
            return

        data = {
            "admin" : ctx.author.id,
            "competicao" : None,
            "jornada" : None,
            "jogos"  : []
        }

        with open(f"{PATH}/temp/jornada.json", "w") as create:
            json.dump(data, create)

        self.embed(ctx)

    @staticmethod
    async def embed(ctx, competicao = "", jornada = "", jogos = []):

        embedMessage = discord.Embed()
        embedMessage.title = "Criação de Jornada"
        embedMessage.add_field("Competição", competicao)
        embedMessage.add_field("Jornada", jornada)

        for j, jogo in enumerate(jogos):
            embedMessage.add_field(f"Jogo {j+1}", jogo)

        await ctx.author.send(embed = embedMessage)

def setup(client):
    client.add_cog(Start(client))