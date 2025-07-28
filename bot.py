import json
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(command_prefix="!", intents=intents)
DATA_FILE = "submissions.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

###
# Commands
# ShowChallenges      - Shows Current Challenges for this week
# AddChallenge        - Adds Challenge Entry
# Leaderboard         - Shows one leaderboard per message - default: SHOW:ALL; if SHOW:EVENT NAME; shows only the event name
# Submit              - Adds an entry in the HHMMSS format for the current user

@bot.command()
async def submit(ctx, event_name: str, time: str):
    data = load_data()
    if event_name not in data:
        data[event_name] = []
    # Check for : in submission
    if not ':' in time:
        await ctx.send(f"Please submit date format in HH:MM:SSS")
    else:
        data[event_name].append({"user": ctx.author.name, "time": time})
        save_data(data)
        await ctx.send(f"{ctx.author.mention} submitted time `{time}` for event `{event_name}`!")

@bot.command()
async def remove(ctx, event_name: str):
    data = load_data()
    if event_name not in data:
        data[event_name] = []
    del data[event_name]
    save_data(data)
    await ctx.send(f"{ctx.author.mention} removed event `{event_name}` :(")

@bot.command()
async def showchallenges(ctx):
    data = load_data()
    if not data:
        await ctx.send("No challenges have been added yet.")
        return

    challenges = "\n".join([f"- {event}" for event in data.keys()])
    await ctx.send(f"**Current Challenges:**\n{challenges}")

@bot.command()
async def leaderboard(ctx, *, event_name: str = None):
    data = load_data()
    
    def parse_time(t):
        """Convert M:SS:MMM or M:SS.MMM into total seconds (float) for sorting."""
        parts = t.replace('.', ':').split(':')
        # Supports formats like "0:17:060" or "1:45.678"
        minutes = int(parts[0])
        seconds = int(parts[1])
        milliseconds = int(parts[2]) if len(parts) > 2 else 0
        return minutes * 60 + seconds + milliseconds / 1000.0

    if not data:
        await ctx.send("No events found yet.")
        return
    
    if event_name:
        # Show leaderboard for a single event
        if event_name not in data:
            await ctx.send(f"No submissions found for `{event_name}`.")
            return

        entries = sorted(data[event_name], key=lambda x: parse_time(x["time"]))
        msg = f"**Leaderboard for {event_name}**\n"
        for i, entry in enumerate(entries, start=1):
            msg += f"{i}. {entry['user']} - {entry['time']}\n"
        await ctx.send(msg)
    else:
        # Show all leaderboards
        for event, submissions in data.items():
            entries = sorted(submissions, key=lambda x: parse_time(x["time"]))
            msg = f"**Leaderboard for {event}**\n"
            for i, entry in enumerate(entries, start=1):
                msg += f"{i}. {entry['user']} - {entry['time']}\n"
            await ctx.send(msg)




bot.run(TOKEN)