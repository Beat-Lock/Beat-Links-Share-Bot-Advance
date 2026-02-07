# plugins/banuser.py
# Ban/Unban User System
# Modified By [telegram username: @Codeflix_Bots]

import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID
from helper_func import is_owner_or_admin
from database.database import add_ban_user, del_ban_user, get_ban_users, is_admin

# ==================== BAN USER COMMAND ====================

@Bot.on_message(filters.private & filters.command('ban') & is_owner_or_admin)
async def add_banuser(client: Bot, message: Message):
    """Ban users from using the bot"""
    pro = await message.reply("⏳ <i>Pʀᴏᴄᴇssɪɴɢ ʀᴇǫᴜᴇsᴛ...</i>", quote=True)
    banuser_ids = await get_ban_users()
    banusers = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• Cʟᴏsᴇ •", callback_data="close")]])

    if not banusers:
        return await pro.edit(
            "<b><blockquote expandable>❗ Yᴏᴜ ᴍᴜsᴛ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ IDs ᴛᴏ ʙᴀɴ.</b>\n\n"
            "<b>📌 Usᴀɢᴇ:</b>\n"
            "<code>/ban [user_id]</code> — Ban one or more users by ID\n"
            "<code>/ban 123456789 987654321</code> — Ban multiple users</blockquote>",
            reply_markup=reply_markup
        )

    report, success_count = "", 0
    
    for uid in banusers:
        try:
            uid_int = int(uid)
        except:
            report += f"⚠️ Iɴᴠᴀʟɪᴅ ID: <code>{uid}</code>\n"
            continue

        # Don't ban admins or owner
        if await is_admin(uid_int) or uid_int == OWNER_ID:
            report += f"⛔ Sᴋɪᴘᴘᴇᴅ ᴀᴅᴍɪɴ/ᴏᴡɴᴇʀ ID: <code>{uid_int}</code>\n"
            continue

        # Check if already banned
        if uid_int in banuser_ids:
            report += f"⚠️ Aʟʀᴇᴀᴅʏ ʙᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
            continue

        # Validate Telegram ID length (usually 9-10 digits)
        if len(str(uid_int)) >= 9 and len(str(uid_int)) <= 10:
            await add_ban_user(uid_int)
            report += f"✅ Bᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
            success_count += 1
        else:
            report += f"⚠️ Iɴᴠᴀʟɪᴅ Tᴇʟᴇɢʀᴀᴍ ID ʟᴇɴɢᴛʜ: <code>{uid_int}</code>\n"

    if success_count:
        await pro.edit(
            f"<b><blockquote expandable>✅ Bᴀɴɴᴇᴅ Usᴇʀs Uᴘᴅᴀᴛᴇᴅ:</b>\n\n{report}</blockquote>",
            reply_markup=reply_markup
        )
    else:
        await pro.edit(
            f"<b><blockquote expandable>❌ Nᴏ ᴜsᴇʀs ᴡᴇʀᴇ ʙᴀɴɴᴇᴅ.</b>\n\n{report}</blockquote>",
            reply_markup=reply_markup
        )


# ==================== UNBAN USER COMMAND ====================

@Bot.on_message(filters.private & filters.command('unban') & is_owner_or_admin)
async def delete_banuser(client: Bot, message: Message):
    """Unban users from the bot"""
    pro = await message.reply("⏳ <i>Pʀᴏᴄᴇssɪɴɢ ʀᴇǫᴜᴇsᴛ...</i>", quote=True)
    banuser_ids = await get_ban_users()
    banusers = message.text.split()[1:]

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• Cʟᴏsᴇ •", callback_data="close")]])

    if not banusers:
        return await pro.edit(
            "<b><blockquote expandable>❗ Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴜsᴇʀ IDs ᴛᴏ ᴜɴʙᴀɴ.</b>\n\n"
            "<b>📌 Usᴀɢᴇ:</b>\n"
            "<code>/unban [user_id]</code> — Unban specific user(s)\n"
            "<code>/unban all</code> — Remove all banned users</blockquote>",
            reply_markup=reply_markup
        )

    # Handle "unban all" command
    if banusers[0].lower() == "all":
        if not banuser_ids:
            return await pro.edit(
                "<b><blockquote expandable>✅ Nᴏ ᴜsᴇʀs ɪɴ ᴛʜᴇ ʙᴀɴ ʟɪsᴛ.</b></blockquote>",
                reply_markup=reply_markup
            )
        
        count = 0
        listed = ""
        for uid in banuser_ids:
            await del_ban_user(uid)
            listed += f"✅ Uɴʙᴀɴɴᴇᴅ: <code>{uid}</code>\n"
            count += 1
        
        return await pro.edit(
            f"<b><blockquote expandable>🚫 Cʟᴇᴀʀᴇᴅ Bᴀɴ Lɪsᴛ ({count} users):</b>\n\n{listed}</blockquote>",
            reply_markup=reply_markup
        )

    # Unban specific users
    report = ""
    success_count = 0
    
    for uid in banusers:
        try:
            uid_int = int(uid)
        except:
            report += f"⚠️ Iɴᴠᴀʟɪᴅ ID: <code>{uid}</code>\n"
            continue

        if uid_int in banuser_ids:
            await del_ban_user(uid_int)
            report += f"✅ Uɴʙᴀɴɴᴇᴅ: <code>{uid_int}</code>\n"
            success_count += 1
        else:
            report += f"⚠️ Nᴏᴛ ɪɴ ʙᴀɴ ʟɪsᴛ: <code>{uid_int}</code>\n"

    if success_count:
        await pro.edit(
            f"<b><blockquote expandable>🚫 Uɴʙᴀɴ Rᴇᴘᴏʀᴛ:</b>\n\n{report}</blockquote>",
            reply_markup=reply_markup
        )
    else:
        await pro.edit(
            f"<b><blockquote expandable>❌ Nᴏ ᴜsᴇʀs ᴡᴇʀᴇ ᴜɴʙᴀɴɴᴇᴅ.</b>\n\n{report}</blockquote>",
            reply_markup=reply_markup
        )


