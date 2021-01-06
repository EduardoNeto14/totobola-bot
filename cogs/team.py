import discord
from discord.ext import commands
import pymongo
import random

class Team(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(brief = "**Cria uma equipa!**", description = "**Utilização:** `td!team [jogador] [jogador]`")
    async def team(self, ctx, name: str, member1 : discord.abc.User, member2 : discord.abc.User):
        print(isinstance(name, discord.abc.User))
        print(isinstance(member1, discord.abc.User))
        print(isinstance(member2, discord.abc.User))
        
        color = "#" + "".join([random.choice("0123456789ABCDEF") for j in range(6)])
        # TODO: Verificar se o nome da equipa existe
        # TODO: Verificar se os membros não pertencem a outra equipa
        # TODO: Gerar ID e verificar se é válido
        # TODO: Escolher cor para a equipa e ver se não foi atribuída
        # {
        #   "team_id": ""
        #   "team_name": ""
        #   "members" : []
        #   "color" : ""
        #   "pontuacao" : "" 
        # } 
        pass
    
    @commands.command(brief = "**Mostra o campeonato das equipas!**", description = "**Utilização:** `td!classificacao`")
    async def classificacao(self, ctx):
        pass

def setup(client):
    client.add_cog(Team(client))