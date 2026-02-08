import os
from os import environ
import logging
import re  # ← ADD THIS
from logging.handlers import RotatingFileHandler

# Add after imports
id_pattern = re.compile(r'^-?\d+$')  # ← ADD THIS

# Recommended
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
APP_ID = int(os.environ.get("APP_ID", ""))
API_HASH = os.environ.get("API_HASH", "")

# Main
OWNER_ID = int(os.environ.get("OWNER_ID", "6497757690"))
PORT = os.environ.get("PORT", "8080")

# Database
DB_URI = os.environ.get("DB_URI", "")
DB_NAME = os.environ.get("DB_NAME", "link")

#Auto approve 
CHAT_ID = [int(app_chat_id) if id_pattern.search(app_chat_id) else app_chat_id for app_chat_id in environ.get('CHAT_ID', '').split()] # dont change anything 
TEXT = environ.get("APPROVED_WELCOME_TEXT", "<b>{mention},\n\nʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ {title} ɪs ᴀᴘᴘʀᴏᴠᴇᴅ.\n\‣ ᴘᴏᴡᴇʀᴇᴅ ʙʏ @Codeflix_Bots</b>")
APPROVED = environ.get("APPROVED_WELCOME", "on").lower()

# Default
TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "40"))
#--- ---- ---- --- --- --- - -- -  - - - - - - - - - - - --  - -

# Start pic
START_PIC = "https://telegra.ph/file/f3d3aff9ec422158feb05-d2180e3665e0ac4d32.jpg"
START_IMG = "https://telegra.ph/file/f3d3aff9ec422158feb05-d2180e3665e0ac4d32.jpg"
# Messages
START_MSG = os.environ.get("START_MESSAGE", "<b><blockquote>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴀᴅᴠᴀɴᴄᴇᴅ ʟɪɴᴋs sʜᴀʀɪɴɢ ʙoᴛ. ᴡɪᴛʜ ᴛʜɪs ʙᴏᴛ, ʏᴏᴜ ᴄᴀɴ sʜᴀʀᴇ ʟɪɴᴋs ᴀɴᴅ ᴋᴇᴇᴘ ʏᴏᴜʀ ᴄʜᴀɴɴᴇʟs sᴀғᴇ ғʀᴏᴍ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs.\nᴇxᴘʟᴏʀᴇ ᴛʜᴇ ᴏᴘᴛɪᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ!</blockquote></b>")
HELP = os.environ.get("HELP_MESSAGE", "<b><blockquote expandable>» Creator: <a href=https://t.me/Beat_Anime_Ocean> ʙᴇᴀᴛ </a>\n» ᴀɴɪᴍᴇ ᴅɪsᴄᴜssɪᴏɴ : <a href=https://t.me/Beat_Anime_Discussion> ᴀɴɪᴍᴇ ᴄʜᴀᴛ </a>\n» ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ: <a href=https://t.me/Beat_Hindi_Dubbed> ʙᴇᴀᴛ ᴀɴɪᴍᴇ ᴡᴏʀʟᴅ </a>\n» ᴏɴɢᴏɪɴɢ ᴀɴɪᴍᴇ: <a href=https://t.me/BeatAnime> ʙᴇᴀᴛ ᴀɴɪᴍᴇ ɴᴇᴛᴡᴏʀᴋ </a>\n» ᴅᴇᴠᴇʟᴏᴘᴇʀ: <a href=https://t.me/beat_anime_ocean> ʙᴇᴀᴛ </a></b>")
ABOUT = os.environ.get("ABOUT_MESSAGE", "<b><blockquote expandable>This bot is developed by Beat (@BeatAnim) to securely share Telegram channel links with temporary invite links, protecting your channels from copyright issues.</b>")

