from utils import database_exists
import discord
from discord.ext import commands
from discord.utils import get
import os
import pymongo
import json
import sys
import logging

PATH = "/home/eduardo/HDD/Development/Totobola"
logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

sys.path.append(f"{PATH}/utils")


class Registar(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)

        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

        file_handler = logging.FileHandler("logs/registar.log")
        file_handler.setFormatter(formatter)
        self.logger.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):

        database = pymongo.MongoClient(port=27017)

        if "totobola" not in database.list_database_names() or user.bot:
            return False
        else:
            message_id = database["totobola"]["registo"].find_one()[
                "message_id"]
            if reaction.message.id != message_id or str(reaction) != "✍":
                return False

            else:
                if database["totobola"]["jogadores"].find_one({"player_name": f"{user.display_name}"}) is None:
                    database["totobola"]["jogadores"].insert_one(
                        {"player_id": user.id, "player_name": user.display_name, "team_id": None})

                    n_comps = []
                    for competicao in database["totobola"]["properties"].find_one()["competicoes"]:
                        database["totobola"][f"{competicao['competicao']}"].insert_one(
                            {"player_id": user.id, "pontuacao": 0, "apostas": 0, "vitorias": 0})
                        n_comps.append(
                            {"competicao": competicao['competicao'], "pontuacao": 0})

                    database["totobola"]["total"].insert_one(
                        {"player_id": user.id, "p_competicoes": n_comps, "pontuacao": 0})

                    # TODO: Melhorar mensagem #
                    embed = discord.Embed(
                        title="Registo", colour=discord.Colour.dark_green())

                    embed.set_thumbnail(url=user.avatar_url)

                    embed.set_footer(text="Totobola Discordiano", icon_url=logo)

                    embed.add_field(name="**Estado**", value="`Registado`")

                    embed.add_field(name="**Nome**",
                                    value=f"`{user.display_name}`")

                    embed.description = "Muito obrigado por participares! \n\nBoa sorte!"

                    await user.send(embed=embed)
                    self.logger.info(f"\n[on_reaction_add] {user.display_name} -> Registado no Totobola!")
                    
                    channel = database["totobola"]["properties"].find_one({}, {"_id" : 0, "channel" : 1})
                    channel = self.client.get_channel(channel["channel"])

                    embed = discord.Embed(colour = discord.Colour.dark_blue())
                    embed.set_author(icon_url = user.avatar_url, name = f"{user.display_name} registado com sucesso! Bem-vindo e boa sorte!")
                    embed.set_footer(text = "Totobola Discordiano", icon_url = logo)

                    await channel.send(embed = embed)
                    #role = get(reaction.message.guild.roles, name = "TotobolaDiscordiano")
                    # await user.add_roles(role)

                else:
                    self.logger.info(f"\n[on_reaction_add] {user.display_name} -> Jogador já se encontra registado!")
                    await user.send(f"Já te encontras registado, {user.display_name}!")

    @commands.command(brief="**Para efetuar o registo!**", description="**Utilização:** `td!registar`")
    @commands.check(database_exists)
    async def registar(self, ctx, *args):

        database = pymongo.MongoClient(port=27017)
        message_id = database["totobola"]["registo"].find_one()["message_id"]

        try:
            message = await ctx.fetch_message(message_id)

            await message.unpin()
            await message.delete()

        except discord.errors.NotFound:
            pass

        # TODO: Melhorar mensagem #
        embed = discord.Embed(
            title="Registo", colour=discord.Colour.dark_gold())
        embed.set_thumbnail(url=logo)
        embed.description = "Para te registares na prova, basta clicares no :writing_hand:."
        embed.set_footer(text="Totobola Discordiano")

        message = await ctx.send(embed=embed)

        await message.add_reaction("✍")
        await message.pin()

        database["totobola"]["registo"].update_one(
            {"message_id": message_id},
            {"$set": {"message_id": message.id}}
        )


def setup(client):
    client.add_cog(Registar(client))
