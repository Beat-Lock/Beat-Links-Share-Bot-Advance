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

import random
import os
import psutil
import asyncio
from datetime import datetime, timezone
from pyrogram import Client 
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *
from helper_func import get_readable_time, get_exp_time

print("[CBB] Loading COMPLETE callback handler module...")



    # ============================================
    # BASIC NAVIGATION CALLBACKS
    # ============================================
    
    elif data == "help":
        user_name = query.from_user.first_name
        
        help_content = (
            "<b>➪ I ᴀᴍ ᴀ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇ sʜᴀʀɪɴɢ ʙᴏᴛ, ᴍᴇᴀɴᴛ ᴛᴏ ᴘʀᴏᴠɪᴅᴇ ғɪʟᴇs ᴀɴᴅ ɴᴇᴄᴇssᴀʀʏ sᴛᴜғғ ᴛʜʀᴏᴜɢʜ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ ғᴏʀ sᴘᴇᴄɪғɪᴄ ᴄʜᴀɴɴᴇʟs.\n\n"
            "➪ Iɴ ᴏʀᴅᴇʀ ᴛᴏ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ʏᴏᴜ ʜᴀᴠᴇ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ ᴀʟʟ ᴍᴇɴᴛɪᴏɴᴇᴅ ᴄʜᴀɴɴᴇʟ ᴛʜᴀᴛ I ᴘʀᴏᴠɪᴅᴇ ʏᴏᴜ ᴛᴏ ᴊᴏɪɴ. "
            "Yᴏᴜ ᴄᴀɴ ɴᴏᴛ ᴀᴄᴄᴇss ᴏʀ ɢᴇᴛ ᴛʜᴇ ғɪʟᴇs ᴜɴʟᴇss ʏᴏᴜ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs.\n\n"
            "➪ Sᴏ ᴊᴏɪɴ Mᴇɴᴛɪᴏɴᴇᴅ Cʜᴀɴɴᴇʟs ᴛᴏ ɢᴇᴛ Fɪʟᴇs ᴏʀ ɪɴɪᴛɪᴀᴛᴇ ᴍᴇssᴀɢᴇs...\n\n"
            "━ /help - Oᴘᴇɴ ᴛʜɪs ʜᴇʟᴘ ᴍᴇssᴀɢᴇ !</b>"
        )
        
        help_text = (
            f"<b>‼️ Hᴇʟʟᴏ {user_name} ~</b>\n\n"
            f"<blockquote expandable>{help_content}</blockquote>\n"
            "<b>◈ Sᴛɪʟʟ ʜᴀᴠᴇ ᴅᴏᴜʙᴛs, ᴄᴏɴᴛᴀᴄᴛ ʙᴇʟᴏᴡ ᴘᴇʀsᴏɴs/ɢʀᴏᴜᴘ ᴀs ᴘᴇʀ ʏᴏᴜʀ ɴᴇᴇᴅ !</b>"
        )
        
        await query.message.delete()
        help_pic = get_random_help_pic()
        
        try:
            await query.message.reply_photo(
                photo=help_pic,
                caption=help_text,
                reply_markup=InlineKeyboardMarkup([
                    [ InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/Beat_Hindi_Dubbed"),
                      InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url="https://t.me/Beat_Anime_Ocean")
                    ],
                    [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                     InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
                ])
            )
            print(f"[CBB] ✅ Sent help with photo to {user_id}")
        except Exception as e:
            print(f"[CBB] ⚠️ Help photo failed for {user_id}: {e}")
            print(f"[CBB] 🔗 Failed URL: {help_pic}")
            await query.message.reply_text(
                text=help_text,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([
                    [ InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/Beat_Hindi_Dubbed"),
                      InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url="https://t.me/Beat_Anime_Ocean")
                    ],
                    [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                     InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
                ])
            )
    elif data == "about":
        await query.message.delete()
        start_pic = get_random_start_pic()
        
        try:
            await query.message.reply_photo(
                photo=start_pic,
                caption=ABOUT_TXT.format(first=query.from_user.first_name),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                     InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
                ])
            )
            print(f"[CBB] ✅ Sent about with photo to {user_id}")
        except Exception as e:
            print(f"[CBB] ⚠️ About photo failed for {user_id}: {e}")
            print(f"[CBB] 🔗 Failed URL: {start_pic}")
            await query.message.reply_text(
                text=ABOUT_TXT.format(first=query.from_user.first_name),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                     InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
                ])
            )

    

    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()

    

print("[CBB] ✅ COMPLETE Comprehensive callback handler loaded!")



