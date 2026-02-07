# Don't Remove Credit @BeatAnime, @mebeet1
# Ask Doubt on telegram @Beat_Anime_Discussion
#
# Copyright (C) 2025 by Beat Anime-Bots@Github, < https://github.com/beathindidubbed-lab >.
#
# This file is part of < https://github.com/beathindidubbed-lab/Advance-File-Share-bot-V4 > project,
# and is released under the MIT License.
# Please see < https://github.com/beathindidubbed-lab/Advance-File-Share-bot-V4/blob/master/LICENSE >
#
# All rights reserved.
#

import random
import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from bot import Bot
from config import *

# Default help pictures (can be customized via config)
HELP_PICS = os.environ.get("HELP_PICS", "").split(",")
if not HELP_PICS or HELP_PICS == [""]:
    HELP_PICS = [
        "https://ibb.co/BVccVQZq"
    ]

# Start pictures support (NEW FEATURE)
START_PICS = os.environ.get("START_PICS", "").split(",")
if not START_PICS or START_PICS == [""]:
    # Use single START_PIC from config as default, or fallback
    START_PICS = [START_PIC] if START_PIC else [
        "https://telegra.ph/file/ec17880d61180d3312d6a.jpg"
    ]

def get_random_help_pic():
    """Get a random help picture from the list"""
    try:
        return random.choice([pic.strip() for pic in HELP_PICS if pic.strip()])
    except:
        return HELP_PICS[0]


def get_random_start_pic():
    """Get a random start picture from the list"""
    try:
        return random.choice([pic.strip() for pic in START_PICS if pic.strip()])
    except:
        return START_PICS[0]


def create_help_text(user_name: str) -> str:
    """
    Create help text with expandable blockquote
    """
    help_content = (
        "<b>➪ I ᴀᴍ ᴀ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇ sʜᴀʀɪɴɢ ʙᴏᴛ, ᴍᴇᴀɴᴛ ᴛᴏ ᴘʀᴏᴠɪᴅᴇ ғɪʟᴇs ᴀɴᴅ ɴᴇᴄᴇssᴀʀʏ sᴛᴜғғ ᴛʜʀᴏᴜɢʜ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ ғᴏʀ sᴘᴇᴄɪғɪᴄ ᴄʜᴀɴɴᴇʟs.\n\n"
        "➪ Iɴ ᴏʀᴅᴇʀ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ʏᴏᴜ ʜᴀᴠᴇ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ ᴀʟʟ ᴍᴇɴᴛɪᴏɴᴇᴅ ᴄʜᴀɴɴᴇʟ ᴛʜᴀᴛ I ᴘʀᴏᴠɪᴅᴇ ʏᴏᴜ ᴛᴏ ᴊᴏɪɴ. "
        "Yᴏᴜ ᴄᴀɴ ɴᴏᴛ ᴀᴄᴄᴇss ᴏʀ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ᴜɴʟᴇss ʏᴏᴜ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs.\n\n"
        "➪ Sᴏ ᴊᴏɪɴ Mᴇɴᴛɪᴏɴᴇᴅ Cʜᴀɴɴᴇʟs ᴛᴏ ɢᴇᴛ Fɪʟᴇs ᴏʀ ɪɴɪᴛɪᴀᴛᴇ ᴍᴇssᴀɢᴇs...\n\n"
        "━ /help - Oᴘᴇɴ ᴛʜɪs ʜᴇʟᴘ ᴍᴇssᴀɢᴇ !</b>"
    )
    
    # Wrap in expandable blockquote
    blockquote_content = f'<blockquote expandable>{help_content}</blockquote>'
    
    return (
        f"<b>‼️ Hᴇʟʟᴏ {user_name} ~</b>\n\n"
        f"{blockquote_content}\n"
        "<b>◈ Sᴛɪʟʟ ʜᴀᴠᴇ ᴅᴏᴜʙᴛs, ᴄᴏɴᴛᴀᴄᴛ ʙᴇʟᴏᴡ ᴘᴇʀsᴏɴs/ɢʀᴏᴜᴘ ᴀs ᴘᴇʀ ʏᴏᴜʀ ɴᴇᴇᴅ !</b>"
    )


@Bot.on_message(filters.command("help") & filters.private)
async def help_command(client: Bot, message: Message):
    """
    Handle /help command
    Shows help information with expandable blockquote
    """
    user = message.from_user
    user_name = user.first_name
    
    # Get random help picture
    help_pic = get_random_help_pic()
    
    # Create help text with expandable blockquote
    help_text = create_help_text(user_name)
    
    # Create inline keyboard buttons
    buttons = [
        [
            InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/Beat_Hindi_Dubbed"),
            InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url="https://t.me/Beat_Anime_Ocean")
        ],
        [
            InlineKeyboardButton("ᴀʙᴏᴜᴛ ᴍᴇ ", callback_data="about"),
            InlineKeyboardButton(" ʙᴀᴄᴋ", callback_data="start")
        ],
        [
            InlineKeyboardButton("ᴄʟᴏsᴇ ✖️", callback_data="close")
        ]
    ]
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    try:
        # Try to send with photo
        await message.reply_photo(
            photo=help_pic,
            caption=help_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            quote=True
        )
    except Exception as e:
        # Fallback to text-only if photo fails
        print(f"Error sending help photo: {e}")
        await message.reply_text(
            text=help_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            quote=True
        )


