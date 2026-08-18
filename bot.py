import discord
from discord.ext import commands, tasks
import json
import os


# ==================================================
# CẤU HÌNH
# ==================================================

TOKEN = os.getenv("TOKEN")
PREFIX = "?"

# Kênh gửi thông báo cộng điểm
POINT_CHANNEL_ID = int(
    os.getenv("POINT_CHANNEL_ID", "0")
)

DATA_FILE = "pair_points.json"


# ==================================================
# ROLE ĐƯỢC PHÉP TÍNH
# ==================================================
# Thay bằng Role ID thật của bạn

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


pair_points = load_points()


def save_points():

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            pair_points,
            f,
            ensure_ascii=False,
            indent=4
        )


# ==================================================
# LẤY ROLE ĐƯỢC CHỈ ĐỊNH
# ==================================================

def get_allowed_roles(member):

    return tuple(sorted(
        role.id
        for role in member.roles
        if role.id in ALLOWED_ROLE_IDS
    ))


# ==================================================
# ROLE PHẢI GIỐNG HỆT
# ==================================================

def same_roles(member1, member2):

    roles1 = get_allowed_roles(member1)
    roles2 = get_allowed_roles(member2)

    # Không có role được phép
    if not roles1 or not roles2:
        return False

    # Phải giống 100%
    return roles1 == roles2


# ==================================================
# TẠO ID CẶP
# ==================================================

def get_pair_id(member1, member2):

    ids = sorted([
        member1.id,
        member2.id
    ])

    return f"{ids[0]}_{ids[1]}"


# ==================================================
# LẤY TÊN ROLE
# ==================================================

def get_role_names(member):

    roles = []

    for role in member.roles:

        if role.id in ALLOWED_ROLE_IDS:

            roles.append(role.name)

    return roles


# ==================================================
# CỘNG ĐIỂM CHO CẶP
# ==================================================

async def add_pair_point(
    member1,
    member2,
    amount=1,
    reason=""
):

    # Kiểm tra role
    if not same_roles(
        member1,
        member2
    ):
        return

    guild_id = str(
        member1.guild.id
    )

    pair_id = get_pair_id(
        member1,
        member2
    )

    if guild_id not in pair_points:

        pair_points[guild_id] = {}

    if pair_id not in pair_points[guild_id]:

        pair_points[guild_id][pair_id] = {
            "user1": min(
                member1.id,
                member2.id
            ),
            "user2": max(
                member1.id,
                member2.id
            ),
            "points": 0,
            "roles": list(
                get_allowed_roles(member1)
            )
        }

    pair_points[guild_id][pair_id][
        "points"
    ] += amount

    save_points()

    total = pair_points[
        guild_id
    ][
        pair_id
    ][
        "points"
    ]

    # ==================================================
    # THÔNG BÁO
    # ==================================================

    if POINT_CHANNEL_ID == 0:
        return

    channel = member1.guild.get_channel(
        POINT_CHANNEL_ID
    )

    if channel is None:
        return

    role_names = get_role_names(
        member1
    )

    role_text = ", ".join(
        role_names
    )

    message = (
        f"🎉 **Điểm cặp tăng +{amount}**\n"
        f"👥 {member1.display_name} "
        f"❤️ {member2.display_name}\n"
        f"🎭 Role: `{role_text}`\n"
        f"🏆 Điểm chung: **{total}**\n"
        f"📌 {reason}"
    )

    try:

        await channel.send(message)

    except discord.Forbidden:

        print(
            "❌ Bot không có quyền "
            "gửi tin nhắn."
        )

    except Exception as e:

        print(
            f"❌ Lỗi gửi thông báo: {e}"
        )


# ==================================================
# CỘNG ĐIỂM CÙNG ROOM
# ==================================================

@tasks.loop(minutes=1)
async def room_points():

    for guild in bot.guilds:

        rooms = {}

        # ------------------------------------------
        # Tìm người trong voice
        # ------------------------------------------

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

            rooms[channel_id].append(
                member
            )

        # ------------------------------------------
        # Kiểm tra từng room
        # ------------------------------------------

        for room_members in rooms.values():

            if len(room_members) < 2:
                continue

            # --------------------------------------
            # Từng cặp người
            # --------------------------------------

            for i in range(
                len(room_members)
            ):

                for j in range(
                    i + 1,
                    len(room_members)
                ):

                    member1 = room_members[i]
                    member2 = room_members[j]

                    # Role giống hệt
                    if same_roles(
                        member1,
                        member2
                    ):

                        await add_pair_point(
                            member1,
                            member2,
                            1,
                            "Cùng Voice Room."
                        )


# ==================================================
# TAG NHAU
# ==================================================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.guild is None:

        await bot.process_commands(
            message
        )

        return

    author = message.author

    checked_users = set()

    # ------------------------------------------
    # Có người được tag
    # ------------------------------------------

    for target in message.mentions:

        if target.bot:
            continue

        if target.id in checked_users:
            continue

        checked_users.add(
            target.id
        )

        # Role phải giống hệt
        if same_roles(
            author,
            target
        ):

            await add_pair_point(
                author,
                target,
                1,
                f"{author.display_name} "
                f"tag {target.display_name}."
            )

    await bot.process_commands(
        message
    )


# ==================================================
# ?DIEM @NGUOI
# ==================================================

@bot.command()
async def diem(
    ctx,
    member: discord.Member = None
):

    if member is None:

        await ctx.send(
            "❌ Dùng: `?diem @người`"
        )

        return

    # Role không giống
    if not same_roles(
        ctx.author,
        member
    ):

        await ctx.send(
            "❌ Hai người không có "
            "bộ role giống nhau."
        )

        return

    guild_id = str(
        ctx.guild.id
    )

    pair_id = get_pair_id(
        ctx.author,
        member
    )

    data = pair_points.get(
        guild_id,
        {}
    )

    if pair_id not in data:

        score = 0

    else:

        score = data[
            pair_id
        ]["points"]

    await ctx.send(
        f"👥 **{ctx.author.display_name}** "
        f"❤️ **{member.display_name}**\n"
        f"🏆 Điểm chung: **{score}**"
    )


# ==================================================
# ?TOP
# ==================================================

@bot.command()
async def top(ctx):

    guild_id = str(
        ctx.guild.id
    )

    data = pair_points.get(
        guild_id,
        {}
    )

    if not data:

        await ctx.send(
            "📊 Chưa có cặp nào có điểm."
        )

        return

    ranking = sorted(
        data.items(),
        key=lambda x: x[1]["points"],
        reverse=True
    )[:10]

    text = "🏆 **TOP CẶP ĐIỂM**\n\n"

    for index, (
        pair_id,
        pair
    ) in enumerate(
        ranking,
        1
    ):

        member1 = ctx.guild.get_member(
            pair["user1"]
)
