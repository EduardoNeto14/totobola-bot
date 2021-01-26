import discord
from discord.ext import commands
import os

client = commands.Bot(command_prefix = "td!", help_command = None)
PATH = "/home/eduardo/HDD/Development/Totobola"

with open(f"{PATH}/token.txt", "r") as token:
    token = token.readline()

for filename in os.listdir(f"{PATH}/cogs"):
    if filename.endswith(".py") : client.load_extension(f"cogs.{filename[:-3]}")
    '''and filename != "teste.py"'''

client.run(token)