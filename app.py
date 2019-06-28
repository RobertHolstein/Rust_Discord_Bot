import discord
from discord.ext import commands
import asyncio
import requests
import json
from os import path

with open('config.json') as json_config:
    config = json.load(json_config)


steam_user_id = config["steam"]["steam_user_id"]
rust_game_id = config["steam"]["game_id"]
steam_api_key = config["steam"]["steam_api_key"]
steam_api_url_game_stats = f"http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?appid={rust_game_id}&key={steam_api_key}&steamid={steam_user_id}"

def get_steam_rust_data():
    return requests.get(steam_api_url_game_stats).json()

def get_local_rust_data():
    with open('my_rust_data.json') as json_rust_data:
        local_rust_data = json.load(json_rust_data)
    return local_rust_data

def check_rust_kills():
    get_rust_data = get_steam_rust_data()

    if not path.exists("my_rust_data.json"):
        print("Rust data file does not exists. Creating...")
        update_my_rust_data(get_rust_data())

    local_rust_player_stats = get_local_rust_data()["playerstats"]["stats"]
    steam_rust_player_stats = get_rust_data["playerstats"]["stats"]
    for stat in local_rust_player_stats:
        if(stat["name"] == "kill_player"):
            local_kills = stat["value"]
    for stat in steam_rust_player_stats:
        if(stat["name"] == "kill_player"):
            steam_kills = stat["value"]

    if steam_kills > local_kills:
        new_kills = steam_kills-local_kills
        print(f"You got {new_kills} kills!")
        update_my_rust_data(get_rust_data)
        return new_kills
    else:
        print(f"You suck")
        return 0

def update_my_rust_data(data):
    with open('my_rust_data.json', "w+") as my_rust_data:
        my_rust_data.write(json.dumps(data, indent=4, sort_keys=True))

bot = commands.Bot(command_prefix='?')

@bot.command()
async def rustkills(ctx):
    while True:
        kills = check_rust_kills()
        if kills > 0:
            await ctx.send(f"You killed {kills} people!")
        await asyncio.sleep(5)

bot.run(config["discord"]["discord_bot_token"])