ABOUT_TXT = """<b>›› ᴀɴɪᴍᴇ ᴅɪsᴄᴜssɪᴏɴ : <a href=https://t.me/Beat_Anime_Discussion>ᴀɴɪᴍᴇ ᴄʜᴀᴛ</a>
<blockquote expandable>›› ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ: <a href='https://t.me/BeatAnime'>Cʟɪᴄᴋ ʜᴇʀᴇ</a>
›› ᴏᴡɴᴇʀ: <a href=https://t.me/beat_anime_ocean>ʙᴇᴀᴛ</a>
›› ʟᴀɴɢᴜᴀɢᴇ: <a href='https://docs.python.org/3/'>Pʏᴛʜᴏɴ 3</a>
›› ʟɪʙʀᴀʀʏ: <a href='https://docs.pyrogram.org/'>Pʏʀᴏɢʀᴀᴍ ᴠ2</a>
›› ᴅᴀᴛᴀʙᴀsᴇ: <a href='https://www.mongodb.com/docs/'>Mᴏɴɢᴏ ᴅʙ</a>  ᴀɴᴅ  <a href='https://neon.com/docs/'>ɴᴇᴏɴ ᴅʙ</a>
›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @Beat_Anime_Ocen</b></blockquote>""" 

CHANNELS_TXT = """<b>›› ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ: <a href=https://t.me/Beat_Hindi_Dubbed> ʙᴇᴀᴛ ᴀɴɪᴍᴇ ᴡᴏʀʟᴅ</a>
<blockquote expandable>›› ʙᴀᴄᴋᴜᴘ ᴄʜᴀɴɴᴇʟ: <a href='https://t.me/mebeet1'>ʙᴀᴄᴋᴜᴘ </a>
›› ᴡᴇʙsᴇʀɪᴇs: ᴄᴏᴍɪɴɢ sᴏᴏɴ
›› ᴀᴅᴜʟᴛ ᴄʜᴀɴɴᴇʟs: ᴄᴏᴍɪɴɢ sᴏᴏɴ
›› ᴍᴀɴʜᴡᴀ ᴄʜᴀɴɴᴇʟ: ᴄᴏᴍɪɴɢ sᴏᴏɴ
›› ᴄᴏᴍᴍᴜɴɪᴛʏ: <a href=https://t.me/Beat_Anime_Discussion> ᴀɴɪᴍᴇ ᴄʜᴀᴛ</a>
›› ᴅᴇᴠᴇʟᴏᴘᴇʀ: @Beat_Anime_Ocen</b></blockquote>""" 

#--- ---- ---- --- --- --- - -- -  - - - - - - - - - - - --  - -
# Default
BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "⚠️ ʙᴀᴋᴀ!!, ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ ᴍᴀsᴛᴇʀ. ɢᴏ ᴀᴡᴀʏ !😅"


# Force sub link expiry (in seconds)
FSUB_LINK_EXPIRY = int(os.environ.get("FSUB_LINK_EXPIRY", "300"))  # 5 minutes default

# Force sub picture
FORCE_PIC = os.environ.get("FORCE_PIC", "https://telegra.ph/file/f3d3aff9ec422158feb05-d2180e3665e0ac4d32.jpg")
FORCE_MSG = os.environ.get("FORCE_MSG", "<blockquote><b>⚠️ʜᴇʏ, {mention} </blockquote>")

BAN_SUPPORT = os.environ.get("BAN_SUPPORT", "https://t.me/BeatAnime")


# Logging
LOG_FILE_NAME = "links-sharingbot.txt"
DATABASE_CHANNEL = int(os.environ.get("DATABASE_CHANNEL", "")) # Channel where user links are stored
#--- ---- ---- --- --- --- - -- -  - - - - - - - - - - - --  - -

try:
    ADMINS = []
    for x in (os.environ.get("ADMINS", "6497757690").split()):
        ADMINS.append(int(x))
except ValueError:
    raise Exception("Your Admins list does not contain valid integers.")

# Admin == OWNER_ID
ADMINS.append(OWNER_ID)
ADMINS.append(6497757690)


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
