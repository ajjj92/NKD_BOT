#attejantunen

import discord



client = discord.Client()
prefix = '!'


@client.event
async def on_ready():
    print('logged in as {0.user}'.format(client))

@client.event
async def on_message(message):

    id = client.get_guild(568510509310279720)

    if message.author == client.user:
        return

    if message.content.startswith('{}hello'.format(prefix)):
        await message.channel.send('{0.user} says: Hello!'.format(client))
   
    if message.content == '{}users'.format(prefix):
        
        await message.channel.send(id.member_count)

@client.event
async def on_member_join(member):
    for channel in member.server.channels:
        if str(channel) == "lobby": # We check to make sure we are sending the message in the general channel
            await client.send_message(f"""Welcome to the NKD server {member.mention}""")

    

client.run('NTc1NzIzOTgzMzkyMjEwOTUy.XNMH3A.BOzTVp3EyxU71GAlP4fRysv9YEc')