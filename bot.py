import discord
from discord.ext import commands, tasks
import json
import os


# ==================================================
# CẤU HÌNH
# ==================================================

TOKEN = os.getenv("TOKEN")
PREFIX = "?"

# ID kênh thông báo cộng điểm
POINT_CHANNEL_ID = int(
    os.getenv("POINT_CHANNEL_ID", "0")
)

DATA_FILE = "points.json"


# ==================================================
# ROLE ĐƯỢC PHÉP TÍNH ĐIỂM
# ==================================================
#
# CHỈ những role có ID ở đây mới được xét.
#
# Ví dụ:
#
# Gamer = 123456789
# Player = 987654321
#
# ==================================================

ALLOWED_ROLE_IDS = {
    1538841659708547082,  # Couple
}


# ==================================================
# INTENTS
# ==================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents
)


# ==================================================
# DATABASE
# ==================================================

def load_points():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


points = load_points()


def save_points():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            points,
            f,
            ensure_ascii=False,
            indent=4
        )


# ==================================================
# LẤY TOÀN BỘ ROLE ĐƯỢC CHỈ ĐỊNH
# ==================================================

def get_allowed_roles(member):

    """
    Chỉ lấy role nằm trong ALLOWED_ROLE_IDS.

    Ví dụ:

    Member A:
    Gamer
    Player

    -> (Gamer ID, Player ID)

    Member B:
    Gamer

    -> (Gamer ID)

    Hai bộ khác nhau -> không cộng.
    """

    roles = [
        role.id
        for role in member.roles
        if role.id in ALLOWED_ROLE_IDS
    ]

    return tuple(sorted(roles))


# ==================================================
# KIỂM TRA ROLE CÓ GIỐNG 100% KHÔNG
# ==================================================

def same_roles(member1, member2):

    roles1 = get_allowed_roles(member1)
    roles2 = get_allowed_roles(member2)

    # Không có role được chỉ định
    if not roles1:
        return False

    if not roles2:
        return False

    # PHẢI GIỐNG HOÀN TOÀN
    return roles1 == roles2


# ==================================================
# CỘNG ĐIỂM
# ==================================================

async def add_point(
    member,
    amount=1,
    reason=""
):

    guild_id = str(member.guild.id)
    user_id = str(member.id)

    if guild_id not in points:

        points[guild_id] = {}

    if user_id not in points[guild_id]:

        points[guild_id][user_id] = 0

    points[guild_id][user_id] += amount

    save_points()

    # ==================================================
    # THÔNG BÁO
    # ==================================================

    if POINT_CHANNEL_ID == 0:
        return

    channel = member.guild.get_channel(
        POINT_CHANNEL_ID
    )

    if channel is None:
        return

    total = points[guild_id][user_id]

    message = (
        f"🎉 **{member.display_name}** +{amount} điểm!\n"
        f"🏆 Tổng điểm: **{total}**\n"
        f"📌 {reason}"
    )

    try:

        await channel.send(message)

    except discord.Forbidden:

        print(
            "❌ Bot không có quyền gửi "
            "tin nhắn ở kênh thông báo."
        )

    except Exception as e:

        print(
            f"❌ Lỗi gửi thông báo: {e}"
        )


# ==================================================
# CỘNG ĐIỂM KHI CÙNG VOICE ROOM
# ==================================================

@tasks.loop(minutes=1)
async def room_points():

    for guild in bot.guilds:

        rooms = {}

        # ==================================================
        # TÌM NGƯỜI ĐANG Ở VOICE
        # ==================================================

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

        # ==================================================
        # KIỂM TRA TỪNG ROOM
        # ==================================================

        for room_members in rooms.values():

            if len(room_members) < 2:
                continue

            # ==================================================
            # KIỂM TRA TỪNG CẶP NGƯỜI
            # ==================================================

            for i in range(
                len(room_members)
            ):

                for j in range(
                    i + 1,
                    len(room_members)
                ):

                    member1 = room_members[i]
                    member2 = room_members[j]

                    # ROLE GIỐNG 100%
                    if same_roles(
                        member1,
                        member2
                    ):

                        await add_point(
                            member1,
                            1,
                            "Cùng Voice Room "
                            "với người có cùng bộ role."
                        )

                        await add_point(
                            member2,
                            1,
                            "Cùng Voice Room "
                            "với người có cùng bộ role."
                        )


# ==================================================
# TAG NHAU
# ==================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    # Tin nhắn ngoài server
    if message.guild is None:

        await bot.process_commands(
            message
        )

        return

    # ==================================================
    # CÓ TAG
    # ==================================================

    if message.mentions:

        author = message.author

        # Không cộng nhiều lần nếu
        # tag cùng một người nhiều lần
        checked_users = set()

        for target in message.mentions:

            if target.bot:
                continue

            if target.id in checked_users:
                continue

            checked_users.add(
                target.id
            )

            # ==================================================
            # ROLE PHẢI GIỐNG 100%
            # ==================================================

            if same_roles(
                author,
                target
            ):

                await add_point(
                    author,
                    1,
                    f"Tag **{target.display_name}**."
                )

    await bot.process_commands(
        message
    )


# ==================================================
# ?DIEM
# ==================================================

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


# ==================================================
# ?TOP
# ==================================================

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


# ==================================================
# BOT ONLINE
# ==================================================

@bot.event
async def on_ready():

    print(
        f"✅ Bot online: {bot.user}"
    )

    print(
        "🎭 Đang kiểm tra role bằng Role ID."
    )

    if not room_points.is_running():

        room_points.start()


# ==================================================
# KIỂM TRA TOKEN
# ==================================================

if not TOKEN:

    raise ValueError(
        "❌ Chưa thêm TOKEN vào Railway Variables!"
    )


# ==================================================
# CHẠY BOT
# ==================================================

bot.run(TOKEN)
