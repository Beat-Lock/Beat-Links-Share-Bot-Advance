# plugins/fsub.py
# Force Subscription Module
# Modified By [telegram username: @Codeflix_Bots]

from bot import Bot
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant
from pyrogram.enums import ChatMemberStatus, ParseMode
from database.database import add_fsub_channel, remove_fsub_channel, get_fsub_channels
from helper_func import is_owner_or_admin
from config import ADMINS

# ==================== FSUB MANAGEMENT COMMANDS ====================

@Bot.on_message(filters.command('addfsub') & is_owner_or_admin)
async def add_fsub_command(client: Bot, message: Message):
    """Add a channel to force subscription list"""
    if len(message.command) != 2:
        return await message.reply(
            "<b><blockquote expandable>Usage: <code>/addfsub &lt;channel_id&gt;</code>\n"
            "Example: <code>/addfsub -1001234567890</code></b>"
        )
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply("<b><blockquote expandable>❌ Invalid channel ID. Must be a number.</b>")
    
    # Verify bot has access to the channel
    try:
        chat = await client.get_chat(channel_id)
        
        # Check if bot is admin
        bot_member = await client.get_chat_member(channel_id, (await client.get_me()).id)
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await message.reply(
                f"<b><blockquote expandable>❌ I must be an admin in {chat.title} to add it as FSub channel.</b>"
            )
        
        # Add to database
        success = await add_fsub_channel(channel_id)
        if success:
            await message.reply(
                f"<b><blockquote expandable>✅ Force Subscription Added\n\n"
                f"Channel: {chat.title}\n"
                f"ID: <code>{channel_id}</code>\n\n"
                f"Users must now join this channel to use the bot.</b>"
            )
        else:
            await message.reply(
                f"<b><blockquote expandable>⚠️ Channel {chat.title} is already in FSub list.</b>"
            )
            
    except Exception as e:
        await message.reply(
            f"<b><blockquote expandable>❌ Error: <code>{str(e)}</code>\n\n"
            "Make sure:\n"
            "• The channel ID is correct\n"
            "• I'm a member/admin of the channel</b>"
        )

@Bot.on_message(filters.command('delfsub') & is_owner_or_admin)
async def del_fsub_command(client: Bot, message: Message):
    """Remove a channel from force subscription list"""
    if len(message.command) != 2:
        return await message.reply(
            "<b><blockquote expandable>Usage: <code>/delfsub &lt;channel_id&gt;</code></b>"
        )
    
    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply("<b><blockquote expandable>❌ Invalid channel ID.</b>")
    
    success = await remove_fsub_channel(channel_id)
    if success:
        await message.reply(
            f"<b><blockquote expandable>✅ Removed channel <code>{channel_id}</code> from Force Subscription list.</b>"
        )
    else:
        await message.reply(
            f"<b><blockquote expandable>❌ Channel <code>{channel_id}</code> not found in FSub list.</b>"
        )

@Bot.on_message(filters.command('fsublist') & is_owner_or_admin)
async def list_fsub_command(client: Bot, message: Message):
    """List all force subscription channels"""
    channels = await get_fsub_channels()
    
    if not channels:
        return await message.reply(
            "<b><blockquote expandable>📋 No Force Subscription channels configured.\n\n"
            "Use <code>/addfsub &lt;channel_id&gt;</code> to add channels.</b>"
        )
    
    text = "<b>📋 Force Subscription Channels:</b>\n\n"
    
    for i, channel_id in enumerate(channels, 1):
        try:
            chat = await client.get_chat(channel_id)
            invite_link = f"https://t.me/{chat.username}" if chat.username else "Private Channel"
            text += f"<b>{i}. {chat.title}</b>\n"
            text += f"   <b>➥ ID:</b> <code>{channel_id}</code>\n"
            text += f"   <b>➥ Link:</b> {invite_link}\n\n"
        except Exception as e:
            text += f"<b>{i}.</b> <code>{channel_id}</code> (Error: {str(e)})\n\n"
    
    await message.reply(text)
