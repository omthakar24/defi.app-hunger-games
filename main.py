import discord
import random
import asyncio
from discord.ext import commands

# Set up intents for the bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Player class to hold player information
class Player:
    def __init__(self, member, hp=100, alive=True):
        self.member = member
        self.hp = hp
        self.alive = alive

# Global variables to manage game state
players = []
round_number = 1
game_running = False
join_message = None

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    await bot.tree.sync()
    print("Commands synced.")

@bot.tree.command(name="hunger", description="Start the Hunger Games")
async def hunger(interaction: discord.Interaction, start_time: int):
    global game_running, join_message

    if game_running:
        await interaction.response.send_message("A game is already running!", ephemeral=True)
        return

    # Reset players for a new game
    global players, round_number
    players = []
    round_number = 1
    game_running = True

    # Send start and join messages
    start_embed = discord.Embed(
        title="The Hunger Games",
        description=f"The Hunger Games will begin soon! You have {start_time} minute(s) to join by reacting with :pepesword:.",
        color=0x00FF00)
    await interaction.response.send_message(embed=start_embed)

    join_embed = discord.Embed(
        title="Join the Game",
        description="React with :pepesword: to join the Hunger Games!",
        color=0x7289DA)
    join_message = await interaction.followup.send(embed=join_embed)

    # Add the custom emoji as a reaction
    pepesword_emoji = discord.utils.get(interaction.guild.emojis, name="pepesword")
    await join_message.add_reaction(pepesword_emoji)

    # Include the command initiator as a player
    players.append(Player(member=interaction.user))

    # Wait for players to join
    await wait_for_players(interaction, start_time * 60)

async def wait_for_players(interaction: discord.Interaction, timeout):
    global players, join_message

    # Check for valid reactions with the custom emoji
    def check(reaction, user):
        return user != bot.user and reaction.emoji.name == "pepesword" and reaction.message.id == join_message.id

    try:
        while True:
            reaction, user = await bot.wait_for('reaction_add', timeout=timeout, check=check)
            if user not in [p.member for p in players]:
                players.append(Player(member=user))
    except asyncio.TimeoutError:
        timeout_embed = discord.Embed(
            title="⏳ Time to Join Expired",
            description="The time to join has expired! The game will start shortly.",
            color=0xFF0000)
        await interaction.channel.send(embed=timeout_embed)

    # Simulate 50 players for testing
    simulate_players(50)

    # Start game countdown and rounds after join wait
    await asyncio.sleep(2)
    await start_round(interaction)

def simulate_players(num_players):
    global players
    while len(players) < num_players:
        fake_member = f"Player{len(players) + 1}"
        players.append(Player(member=fake_member))

async def start_round(interaction):
    global round_number
    alive_players = [p for p in players if p.alive]

    if len(alive_players) == 1:
        winner = alive_players[0]
        winner_name = winner.member.mention if isinstance(winner.member, discord.Member) else f"Simulated User {winner.member}"
        winner_embed = discord.Embed(
            description=f"🎉 **The winner is {winner_name}!** 🎉",
            color=0xFFD700,
        )
        await interaction.channel.send(embed=winner_embed)
        global game_running
        game_running = False
        return

    # Display the final stage message if 20 or fewer players are alive
    if len(alive_players) <= 20:
        final_stage_embed = discord.Embed(
            title="Final Stage Incoming - Direct eliminations only",
            color=0xFFFF00)
        await interaction.channel.send(embed=final_stage_embed)
        await direct_elimination(interaction, alive_players)
    else:
        round_events = await generate_events(interaction)
        round_embed = discord.Embed(title=f"**Round {round_number}**", description="Events and Player Status", color=0x7289DA)

        for event in round_events:
            round_embed.add_field(name="\u200b", value=event, inline=False)

        round_embed.add_field(name="Players Left", value=f"{len(alive_players)}", inline=False)
        await interaction.channel.send(embed=round_embed)

        round_number += 1
        await asyncio.sleep(get_wait_time(len(alive_players)))

        if len(alive_players) > 1:
            await start_round(interaction)

async def direct_elimination(interaction, alive_players):
    elimination_messages = [
        "**{}** devoured ~~**{}**~~!",
        "**{}** hunted down ~~**{}**~~!",
        "**{}** eliminated ~~**{}**~~!",
        "**{}** ambushed ~~**{}**~~!",
        "**{}** struck down ~~**{}**~~!"
    ]
    
    while len(alive_players) > 1:
        event_text = []
        for _ in range(5 if len(alive_players) > 5 else len(alive_players) - 1):
            attacker = random.choice(alive_players)
            victim = random.choice([p for p in alive_players if p != attacker])
            elimination_text = random.choice(elimination_messages).format(
                attacker.member.display_name if isinstance(attacker.member, discord.Member) else attacker.member,
                victim.member.display_name if isinstance(victim.member, discord.Member) else victim.member
            )
            victim.alive = False
            alive_players.remove(victim)
            event_text.append(elimination_text)
            if len(alive_players) == 1:
                break

        elimination_embed = discord.Embed(
            description="\n".join(event_text),
            color=0xFF4500
        )
        await interaction.channel.send(embed=elimination_embed)

        if len(alive_players) == 1:
            winner = alive_players[0]
            winner_embed = discord.Embed(
                description=f"🎉 **The winner is {winner.member.mention if isinstance(winner.member, discord.Member) else winner.member}!** 🎉",
                color=0xFFD700,
            )
            await interaction.channel.send(embed=winner_embed)
            global game_running
            game_running = False
            return

