#!/usr/bin/python
import discord
from discord.ext import commands
import asyncio
import aiofiles
import requests
import json
from os import path
import logging
from fuzzywuzzy import process

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

with open('config.json') as json_config:
    config = json.load(json_config)


def get_user_steam_rust_data(steam_user_id):
    qparams  = (
        ('appid', config["steam"]["game_id"]),
        ('key', config["steam"]["api_key"]),
        ('steamid', steam_user_id)
    )
    request = requests.get(config["steam"]["api_url"], params=qparams)
    if request.status_code == 200:
        return request.json()
    else:
        return 500



def get_local_rust_data():
    if not path.exists("rust_data.json"):
        print("Rust data file does not exists. Creating...")
        create_rust_data_file()

    with open('rust_data.json', 'r+') as json_rust_data:
        local_rust_data = json.load(json_rust_data)
    return local_rust_data


async def check_rust_kills(local_rust_user_data):
    steam_data = get_user_steam_rust_data(local_rust_user_data["playerstats"]["steamID"])

    steam_rust_player_stats = steam_data["playerstats"]["stats"]
    for stat in local_rust_user_data["playerstats"]["stats"]:
        if(stat["name"] == "kill_player"):
            local_kills = stat["value"]
            break
    for stat in steam_rust_player_stats:
        if(stat["name"] == "kill_player"):
            steam_kills = stat["value"]
            break

    if steam_kills > local_kills:
        new_kills = steam_kills-local_kills
        local_rust_data = await get_local_rust_data_object()
        await update_rust_data_file(local_rust_data, steam_data, local_rust_user_data["discord_id"], True)
        return new_kills
    else:
        return 0


def create_rust_data_file():
    with open("rust_data.json", "w+") as rust_data_file:
        json_template = {}
        json_template["users"] = []
        rust_data_file.write(json.dumps(json_template, indent=4, sort_keys=True))


async def update_rust_data_file(local_data, steam_data, discord_user_id, exists):
    with open('rust_data.json', "w+") as rust_data:
        if exists:
                for user in local_data["users"]:
                    if user["discord_id"] == discord_user_id:
                        user["playerstats"] = steam_data["playerstats"]
                        rust_data.write(json.dumps(local_data, indent=4, sort_keys=True))
                        break
        else:
            local_data["users"].append({'discord_id': discord_user_id, 'playerstats': steam_data["playerstats"]})
            rust_data.write(json.dumps(local_data, indent=4, sort_keys=True))

                

async def add_new_user_to_rust_data_file(steam_id, discord_id):
    steam_data = get_user_steam_rust_data(steam_id)
    if steam_data == 500: return 500
    else:
        all_rust_user_data = await get_local_rust_data_object()
        exists = await does_user_exist_by_steam_id(all_rust_user_data['users'], steam_data['playerstats']['steamID'])
        if not exists:
            await update_rust_data_file(all_rust_user_data, steam_data, discord_id, exists)
            return steam_data
        else: return 500


async def delete_user_from_rust_data_file(steam_id):
    all_rust_user_data = await get_local_rust_data_object()
    exists = await does_user_exist_by_steam_id(all_rust_user_data['users'], steam_id)
    if exists:
        with open('rust_data.json', "w+") as rust_data:
            for i, user in enumerate(all_rust_user_data["users"]):
                if user['playerstats']['steamID'] == steam_id:
                    del all_rust_user_data["users"][i]
                    rust_data.write(json.dumps(all_rust_user_data, indent=4, sort_keys=True))
                    break



async def get_local_rust_data_object():
    with open('rust_data.json', "r") as rust_data:
        all_rust_user_data = json.load(rust_data)

    return all_rust_user_data

async def does_user_exist_by_steam_id(users, steam_id):
    for user in users:
        if user['playerstats']['steamID'] == steam_id:
            return True
    return False

async def does_user_exist_by_discord_id(users, discord_id):
    for user in users:
        if user['discord_id'] == discord_id:
            return True
    return False

async def get_user_with_discord_id(users, discord_id):
    for user in users:
        if user['discord_id'] == discord_id:
            return user

async def get_rust_data_for_user(data_attr, discord_id):
    local_users = await get_local_rust_data_object()
    exists = await does_user_exist_by_discord_id(local_users["users"], discord_id)
    if exists:
        user = await get_user_with_discord_id(local_users["users"], discord_id)
        for stat in user['playerstats']['stats']:
            if stat['name'] == data_attr:
                return stat['value']
        return "That attrabute does not exist."

async def get_rust_data_attribute(data_attr):
    rust_attrs = await get_all_rust_attributes()
    best_guess = process.extractOne(data_attr, rust_attrs)
    return best_guess[0]

async def get_all_rust_attributes():
    with open('rust_attributes.json','r') as f:
        rust_attrs = json.load(f)
    return rust_attrs


def create_rust_data_file_if_not_exist():
    if not path.exists("rust_data.json"):
        create_rust_data_file()

# *********************************************************************************
# DISCORD CLIENT CODE
# *********************************************************************************
class DiscordClient(discord.Client):
    async def on_ready(self):
        print('Logged on as', self.user)


    async def on_message(self, message):
        if message.author == self.user:
                return
        
        if message.content.startswith('!steamid '):
            steam_id = message.content[9: ]
            response = await add_new_user_to_rust_data_file(steam_id, message.author.id)
            if response == 500:
                await message.channel.send("Please make sure your profile is public and you typed your steam ID correctly.")
            else:
                await message.channel.send("You steam ID has been assoiciated with your discord profile.")

        if message.content.startswith('!delsteamid '):
            steam_id = message.content[12: ]
            response = await delete_user_from_rust_data_file(steam_id)

        if message.content.startswith('!rustdata '):
            data_attr = await get_rust_data_attribute(message.content[10: ])
            response = await get_rust_data_for_user(data_attr, message.author.id)
            await message.channel.send(f"{message.author.display_name} - {data_attr} : {response}")


async def my_background_task():
    await client.wait_until_ready()
    while True:
        members_playing_rust = get_members_playing_rust()
        if len(members_playing_rust) > 0:
            for member in members_playing_rust:
                await kill_watcher(member)
            await asyncio.sleep(len(members_playing_rust))
        else:
            print("No one is playing Rust. Waiting a minute to check again.")
            await asyncio.sleep(60)


async def kill_watcher(discord_member):
    channel = client.get_channel(config["discord"]["channel_id"])
    local_rust_data = get_local_rust_data()
    for member_local_rust_data in local_rust_data["users"]:
        if discord_member.id == member_local_rust_data["discord_id"]:
            new_rust_kills = await check_rust_kills(member_local_rust_data)
            if new_rust_kills > 0:
                await channel.send(f"{discord_member.display_name} recently killed {new_rust_kills} persons!")
                break

       

def get_members_playing_rust():
    members_playing_rust_array = []
    for member in client.get_all_members():
        if len(member.activities) > 0:
            for activity in member.activities:
                if hasattr(activity, "application_id"): 
                    if activity.application_id == config["discord"]["game_id"]: 
                        members_playing_rust_array.append(member)
                        break
    return members_playing_rust_array



create_rust_data_file_if_not_exist()
client = DiscordClient()
client.loop.create_task(my_background_task())
client.run(config["discord"]["bot_token"])
