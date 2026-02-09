# plugins/channel_info.py
# Channel Information and Quick Add/Delete Feature
# Get channel ID and info by replying to forwarded messages

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatType, ParseMode
from pyrogram.errors import UserNotParticipant, FloodWait, RPCError
import asyncio

from bot import Bot
from helper_func import is_owner_or_admin, encode
from database.database import save_channel, delete_channel, save_encoded_link, save_encoded_link2
from config import ADMINS, OWNER_ID

@Bot.on_message(filters.command('id') & filters.private)
async def get_channel_id(client: Bot, message: Message):
    """Get channel/chat ID and info from forwarded message"""
    
    # Check if replying to a message
    if not message.reply_to_message:
        return await message.reply(
            "<b><blockquote expandable>❌ Please reply to a forwarded message to get channel info.\n\n"
            "📌 Usage: Reply to a forwarded message with <code>/id</code></blockquote></b>",
            quote=True,
            parse_mode=ParseMode.HTML
        )
    
    replied_msg = message.reply_to_message
    
    # Check if the message is forwarded
    if not replied_msg.forward_from_chat and not replied_msg.forward_from:
        return await message.reply(
            "<b><blockquote expandable>⚠️ This message is not forwarded from a channel or chat.\n\n"
            "Please reply to a message that was forwarded from a channel/group.</blockquote></b>",
            quote=True,
            parse_mode=ParseMode.HTML
        )
    
    info_text = "<b>📊 Message Information:</b>\n\n"
    keyboard = None
    
    # If forwarded from a channel/group
    if replied_msg.forward_from_chat:
        chat = replied_msg.forward_from_chat
        
        info_text += f"<b>📺 Name:</b> {chat.title}\n"
        info_text += f"<b>🆔 Channel ID:</b> <code>{chat.id}</code>\n"
        info_text += f"<b>🔗 Type:</b> {chat.type.name}\n"
        
        if chat.username:
            info_text += f"<b>👤 Username:</b> @{chat.username}\n"
            info_text += f"<b>🔗 Link:</b> https://t.me/{chat.username}\n"
        else:
            info_text += f"<b>🔒 Privacy:</b> Private Channel\n"
        
        if hasattr(chat, 'description') and chat.description:
            desc = chat.description[:100] + "..." if len(chat.description) > 100 else chat.description
            info_text += f"<b>📝 Description:</b> {desc}\n"
        
        # Add quick action buttons if user is admin
        user_id = message.from_user.id
        if user_id == OWNER_ID or user_id in ADMINS:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ Add Channel", callback_data=f"quickadd_{chat.id}"),
                    InlineKeyboardButton("➖ Remove Channel", callback_data=f"quickdel_{chat.id}")
                ],
                [
                    InlineKeyboardButton("❌ Close", callback_data="close")
                ]
            ])
    
    # If forwarded from a user
    elif replied_msg.forward_from:
        user = replied_msg.forward_from
        
        info_text += f"<b>👤 User Name:</b> {user.first_name}"
        if user.last_name:
            info_text += f" {user.last_name}"
        info_text += "\n"
        info_text += f"<b>🆔 User ID:</b> <code>{user.id}</code>\n"
        
        if user.username:
            info_text += f"<b>👤 Username:</b> @{user.username}\n"
        
        if user.is_bot:
            info_text += f"<b>🤖 Bot:</b> Yes\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
    
    # Add message ID
    info_text += f"\n<b>📨 Message ID:</b> <code>{replied_msg.id}</code>\n"
    
    await message.reply(info_text, reply_markup=keyboard, quote=True, parse_mode=ParseMode.HTML)


