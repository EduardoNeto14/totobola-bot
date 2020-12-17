import discord
from discord.ext import commands
import os
import pymongo
import json
import sys

PATH = "/home/eduardo/HDD/Development/Totobola"

sys.path.append(f"{PATH}/utils")

from utils import database_exists

class Registar(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        
        database = pymongo.MongoClient(port = 27017)
        
        if "totobola" not in database.list_database_names() or user.bot: return False
        else:
            message_id = database["totobola"]["registo"].find_one()["message_id"]
            if reaction.message.id != message_id or str(reaction) != "✍":
                return False

            else:
                if database["totobola"]["jogadores"].find_one({"player_name" : f"{user.display_name}"}) is None:
                    database["totobola"]["jogadores"].insert_one({"player_id" : user.id, "player_name" : user.display_name})
                    
                    for competicao in database["totobola"]["properties"].find_one()["competicoes"]:
                        database["totobola"][f"{competicao['competicao']}"].insert_one({"player_id" : user.id, "pontuacao" : 0})
                    
                    # TODO: Melhorar mensagem #
                    embed = discord.Embed(title="Registo", colour = discord.Colour.dark_green())
                    embed.set_thumbnail(url = user.avatar_url)
                    embed.set_footer(text = "Totobola Discordiano", icon_url = "https://media.discordapp.net/attachments/786651440528883745/788119312489381928/totoo.png")
                    embed.add_field(name = "**Estado**", value = "```Registado```")
                    embed.add_field(name = "**Nome**", value = f"```{user.display_name}```")
                    embed.description = "Muito obrigado por participares! \n\nBoa sorte!"
                    await user.send(embed = embed)
                
                else:
                    # TODO: Melhorar mensagem #
                    await user.send(f"Já te encontras registado, {user.display_name}!")

    @commands.command()
    @commands.check(database_exists)
    async def registar(self, ctx, *args):      

        database = pymongo.MongoClient(port = 27017)
        message_id = database["totobola"]["registo"].find_one()["message_id"]
        
        try:
            message = await ctx.fetch_message(message_id)
        
            await message.unpin()
            await message.delete()
        
        except discord.errors.NotFound:
            pass

        # TODO: Melhorar mensagem #
        embed = discord.Embed(title = "Registo", colour = discord.Colour.dark_gold())
        embed.set_thumbnail(url = "https://media.discordapp.net/attachments/786651440528883745/788119312489381928/totoo.png")
        embed.description = "Para te registares na prova, basta clicares no :writing_hand:."
        embed.set_footer(text = "Totobola Discordiano")
         
        message = await ctx.send(embed = embed)
        
        await message.add_reaction("✍")
        await message.pin()
        
        database["totobola"]["registo"].update_one(
            {"message_id": message_id},
            {"$set" : {"message_id": message.id}}
        )

def setup(client):
    client.add_cog(Registar(client))