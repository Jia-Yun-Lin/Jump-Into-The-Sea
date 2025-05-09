# -*- coding: utf-8 -*-

# 導入Discord.py模組
import discord
from discord import app_commands
import random
import csv
import logging
from fastapi import FastAPI
import uvicorn
import asyncio
import os

#%%

# --- 載入環境變數 (Render 上會設)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# --- 設定 LOG ---
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
console_handler = logging.StreamHandler()
logging.basicConfig(handlers=[handler, console_handler], level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')

# --- 讀取 CSV ---
def load_messages_from_csv(file_path):
    messages = []
    with open(file_path, mode='r', encoding='big5') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            messages.append({
                "title": row["title"],
                "message": row["message"],
                "final": row["final"]
            })
    return messages

csv_file_path = "./message.csv"
string_list = load_messages_from_csv(csv_file_path)

# --- Discord Bot 初始化 ---
channel_id = 1370303370392371255
message_id = 0

# client是跟discord連接，intents是要求機器人的權限
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents = intents)

#%% --- Functions ---

def get_sea_string():
    random.shuffle(string_list)  # 隨機打亂字串陣列
    return string_list[0] # 回傳第一個字串

#%% --- UI Button Classes ---

class SeaButtonHandler(discord.ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):

        message = get_sea_string()

        embed=discord.Embed(title=message["title"], description="➤ "+message["message"], color=0x007bff)
        embed.set_author(name="海港事件")
        embed.add_field(name="事件結果", value="• "+message["final"], inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # print("Button clicked!")

class JobButtonHandler(discord.ui.Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        new_view = discord.ui.View(timeout=30)
        new_view.add_item(SeaButtonHandler(label="海港", style=discord.ButtonStyle.success))
        await interaction.response.send_message("> 去跳海吧", view=new_view, ephemeral=True)

class MyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)  # timeout in seconds
        self.add_item(JobButtonHandler(label="工作", style=discord.ButtonStyle.primary))

    async def on_timeout(self):
        channel = client.get_channel(channel_id)
        if channel:
            print("View 已超時，重新生成按鈕。")
            await edit_resend_view()

#%% --- Discord 事件 ---

# 調用event函式庫
@client.event
# 當機器人完成啟動
async def on_ready():
    print(f"目前登入身份 --> {client.user}")
    
    channel = client.get_channel(channel_id)  # Fetch the channel using its ID
    if channel:
        async for msg in channel.history(limit=None):
            await msg.delete()
        
        await send_view()
    else:
        print("Channel not found!")

@client.event
async def on_resumed():
    await on_ready()

@client.event
async def on_error(event, *args, **kwargs):
    print(f"發生錯誤: {event} {args} {kwargs}")

async def edit_resend_view():
    global message_id  # 明確宣告使用全域變數
    channel = client.get_channel(channel_id)

    if channel:
        view = MyView()
        sent_message = await channel.fetch_message(message_id)
        new_message = await sent_message.edit(view=view)
        message_id = new_message.id
        print("Message updated!")

async def send_view():
    global message_id
    channel = client.get_channel(channel_id)

    if channel:
        try:
            view = MyView()
            sent_message = await channel.send(file=discord.File("CountryState.png"), view=view)
            message_id = sent_message.id
            print("Message sent to channel!")
        except Exception as e:
            print(f"send_view() 發生錯誤: {e}")
    else:
        print("Channel not found!")

#%% --- FastAPI 設定 ---
app = FastAPI()

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"message": "Discord bot is running!"}

# @app.get("/")
# async def root():
#     return {"message": "Discord bot is running!"}

# --- 並行執行 bot 與 Web Server ---
async def start():
    # 啟動 web server
    config = uvicorn.Config(app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    # 同時啟動 bot 跟 web server
    bot_task = asyncio.create_task(client.start(DISCORD_TOKEN))
    web_task = asyncio.create_task(server.serve())
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    asyncio.run(start())