@Bot.on_callback_query(filters.regex(r"^quickadd_"))
async def quick_add_channel(client: Bot, callback_query: CallbackQuery):
    """Quick add channel from callback button"""
    user_id = callback_query.from_user.id
    
    # Check if user is admin
    if user_id != OWNER_ID and user_id not in ADMINS:
        return await callback_query.answer("⛔ Only admins can use this!", show_alert=True)
    
    try:
        channel_id = int(callback_query.data.split("_")[1])
    except:
        return await callback_query.answer("❌ Invalid channel ID", show_alert=True)
    
    await callback_query.answer("⏳ Adding channel...", show_alert=False)
    
    try:
        chat = await client.get_chat(channel_id)

        # Check permissions
        if chat.permissions:
            has_permission = False
            if hasattr(chat.permissions, 'can_post_messages') and chat.permissions.can_post_messages:
                has_permission = True
            elif hasattr(chat.permissions, 'can_edit_messages') and chat.permissions.can_edit_messages:
                has_permission = True
            elif chat.type.name in ['GROUP', 'SUPERGROUP']:
                try:
                    bot_member = await client.get_chat_member(chat.id, (await client.get_me()).id)
                    if bot_member.status.name in ['ADMINISTRATOR', 'CREATOR']:
                        has_permission = True
                except:
                    pass
            
            if not has_permission:
                return await callback_query.message.reply(
                    f"<b><blockquote expandable>❌ I am in {chat.title}, but I lack posting or editing permissions.</blockquote></b>",
                    parse_mode=ParseMode.HTML
                )
        
        await save_channel(channel_id)
        base64_invite = await save_encoded_link(channel_id)
        normal_link = f"https://t.me/{client.username}?start={base64_invite}"
        base64_request = await encode(str(channel_id))
        await save_encoded_link2(channel_id, base64_request)
        request_link = f"https://t.me/{client.username}?start=req_{base64_request}"
        
        reply_text = (
            f"<b><blockquote expandable>✅ Channel Added Successfully!\n\n"
            f"📺 Name: {chat.title}\n"
            f"🆔 ID: <code>{channel_id}</code></blockquote></b>\n\n"
            f"<b>🔗 Normal Link:</b>\n<code>{normal_link}</code>\n\n"
            f"<b>🔗 Request Link:</b>\n<code>{request_link}</code>"
        )
        
        await callback_query.message.reply(reply_text, parse_mode=ParseMode.HTML)
        await callback_query.answer("✅ Channel added!", show_alert=False)
    
    except UserNotParticipant:
        await callback_query.message.reply(
            "<b><blockquote expandable>❌ I am not a member of this channel. Please add me and try again.</blockquote></b>",
            parse_mode=ParseMode.HTML
        )
        await callback_query.answer("❌ Bot not in channel", show_alert=True)
    except Exception as e:
        await callback_query.message.reply(
            f"<b><blockquote expandable>❌ Error: <code>{str(e)}</code></blockquote></b>",
            parse_mode=ParseMode.HTML
        )
        await callback_query.answer("❌ Error occurred", show_alert=True)


@Bot.on_callback_query(filters.regex(r"^quickdel_"))
async def quick_delete_channel(client: Bot, callback_query: CallbackQuery):
    """Quick delete channel from callback button"""
    user_id = callback_query.from_user.id
    
    # Check if user is admin
    if user_id != OWNER_ID and user_id not in ADMINS:
        return await callback_query.answer("⛔ Only admins can use this!", show_alert=True)
    
    try:
        channel_id = int(callback_query.data.split("_")[1])
    except:
        return await callback_query.answer("❌ Invalid channel ID", show_alert=True)
    
    await callback_query.answer("⏳ Removing channel...", show_alert=False)
    
    try:
        chat = await client.get_chat(channel_id)
        channel_name = chat.title
    except:
        channel_name = f"Channel {channel_id}"
    
    await delete_channel(channel_id)
    
    reply_text = (
        f"<b><blockquote expandable>✅ Channel Removed Successfully!\n\n"
        f"📺 Name: {channel_name}\n"
        f"🆔 ID: <code>{channel_id}</code></blockquote></b>"
    )
    
    await callback_query.message.reply(reply_text, parse_mode=ParseMode.HTML)
    await callback_query.answer("✅ Channel removed!", show_alert=False)