# ==================== BAN LIST COMMAND ====================

@Bot.on_message(filters.private & filters.command('banlist') & is_owner_or_admin)
async def get_banuser_list(client: Bot, message: Message):
    """Show list of all banned users"""
    pro = await message.reply("⏳ <i>Fᴇᴛᴄʜɪɴɢ Bᴀɴ Lɪsᴛ...</i>", quote=True)
    banuser_ids = await get_ban_users()

    if not banuser_ids:
        return await pro.edit(
            "<b><blockquote expandable>✅ Nᴏ ᴜsᴇʀs ɪɴ ᴛʜᴇ ʙᴀɴ ʟɪsᴛ.</b></blockquote>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• Cʟᴏsᴇ •", callback_data="close")]])
        )

    result = f"<b>🚫 Bᴀɴɴᴇᴅ Usᴇʀs ({len(banuser_ids)}):</b>\n\n"
    
    for uid in banuser_ids:
        await message.reply_chat_action(ChatAction.TYPING)
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            username = f"@{user.username}" if user.username else "No username"
            result += f"• {user_link} — <code>{uid}</code>\n   ➥ {username}\n\n"
        except:
            result += f"• <code>{uid}</code> — <i>Cᴏᴜʟᴅ ɴᴏᴛ ғᴇᴛᴄʜ ɴᴀᴍᴇ</i>\n\n"

    result += f"\n<b>Tᴏᴛᴀʟ Bᴀɴɴᴇᴅ:</b> <code>{len(banuser_ids)}</code>"
    
    await pro.edit(
        result,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• Cʟᴏsᴇ •", callback_data="close")]])
    )


# ==================== CHECK BAN STATUS ====================

@Bot.on_message(filters.private & filters.command('checkban') & is_owner_or_admin)
async def check_ban_status(client: Bot, message: Message):
    """Check if a user is banned"""
    if len(message.command) < 2:
        return await message.reply(
            "<b><blockquote expandable>❗ Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴜsᴇʀ ID.</b>\n\n"
            "<b>📌 Usᴀɢᴇ:</b>\n"
            "<code>/checkban [user_id]</code></blockquote>"
        )
    
    try:
        uid = int(message.command[1])
    except:
        return await message.reply(
            "<b><blockquote expandable>⚠️ Iɴᴠᴀʟɪᴅ ᴜsᴇʀ ID.</b></blockquote>"
        )
    
    banuser_ids = await get_ban_users()
    
    if uid in banuser_ids:
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            username = f"@{user.username}" if user.username else "No username"
            
            await message.reply(
                f"<b><blockquote expandable>🚫 Usᴇʀ ɪs BANNED</b>\n\n"
                f"<b>Nᴀᴍᴇ:</b> {user_link}\n"
                f"<b>ID:</b> <code>{uid}</code>\n"
                f"<b>Usᴇʀɴᴀᴍᴇ:</b> {username}</blockquote>",
                disable_web_page_preview=True
            )
        except:
            await message.reply(
                f"<b><blockquote expandable>🚫 Usᴇʀ ɪs BANNED</b>\n\n"
                f"<b>ID:</b> <code>{uid}</code></blockquote>"
            )
    else:
        try:
            user = await client.get_users(uid)
            user_link = f'<a href="tg://user?id={uid}">{user.first_name}</a>'
            username = f"@{user.username}" if user.username else "No username"
            
            await message.reply(
                f"<b><blockquote expandable>✅ Usᴇʀ ɪs NOT BANNED</b>\n\n"
                f"<b>Nᴀᴍᴇ:</b> {user_link}\n"
                f"<b>ID:</b> <code>{uid}</code>\n"
                f"<b>Usᴇʀɴᴀᴍᴇ:</b> {username}</blockquote>",
                disable_web_page_preview=True
            )
        except:
            await message.reply(
                f"<b><blockquote expandable>✅ Usᴇʀ ɪs NOT BANNED</b>\n\n"
                f"<b>ID:</b> <code>{uid}</code></blockquote>"
            )