async def generate_events(interaction):
    events = []
    alive_players = [p for p in players if p.alive]
    dead_players = [p for p in players if not p.alive]

    if not alive_players:
        return events

    # Define custom events for attacks, healing, and revival
    attack_events = [
        "Liberta detected some unusual activities on ~~{}~~ and banned them from the game.",
        "Liberta flamed ~~{}~~ using Phoenix fire.",
        "~~{}~~ refused to join the Cattos Army so MGD stabbed them <a:catstab:1305261170059509833>",
        "~~{}~~ tried to hurt Cryptokitty, MGD buried them alive.",
        "Himelia caught ~~{}~~ in their Pokeball, there was no way out.",
        "~~{}~~ tried to go against Queen Himmy - didn’t end up well for them.",
        "Himelia's Dragons were hungry so they ate ~~{}~~<a:HimmyDragon:1305464932384510024>",
        "Kavvss burned ~~{}~~ with blast burn attack.",
        "~~{}~~ was creeped out by Creeptic, so they left the game.",
        "Cryptic ate ~~{}~~.",
        "Doran manipulated ~~{}~~ to leave the game by giving them :Dappies: 1000 dappies.",
        "IX23 finished ~~{}~~ with their BatMobile :bat:.",
        "Baconcheese bullied ~~{}~~ so they left the game.",
    ]

    heal_events = [
        "{} joined Cattos Army so MGD gave them 20 HP.",
        "Pootie cutie gave 20 HP to {} because he's the best.",
        "Oregano gave {} 20 HP because they bullied Cryptic with them <:kekyou:1305260901976506449>",
    ]

    revival_events = [
        "<:revive:1305468568128720947> | Doran daddy revived {}.",
        "Poot kissed {} which brought them back to life <a:catkiss:1305428032802263161>",
        "<:revive:1305468568128720947> | MGD revived {} because they loved cats :catlove:."
    ]

    # Generate events
    for _ in range(5):
        event_type = random.choices(
            ["attack", "heal", "revival"],
            weights=[0.6, 0.3, 0.1],
            k=1
        )[0]

        if event_type == "heal" and alive_players:
            target = random.choice(alive_players)
            event_text = random.choice(heal_events).format(
                target.member.name if isinstance(target.member, discord.Member) else target.member
            )
            target.hp += 20
            events.append(event_text)

        elif event_type == "revival" and dead_players:
            revived = random.choice(dead_players)
            revived.alive = True
            revived.hp = 100
            event_text = random.choice(revival_events).format(
                revived.member.name if isinstance(revived.member, discord.Member) else revived.member
            )
            events.append(event_text)
            dead_players.remove(revived)
            alive_players.append(revived)

        elif event_type == "attack" and alive_players:
            attacker = random.choice(alive_players)
            target = random.choice([p for p in alive_players if p != attacker])

            # Determine if a direct elimination event occurs
            if random.random() < 0.5:
                elimination_text = random.choice(attack_events).format(
                    target.member.name if isinstance(target.member, discord.Member) else target.member
                )
                target.alive = False
                alive_players.remove(target)
            else:
                # HP Reduction between 20 and 60
                hp_loss = random.randint(20, 60)  # Random HP loss between 20 and 60
                target.hp -= hp_loss

                # Create a human-like attack message with varied text
                elimination_text = random.choice([
                    f"{attacker.member.name if isinstance(attacker.member, discord.Member) else attacker.member} punched {target.member.name if isinstance(target.member, discord.Member) else target.member}, causing a **minor wound** - lost {hp_loss} HP!",
                    f"{attacker.member.name if isinstance(attacker.member, discord.Member) else attacker.member} hit {target.member.name if isinstance(target.member, discord.Member) else target.member} with a **swift blow** - lost {hp_loss} HP!",
                    f"{attacker.member.name if isinstance(attacker.member, discord.Member) else attacker.member} unleashed a **devastating strike** on {target.member.name if isinstance(target.member, discord.Member) else target.member} - lost {hp_loss} HP!",
                    f"{attacker.member.name if isinstance(attacker.member, discord.Member) else attacker.member} attacked {target.member.name if isinstance(target.member, discord.Member) else target.member} with all their might - lost {hp_loss} HP!",
                    f"{attacker.member.name if isinstance(attacker.member, discord.Member) else attacker.member} landed a crushing blow on {target.member.name if isinstance(target.member, discord.Member) else target.member}, causing a **severe injury** - lost {hp_loss} HP!",
                    f"{attacker.member.name if isinstance(attacker.member, discord.Member) else attacker.member} ambushed {target.member.name if isinstance(target.member, discord.Member) else target.member} with a surprise attack - lost {hp_loss} HP!"
                ])

                if target.hp <= 0:
                    target.alive = False
                    alive_players.remove(target)

            events.append(elimination_text)

    return events



def get_wait_time(alive_count):
    if alive_count >= 40:
        return 3
    elif alive_count >= 20:
        return 2
    else:
        return 1

bot.run('Token later')
