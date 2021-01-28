import discord
from discord.ext import commands
import pymongo
import random
import asyncio
import logging

SECONDS = 60
MINUTES = 10

logo = "https://cdn.discordapp.com/attachments/786651440528883745/797114794951704596/logo_totobola.png"

class Team(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)

        formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

        file_handler = logging.FileHandler("logs/team.log")
        file_handler.setFormatter(formatter)

        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

    async def team_confirmation(self, ctx, init_member, confirm_member, team_name, team_id, color, msg = None):
            
        embed = discord.Embed()
        embed.set_author(icon_url = confirm_member.avatar_url, name = f"{confirm_member.display_name} desejas criar uma equipa com {init_member.display_name}?")
        embed.set_footer(text = "Totobola Discordiano", icon_url = logo)
        
        if msg is not None:
            await msg.edit(embed=embed)
            
            if not isinstance(msg.channel, discord.abc.PrivateChannel):
                await msg.clear_reactions()
        else:
            msg = await ctx.send(embed = embed)

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        # wait for reactions (2 minutes)
        def check(reaction, user):
            return True if user != self.client.user and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == msg.id else False
        
        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=MINUTES * SECONDS, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
        
        else:
            if reaction is None:
                return
            elif reaction.emoji == '✅' and user.id == confirm_member.id:
                # Add to database
                database = pymongo.MongoClient(port = 27017)

                team = {
                    "team_id" : team_id,
                    "name" : team_name,
                    "color" : color,
                    "players" : [init_member.id, confirm_member.id],
                    "pontuacao" : 0
                }

                database["totobola"]["teams"].insert_one(team)
                database["totobola"]["jogadores"].update_one({"player_id" : init_member.id}, {"$set" : {"team_id" : team_id}})
                database["totobola"]["jogadores"].update_one({"player_id" : confirm_member.id}, {"$set" : {"team_id" : team_id}})

                embed = discord.Embed(title = "Equipa", colour = color)
                embed.add_field(name = "Nome", value = f"`{team_name}`")
                embed.add_field(name = "Jogador", value = f"`{init_member.display_name}`")
                embed.add_field(name = "Jogador", value = f"`{confirm_member.display_name}`")
                embed.add_field(name = "ID", value = f"`{team_id}`")
                embed.set_footer(text = "Totobola Discordiano")
                embed.set_thumbnail(url = logo)

                self.logger.info(f"[team_confirmation] {confirm_member.display_name} -> Aceitou formar equipa!")
                await ctx.send(embed = embed)

                await msg.delete()

            elif reaction.emoji == '❌' and user.id == confirm_member.id:
                self.logger.info(f"\n[team_confirmation] {confirm_member.display_name} -> Recusou formar equipa!")
                return
            elif user.id != confirm_member.id:
                self.logger.info(f"\n[team_confirmation] {confirm_member.display_name} -> Não é o membro correto!")
                await self.team_confirmation(ctx = ctx, msg = msg, init_member = init_member, confirm_member = confirm_member, team_name = team_name, team_id = team_id, color = color)
    
    @commands.command(brief = "**Cria uma equipa!**", description = "**Utilização:** `td!team [nome] [jogador]`")
    async def team(self, ctx, name: str, member1 : discord.abc.User):
        print(isinstance(member1, discord.abc.User))
        database = pymongo.MongoClient(port = 27017)

        if not isinstance(member1, discord.abc.User):
            await ctx.send(":x: **Precisa de mencionar um jogador válido!**")
        else:
            if database["totobola"]["teams"].count_documents({"name" : name}) > 0:
                await ctx.send(":x: **Nome da equipa já utilizado!**")
                return
            
            if database["totobola"]["teams"].count_documents({"players" : {"$all" : [ctx.message.author.id, member1.id]}}) > 0:
                await ctx.send(":x: **Um dos elementos já pertence a outra equipa!**")
                return
            
            color = int("".join([random.choice("0123456789ABCDEF") for j in range(6)]), 16)

            while database["totobola"]["teams"].count_documents({"color" : color}) != 0:
                color = int("".join([random.choice("0123456789ABCDEF") for j in range(6)]), 16)
            
            team_id = "".join([random.choice("0123456789ABCDEF") for j in range(6)])
            
            while database["totobola"]["teams"].count_documents({"team_id" : team_id}) != 0:
                team_id = "".join([random.choice("0123456789ABCDEF") for j in range(6)])

            await self.team_confirmation(ctx = ctx, init_member = ctx.message.author, confirm_member = member1, team_name = name, team_id = team_id, color = color)
    
    @commands.command(brief = "**Mostra o campeonato das equipas!**", description = "**Utilização:** `td!classificacao`")
    async def classificacao(self, ctx):
        await self.team_pages(ctx = ctx)

    async def team_pages(self, ctx, msg = None, start = 0, per_page = 10, max = None):
        database = pymongo.MongoClient(port = 27017)

        if max is None:
            max = int(database["totobola"]["teams"].count_documents({}) / per_page) + 1
    
        teams = database["totobola"]["teams"].aggregate(
                [{"$lookup" : 
                            { "from" : "jogadores", "localField" : "players", "foreignField" : "player_id", "as" : "names"}},
                {"$sort" : {"pontuacao" : -1}},
                {"$project" :
                            { "player_id" : 1, "names" : 1, "name" : 1, "pontuacao" : 1}},
                {"$limit" : per_page},
                {"$skip" : start*per_page}
            ])

        data_to_send = ""
        for t, team in enumerate(teams):
            print(team)
            if t + start*per_page < 3:
                medals = [":first_place:", ":second_place:", ":third_place:"]

                data_to_send += f"{medals[t]} **{team['name']}**\t\t\t:dart: `{team['pontuacao']}`pts\n👤 `{team['names'][0]['player_name']}`\t\t\t👤 `{team['names'][1]['player_name']}`\n\n"

            else:
                data_to_send += f"`{t+1}º` **{team['name']}**\t\t\t:dart: `{team['pontuacao']}`pts\n👤 `{team['names'][0]['player_name']}`\t\t\t👤 `{team['names'][1]['player_name']}`\n\n"

        embed = discord.Embed(title = f"Ranking Equipas", colour = discord.Colour.dark_magenta())
        embed.description = data_to_send
        embed.set_thumbnail(url = logo)
        embed.set_footer(text = "Totobola Discordiano")

        if msg is not None:
            await msg.edit(embed=embed)
            if not isinstance(msg.channel, discord.abc.PrivateChannel):
                await msg.clear_reactions()
        else:
            msg = await ctx.send(embed=embed)
        
        if start > 0:
            await msg.add_reaction('⏪')
        if start < max - 1:
            await msg.add_reaction('⏩')

        # wait for reactions (2 minutes)
        def check(reaction, user):
            return True if user != self.client.user and str(reaction.emoji) in ['⏪', '⏩'] and reaction.message.id == msg.id else False
        
        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=120, check=check)
        except asyncio.TimeoutError:
            await msg.delete()
        
        else:
            # redirect on reaction
            if reaction is None:
                return
            elif reaction.emoji == '⏪' and start > 0:
                await self.team_pages(ctx=ctx, msg=msg, start=start-1, per_page=per_page, max=max)
            elif reaction.emoji == '⏩' and start < max - 1:
                await self.team_pages(ctx=ctx, msg=msg, start=start+1, per_page=per_page, max=max)

def setup(client):
    client.add_cog(Team(client))