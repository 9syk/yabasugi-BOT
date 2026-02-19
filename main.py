import os
import discord
import pytz
from datetime import datetime, time
from discord import app_commands
from discord.ext import tasks
from sqlalchemy import select, desc
from dotenv import load_dotenv
import re, random, uuid

from db import engine, AsyncSessionLocal
from models import Base, MessageCount, TotalCount, GuildSettings

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN is not set")

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

#起動時
@client.event
async def on_ready():
    await init_db()
    await tree.sync()
    if not monthly_check.is_running():
        monthly_check.start()

#メッセージを受信
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if not message.guild:
        return
    guild_id = message.guild.id
    author_id = message.author.id
    content = message.content
    if content == "おお":
        await message.channel.send("おおじゃないが")
    if content == "おおじゃないが":
        await message.channel.send("これはおおだろ")
    KEYWORDS = ["うお","うぉ","どわー","🐟","けけっ","ひひっ","おう","効いてて草","きちー","😅"]
    if any(keyword in content for keyword in KEYWORDS):
        monthly, total = await increment_count(
            author_id,
            guild_id
        )
        await message.channel.send(
            f"どわーW {message.author.mention} さん！今月 {monthly} 回目の冷笑です！(累計 {total} 回)"
        )
    dice_pattern = r'([\d０-９]+)\s*[dDｄＤ]\s*([\d０-９]+)'
    dice_match = re.search(dice_pattern, content)
    if dice_match:
        dice_count = int(dice_match.group(1))
        dice_sides = int(dice_match.group(2))
        if dice_count > 256:
            await message.reply("ダイスの数が多すぎます！(最大256)")
            return
        if dice_sides > 65536:
            await message.reply("ダイスの面が多すぎます！(最大65536)")
            return
        dice_rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
        dice_total = sum(dice_rolls)
        await message.reply(f"🎲 **合計: {dice_total}** (出目: {dice_rolls})")

#スラッシュコマンド
@tree.command(name="uuid",description="UUIDを生成")
async def generate_uuid(interaction: discord.Interaction):
    uid = uuid.uuid4()
    await interaction.response.send_message(
        f"{uid}\n{uid.hex}"
    )

@tree.command(name="set_ranking_channel", description="ランキング投稿チャンネルを設定")
@app_commands.checks.has_permissions(administrator=True)
async def set_ranking_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.guild is None:
        await interaction.response.send_message(
            "サーバー内でのみ使用できます",
            ephemeral=True
        )
        return
    guild_id = interaction.guild.id
    async with AsyncSessionLocal() as session:
        setting = await session.get(GuildSettings, guild_id)
        if setting:
            setting.ranking_channel_id = channel.id
        else:
            session.add(GuildSettings(
                guild_id=guild_id,
                ranking_channel_id=channel.id
            ))
        await session.commit()
    await interaction.response.send_message(
        f"{channel.mention} をランキング投稿チャンネルに設定しました。",
        ephemeral=True
    )

