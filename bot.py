import json
import os
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
DATA_FILE = "submissions.json"
TRACKS_FILE = "circuits.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_tracks():
    if os.path.exists(TRACKS_FILE):
        with open(TRACKS_FILE, "r") as f:
            return json.load(f)
    return {}

# Autocomplete function for event names
async def event_autocomplete(interaction: discord.Interaction, current: str):
    data = load_data()
    events = list(data.keys())
    # Filter events that start with the current input (case-insensitive)
    filtered = [event for event in events if current.lower() in event.lower()]
    # Return up to 25 choices (Discord's limit)
    return [
        discord.app_commands.Choice(name=event, value=event)
        for event in filtered[:25]
    ]

# Autocomplete function for regions
async def region_autocomplete(interaction: discord.Interaction, current: str):
    regions = ["asia", "america", "europe", "all"]
    # Add snow_dirt to options if dirt parameter is enabled (we can't check it here, so always include it)
    regions.append("snow_dirt")
    # Filter regions that start with the current input (case-insensitive)
    filtered = [region for region in regions if current.lower() in region.lower()]
    return [
        discord.app_commands.Choice(name=region.replace("_", "/").title(), value=region)
        for region in filtered
    ]

###
# Slash Commands
# /showchallenges    - Shows Current Challenges for this week
# /addchallenge      - Adds Challenge Entry (creates empty event)
# /leaderboard       - Shows leaderboard(s) - default: all; specify event for single
# /submit            - Adds an entry in the HHMMSS format for the current user
# /remove            - Removes an event
# /randomize_track   - Selects a random Gran Turismo track from specified region


@bot.tree.command(name="submit", description="Submit your time for an event")
@discord.app_commands.describe(
    event_name="The name of the event to submit to",
    time="Your time in HH:MM:SSS or MM:SS.MMM format"
)
@discord.app_commands.autocomplete(event_name=event_autocomplete)
async def submit(interaction: discord.Interaction, event_name: str, time: str):
    data = load_data()
    if event_name not in data:
        data[event_name] = []
    
    # Check for : or . in submission
    if not (':' in time or '.' in time):
        await interaction.response.send_message(f"Please submit time format in HH:MM:SSS or MM:SS.MMM")
    else:
        data[event_name].append({"user": interaction.user.display_name, "time": time})
        save_data(data)
        await interaction.response.send_message(f"{interaction.user.mention} submitted time `{time}` for event `{event_name}`!")

@bot.tree.command(name="remove", description="Remove an event")
@discord.app_commands.describe(event_name="The name of the event to remove")
@discord.app_commands.autocomplete(event_name=event_autocomplete)
async def remove(interaction: discord.Interaction, event_name: str):
    data = load_data()
    if event_name not in data:
        await interaction.response.send_message(f"Event `{event_name}` doesn't exist!")
        return
    
    del data[event_name]
    save_data(data)
    await interaction.response.send_message(f"{interaction.user.mention} removed event `{event_name}` :(")

@bot.tree.command(name="addchallenge", description="Add a new challenge/event")
@discord.app_commands.describe(event_name="The name of the new event to create")
async def addchallenge(interaction: discord.Interaction, event_name: str):
    data = load_data()
    if event_name in data:
        await interaction.response.send_message(f"Event `{event_name}` already exists!")
        return
    
    data[event_name] = []
    save_data(data)
    await interaction.response.send_message(f"Created new event: `{event_name}`!")

@bot.tree.command(name="showchallenges", description="Show all current challenges")
async def showchallenges(interaction: discord.Interaction):
    data = load_data()
    if not data:
        await interaction.response.send_message("No challenges have been added yet.")
        return

    challenges = "\n".join([f"- {event}" for event in data.keys()])
    await interaction.response.send_message(f"**Current Challenges:**\n{challenges}")

@bot.tree.command(name="leaderboard", description="Show leaderboard(s)")
@discord.app_commands.describe(event_name="Specific event to show leaderboard for (optional)")
@discord.app_commands.autocomplete(event_name=event_autocomplete)
async def leaderboard(interaction: discord.Interaction, event_name: str = None):
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
        await interaction.response.send_message("No events found yet.")
        return
    
    if event_name:
        # Show leaderboard for a single event
        if event_name not in data:
            await interaction.response.send_message(f"No submissions found for `{event_name}`.")
            return

        entries = sorted(data[event_name], key=lambda x: parse_time(x["time"]))
        msg = f"**Leaderboard for {event_name}**\n"
        for i, entry in enumerate(entries, start=1):
            msg += f"{i}. {entry['user']} - {entry['time']}\n"
        await interaction.response.send_message(msg)
    else:
        # Show all leaderboards
        await interaction.response.defer()  # Defer since we might send multiple messages
        for event, submissions in data.items():
            entries = sorted(submissions, key=lambda x: parse_time(x["time"]))
            msg = f"**Leaderboard for {event}**\n"
            for i, entry in enumerate(entries, start=1):
                msg += f"{i}. {entry['user']} - {entry['time']}\n"
            await interaction.followup.send(msg)

@bot.tree.command(name="randomize_track", description="Get a random Gran Turismo track from a specific region")
@discord.app_commands.describe(
    region="The region to select a track from (Asia, America, Europe, Fictional, or All)",
    dirt="Include snow/dirt tracks in the selection (default: False)"
)
@discord.app_commands.autocomplete(region=region_autocomplete)
async def randomize_track(interaction: discord.Interaction, region: str, dirt: bool = False):
    tracks_data = load_tracks()
    
    if not tracks_data:
        await interaction.response.send_message(f"Track data file not found. Please make sure `{TRACKS_FILE}` exists in server side.")
        return
    
    region_lower = region.lower()
    
    # Filter out snow_dirt tracks unless dirt flag is True
    filtered_tracks_data = {}
    for key, track_list in tracks_data.items():
        if key == "snow_dirt" and not dirt:
            continue  # Skip snow_dirt tracks if dirt flag is False
        filtered_tracks_data[key] = track_list
    
    if region_lower == "all":
        # Combine all tracks from all regions (excluding snow_dirt unless dirt=True)
        all_tracks = []
        for key, region_tracks in filtered_tracks_data.items():
            if key != "snow_dirt":  # Don't include snow_dirt in "all" even with dirt=True
                all_tracks.extend(region_tracks)
        if dirt and "snow_dirt" in tracks_data:
            all_tracks.extend(tracks_data["snow_dirt"])
        tracks = all_tracks
        region_display = "All Regions" + (" (including Dirt)" if dirt else "")
    elif region_lower == "snow_dirt" or region_lower == "dirt":
        if not dirt:
            await interaction.response.send_message("Snow/dirt tracks are only available when the `dirt` flag is enabled!")
            return
        tracks = tracks_data.get("snow_dirt", [])
        region_display = "Snow/Dirt Tracks"
    else:
        if region_lower not in filtered_tracks_data:
            available_regions = ", ".join(list(filtered_tracks_data.keys()) + ["all"])
            if dirt:
                available_regions += ", snow_dirt"
            await interaction.response.send_message(f"Region `{region}` not found. Available regions: {available_regions}")
            return
        
        tracks = filtered_tracks_data[region_lower]
        region_display = region.title()
    
    if not tracks:
        await interaction.response.send_message(f"No tracks found for region `{region}`.")
        return
    
    selected_track = random.choice(tracks)
    
    # Create simple text message
    message = f"**{selected_track}** ({region_display})"
    if dirt:
        message += " - Dirt Mode Enabled"
    
    await interaction.response.send_message(message)

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


bot.run(TOKEN)