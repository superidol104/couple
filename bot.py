import discord
from discord.ext import commands, tasks
import json
import os

# =========================
# CẤU HÌNH
# =========================

TOKEN = os.getenv("TOKEN")
PREFIX = "?"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents
)

DATA_FILE = "points.json"


# =========================
# DATABASE
# =========================

def load_points():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


points = load_points()


def save_points():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            points,
            f,
            ensure_ascii=False,
            indent=4
        )


# =========================
# LẤY ROLE
# =========================

def get_roles(member):

    """
    Lấy toàn bộ role của member.

    Bỏ:
    - @everyone
    - role có tên Admin

    Các role còn lại phải giống HỆT NHAU.
    """

    return tuple(sorted(
        role.id
        for role in member.roles
        if role != member.guild.default_role
        and role.name.lower() != "Owner","Manager","Admin","Supporter","Staff","Princes Eleutheromania","Server Booster","Singer Eleutheromania","Bạc xỉu","na đại ca","Na Vĩ Đại","Angel","trẻ em","pao.nhyi_","Thành viên","Play Together","Liên Quân Mobile","Valorant","Free Fire","Liên minh","Roblox","Pubg","TFT","Steam","Người giữ group","Hoang tu mua dong","MIỀN BẮC","MIỀN TRUNG","MIỀN NAM","18 tuổi trở xuống","Hoang tu nam ki","Trai xinh","Gái đẹp","18 tuổi trở lên","
    ))


def same_roles(member1, member2):

    return get_roles(member1) == get_roles(member2)


# =========================
# CỘNG ĐIỂM
# =========================

def add_point(member, amount=1):

    guild_id = str(member.guild.id)
    user_id = str(member.id)

    if guild_id not in points:
        points[guild_id] = {}

    if user_id not in points[guild_id]:
        points[guild_id][user_id] = 0

    points[guild_id][user_id] += amount

    save_points()


# =========================
# CỘNG ĐIỂM KHI CÙNG ROOM
# =========================

@tasks.loop(minutes=1)
async def room_points():

    for guild in bot.guilds:

        rooms = {}

        # Lấy người đang ở voice
        for member in guild.members:

            if member.bot:
                continue

            if member.voice is None:
                continue

            if member.voice.channel is None:
                continue

            channel_id = member.voice.channel.id

            if channel_id not in rooms:
                rooms[channel_id] = []

            rooms[channel_id].append(member)

        # Kiểm tra từng room
        for room_members in rooms.values():

            if len(room_members) < 2:
                continue

            # Kiểm tra từng cặp
            for i in range(len(room_members)):

                for j in range(i + 1, len(room_members)):

                    member1 = room_members[i]
                    member2 = room_members[j]

                    # ROLE PHẢI GIỐNG HỆT
                    if same_roles(member1, member2):

                        add_point(member1, 1)
                        add_point(member2, 1)


# =========================
# TAG NHAU
# =========================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Có người được tag
    if message.mentions:

        author = message.author

        for target in message.mentions:

            if target.bot:
                continue

            # Phải cùng server
            if target.guild.id != message.guild.id:
                continue

            # ROLE PHẢI GIỐNG HỆT
            if same_roles(author, target):

                # Người tag được +1
                add_point(author, 1)

    await bot.process_commands(message)


# =========================
# LỆNH XEM ĐIỂM
# =========================

@bot.command()
async def diem(
    ctx,
    member: discord.Member = None
):

    if member is None:
        member = ctx.author

    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    score = points.get(
        guild_id,
        {}
    ).get(
        user_id,
        0
    )

    await ctx.send(
        f"🏆 **{member.display_name}** "
        f"hiện có **{score} điểm**."
    )


# =========================
# TOP ĐIỂM
# =========================

@bot.command()
async def top(ctx):

    guild_id = str(ctx.guild.id)

    data = points.get(
        guild_id,
        {}
    )

    if not data:

        await ctx.send(
            "📊 Chưa có ai có điểm."
        )

        return

    ranking = sorted(
        data.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    text = "🏆 **TOP ĐIỂM**\n\n"

    for index, (user_id, score) in enumerate(
        ranking,
        1
    ):

        member = ctx.guild.get_member(
            int(user_id)
        )

        if member:
            name = member.display_name
        else:
            name = f"User {user_id}"

        text += (
            f"**{index}.** "
            f"{name} — `{score} điểm`\n"
        )

    await ctx.send(text)


# =========================
# BOT ONLINE
# =========================

@bot.event
async def on_ready():

    print(
        f"✅ Bot online: {bot.user}"
    )

    if not room_points.is_running():

        room_points.start()


# =========================
# CHẠY BOT
# =========================

if not TOKEN:

    raise ValueError(
        "❌ Chưa có TOKEN trong Railway Variables!"
    )

bot.run(TOKEN)