@tree.command(name="ranking", description="今月のランキングを表示")
async def ranking(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "サーバー内で使用してください。",
            ephemeral=True
        )
        return
    await interaction.response.defer()
    now = datetime.now(pytz.timezone("Asia/Tokyo"))
    year = now.year
    month = now.month
    guild_id = interaction.guild.id
    async with AsyncSessionLocal() as session:
        stmt = (
            select(MessageCount)
            .where(
                MessageCount.guild_id == guild_id,
                MessageCount.year == year,
                MessageCount.month == month
            )
            .order_by(desc(MessageCount.count))
        )
        results = (await session.execute(stmt)).scalars().all()
        if not results:
            await interaction.followup.send("今月はまだ冷笑がありません。")
            return
        embed = discord.Embed(
            title=f"{year}年{month}月 冷笑ランキング",
            color=discord.Color.blue()
        )
        last_count = None
        rank_position = 0
        user_rank = None
        user_monthly_count = 0
        for index, row in enumerate(results, start=1):
            # 同率順位処理
            if row.count != last_count:
                rank_position = index
                last_count = row.count
            # 自分の順位記録
            if row.user_id == interaction.user.id:
                user_rank = rank_position
                user_monthly_count = row.count
            # 上位10位までembedに追加
            if rank_position <= 10:
                total = await session.get(
                    TotalCount,
                    (row.user_id, row.guild_id)
                )
                embed.add_field(
                    name=f"{rank_position}位",
                    value=f"<@{row.user_id}> 今月 {row.count}回 / 累計 {total.count if total else 0}回",
                    inline=False
                )
        # 自分が圏外だった場合も表示
        if user_rank is not None and user_rank > 10:
            total = await session.get(
                TotalCount,
                (interaction.user.id, guild_id)
            )
            embed.add_field(
                name="あなたの順位",
                value=f"{user_rank}位 今月 {user_monthly_count}回 / 累計 {total.count if total else 0}回",
                inline=False
            )
        elif user_rank is None:
            embed.add_field(
                name="あなたの順位",
                value="今月はまだ冷笑がありません。",
                inline=False
            )
        await interaction.followup.send(embed=embed)

#冷笑カウント
async def increment_count(user_id: int, guild_id: int):
    now = datetime.now(pytz.timezone("Asia/Tokyo"))
    year = now.year
    month = now.month
    async with AsyncSessionLocal() as session:
        monthly = await session.get(
            MessageCount,
            (user_id, guild_id, year, month)
        )
        if monthly:
            monthly.count += 1
            monthly_count = monthly.count
        else:
            monthly = MessageCount(
                user_id=user_id,
                guild_id=guild_id,
                year=year,
                month=month,
                count=1
            )
            session.add(monthly)
            monthly_count = 1
        total = await session.get(
            TotalCount,
            (user_id, guild_id)
        )
        if total:
            total.count += 1
            total_count = total.count
        else:
            total = TotalCount(
                user_id=user_id,
                guild_id=guild_id,
                count=1
            )
            session.add(total)
            total_count = 1
        await session.commit()
        return monthly_count, total_count

# 月間ランキング（毎月1日 0:00 JST に1回だけ実行）
@tasks.loop(time=time(hour=0, minute=0, tzinfo=pytz.timezone("Asia/Tokyo")))
async def monthly_check():
    now = datetime.now(pytz.timezone("Asia/Tokyo"))
    # 前月を取得
    year = now.year
    month = now.month - 1
    if month == 0:
        month = 12
        year -= 1
    async with AsyncSessionLocal() as session:
        stmt = select(GuildSettings)
        guilds = (await session.execute(stmt)).scalars().all()
        for setting in guilds:
            stmt = (
                select(MessageCount)
                .where(
                    MessageCount.guild_id == setting.guild_id,
                    MessageCount.year == year,
                    MessageCount.month == month
                )
                .order_by(desc(MessageCount.count))
                .limit(10)
            )
            ranking = (await session.execute(stmt)).scalars().all()
            if not ranking:
                continue
            channel = client.get_channel(setting.ranking_channel_id)
            if not isinstance(channel, discord.TextChannel):
                continue
            embed = discord.Embed(
                title=f"{year}年{month}月 冷笑ランキング",
                color=discord.Color.gold()
            )
            last_count = None
            rank_position = 0
            for index, row in enumerate(ranking, start=1):
                # 同率順位対応
                if row.count != last_count:
                    rank_position = index
                    last_count = row.count
                total = await session.get(
                    TotalCount,
                    (row.user_id, row.guild_id)
                )
                embed.add_field(
                    name=f"{rank_position}位",
                    value=f"<@{row.user_id}> {row.count}回 (累計 {total.count if total else 0}回)",
                    inline=False
                )
            await channel.send(embed=embed)


client.run(TOKEN)