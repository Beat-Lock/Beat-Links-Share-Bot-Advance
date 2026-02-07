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

# ==================== FSUB CHECK FUNCTIONS ====================

async def is_user_subscribed(client: Bot, user_id: int, channel_id: int) -> bool:
    """Check if user is subscribed to a channel"""
    try:
        member = await client.get_chat_member(channel_id, user_id)
        return member.status in [
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        ]
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Error checking subscription for user {user_id} in channel {channel_id}: {e}")
        return False

async def check_fsub_status(client: Bot, user_id: int):
    """
    Check if user is subscribed to all FSub channels
    Returns: (is_subscribed: bool, message: str, buttons: InlineKeyboardMarkup or None)
    """
    fsub_channels = await get_fsub_channels()
    
    # If no FSub channels configured, allow access
    if not fsub_channels:
        return True, None, None
    
    not_joined = []
    
    # Check each FSub channel
    for channel_id in fsub_channels:
        if not await is_user_subscribed(client, user_id, channel_id):
            not_joined.append(channel_id)
    
    # If user has joined all channels
    if not not_joined:
        return True, None, None
    
    # Build join buttons for channels user hasn't joined
    buttons = []
    channel_names = []
    
    for channel_id in not_joined:
        try:
            chat = await client.get_chat(channel_id)
            channel_names.append(chat.title)
            
            # Generate invite link
            if chat.username:
                invite_link = f"https://t.me/{chat.username}"
            else:
                # Create temporary invite link for private channels
                invite = await client.create_chat_invite_link(channel_id)
                invite_link = invite.invite_link
            
            buttons.append([InlineKeyboardButton(
                f"📢 Join {chat.title}",
                url=invite_link
            )])
        except Exception as e:
            print(f"Error getting channel info for {channel_id}: {e}")
    
    # Add "Try Again" button
    buttons.append([InlineKeyboardButton("✅ I Joined, Check Again", callback_data="check_fsub")])
    
    # Create message text
    channel_list = "\n".join([f"• {name}" for name in channel_names])
    message_text = (
        f"<b>🔒 You Must Join Our Channel(s) To Use This Bot</b>\n\n"
        f"<blockquote expandable>{channel_list}</blockquote>\n\n"
        f"<b>👇 Click the button(s) below to join, then click 'Check Again'</b>"
    )
    
    return False, message_text, InlineKeyboardMarkup(buttons)

# ==================== CALLBACK HANDLERS ====================

@Bot.on_callback_query(filters.regex("check_fsub"))
async def check_fsub_callback(client: Bot, callback_query: CallbackQuery):
    """Handle FSub verification when user clicks 'Check Again'"""
    user_id = callback_query.from_user.id
    
    # Check subscription status
    is_subscribed, fsub_message, fsub_buttons = await check_fsub_status(client, user_id)
    
    if is_subscribed:
        # User has joined all channels
        await callback_query.answer("✅ Verified! You can now use the bot.", show_alert=True)
        await callback_query.message.delete()
        
        # Send start message
        from config import START_PIC, START_MSG
        inline_buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
                 InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs", callback_data="channels")],
                [InlineKeyboardButton("• Close •", callback_data="close")]
            ]
        )
        
        try:
            await callback_query.message.reply_photo(
                photo=START_PIC,
                caption=START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Error sending start picture: {e}")
            await callback_query.message.reply_text(
                START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )
    else:
        # User still hasn't joined all channels
        await callback_query.answer(
            "❌ You haven't joined all channels yet! Please join and try again.",
            show_alert=True
        )
        
        # Update the message with current status
        try:
            await callback_query.message.edit_text(
                fsub_message,
                reply_markup=fsub_buttons,
                parse_mode=ParseMode.HTML
            )
        except:
            pass
