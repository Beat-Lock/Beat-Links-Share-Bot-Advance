import asyncio
import base64
import time
from asyncio import Lock
from collections import defaultdict
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatMemberStatus, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors import FloodWait, UserNotParticipant, UserIsBlocked, InputUserDeactivated
import os
from asyncio import sleep
import random 

from bot import Bot
from datetime import datetime, timedelta
from config import *
from database.database import *
from plugins.newpost import revoke_invite_after_5_minutes
from helper_func import *

# Create a lock dictionary for each channel to prevent concurrent link generation
channel_locks = defaultdict(asyncio.Lock)

user_banned_until = {}

# Broadcast variables
cancel_lock = asyncio.Lock()
is_canceled = False

# Create a global dictionary to store chat data
chat_data_cache = {}

async def is_user_joined_channel(client: Client, user_id: int, chat_id: int) -> bool:
    """Check if user has joined a specific channel"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        return False
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"⚠️ Error checking membership for user {user_id} in channel {chat_id}: {e}")
        # In case of error, assume user hasn't joined to be safe
        return False

async def get_fsub_channels_not_joined(client: Client, user_id: int) -> list:
    """Get list of FSub channels the user hasn't joined yet"""
    not_joined = []
    
    try:
        # Get all FSub channels from database
        fsub_channels = await db.show_channels()
        
        if not fsub_channels:
            print("ℹ️ No FSub channels configured")
            return []
        
        print(f"📋 Checking {len(fsub_channels)} FSub channels for user {user_id}")
        
        for channel_id in fsub_channels:
            try:
                # Check if user has joined this channel
                is_joined = await is_user_joined_channel(client, user_id, channel_id)
                
                if not is_joined:
                    # Get channel info
                    try:
                        if channel_id in chat_data_cache:
                            chat = chat_data_cache[channel_id]
                        else:
                            chat = await client.get_chat(channel_id)
                            chat_data_cache[channel_id] = chat
                        
                        not_joined.append({
                            'id': channel_id,
                            'title': chat.title,
                            'username': chat.username,
                            'chat': chat
                        })
                        print(f"❌ User {user_id} NOT joined: {chat.title} ({channel_id})")
                    except Exception as e:
                        print(f"⚠️ Error getting info for channel {channel_id}: {e}")
                else:
                    print(f"✅ User {user_id} already joined channel {channel_id}")
                    
            except Exception as e:
                print(f"⚠️ Error processing channel {channel_id}: {e}")
                
    except Exception as e:
        print(f"❌ Error in get_fsub_channels_not_joined: {e}")
    
    return not_joined

async def show_fsub_panel(client: Client, message: Message, not_joined_channels: list):
    """Display the Force Subscribe panel with join buttons"""
    buttons = []
    
    print(f"🔧 Creating FSub panel for {len(not_joined_channels)} channels")
    
    for idx, channel_info in enumerate(not_joined_channels, 1):
        channel_id = channel_info['id']
        chat = channel_info['chat']
        
        try:
            print(f"  Processing channel {idx}: {chat.title} ({channel_id})")
            
            # Get channel mode (request link or normal invite) with error handling
            try:
                mode = await db.get_channel_mode(channel_id)
                print(f"    Mode: {mode}")
            except Exception as mode_error:
                print(f"    ⚠️ Error getting mode, using 'off' as default: {mode_error}")
                mode = "off"
            
            # Generate invite link for the ACTUAL CHANNEL, not the bot
            if mode == "on" and not chat.username:
                # Create request link for the CHANNEL
                print(f"    Creating request link for channel...")
                try:
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        creates_join_request=True,
                        expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                    )
                    link = invite.invite_link
                    print(f"    ✅ Request link created: {link}")
                except Exception as e:
                    print(f"    ⚠️ Failed to create request link, falling back to normal invite: {e}")
                    # Fall back to normal invite
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                    )
                    link = invite.invite_link
            else:
                # Create normal invite link or use username for the CHANNEL
                if chat.username:
                    link = f"https://t.me/{chat.username}"
                    print(f"    ✅ Using public channel link: @{chat.username}")
                else:
                    print(f"    Creating invite link for channel...")
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                    )
                    link = invite.invite_link
                    print(f"    ✅ Invite link created: {link}")
            
            # Add button for this channel - Each channel on its own row for better visibility
            button_text = f" {chat.title.upper()}"
            buttons.append([InlineKeyboardButton(text=button_text, url=link)])
            print(f"    ✅ Button added: {button_text} -> {link}")
            
        except Exception as e:
            print(f"    ❌ Error creating button for channel {channel_id}: {e}")
            import traceback
            traceback.print_exc()
            # Try to add a basic link if possible
            try:
                if chat.username:
                    link = f"https://t.me/{chat.username}"
                    buttons.append([InlineKeyboardButton(
                        text=f" {chat.title.upper()}", 
                        url=link
                    )])
                else:
                    # Can't create button without proper link
                    print(f"    ⚠️ Skipping channel {chat.title} - no username and invite failed")
            except:
                pass
    
    # Check if we have any buttons
    if not buttons:
        print("⚠️ No buttons were created! Falling back to text message.")
        await message.reply_text(
            "<b>⚠️ Please contact admin - FSub channels configured but buttons failed to generate.</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Add "Try Again" button - Make it prominent
    try:
        # Try to get the start parameter if available
        start_param = message.text.split()[1] if len(message.text.split()) > 1 else ""
        if start_param:
            retry_url = f"https://t.me/{client.username}?start={start_param}"
        else:
            retry_url = f"https://t.me/{client.username}?start=refresh"
        
        # Add reload button after all channel buttons
        buttons.append([InlineKeyboardButton(text='♻️ Try Again', url=retry_url)])
        print(f"✅ Reload button added")
    except Exception as e:
        print(f"⚠️ Error adding reload button: {e}")
        buttons.append([InlineKeyboardButton(text='♻️ Try Again ', url=f"https://t.me/{client.username}")])
    
    print(f"✅ Total buttons created: {len(buttons)}")
    
    # Send FSub message
    try:
        # Create the message text
        fsub_caption = FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name if message.from_user.last_name else "",
            username=f"@{message.from_user.username}" if message.from_user.username else "None",
            mention=message.from_user.mention,
            id=message.from_user.id
        )
        
        # Add instruction text
        instruction_text = (
            f"ʏᴏᴜ ʜᴀᴠᴇɴᴛ ᴊᴏɪɴ {len(not_joined_channels)}.ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ᴘʀᴏᴠɪᴅᴇᴅ ʙᴇʟᴏᴡ, ᴛʜᴇɴ ᴛʀʏ ᴀɢᴀɪɴ.. ! </b>\n"
            f"<b>❗ғᴀᴄɪɴɢ ᴘʀᴏʙʟᴇᴍs. ᴜsᴇ /help</b>"
        )
        
        full_caption = fsub_caption + instruction_text
        
        await message.reply_photo(
            photo=FORCE_PIC,
            caption=full_caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
        print(f"✅ FSub panel sent successfully to user {message.from_user.id}")
        
    except Exception as e:
        print(f"❌ Error sending FSub panel with photo: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to text message
        try:
            await message.reply_text(
                f"<b>⚠️ Please join the following channels to use this bot:</b>\n\n" + 
                "\n".join([f"📢 {ch['title']}" for ch in not_joined_channels]) +
                f"\n\n<b>After joining, click the RELOAD button below.</b>",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
            print(f"✅ FSub panel sent as text (fallback)")
        except Exception as e2:
            print(f"❌ Complete failure sending FSub panel: {e2}")
            await message.reply_text(
                "⚠️ Error displaying force subscribe panel. Please contact admin.",
                parse_mode=ParseMode.HTML
            )

async def delete_after_delay(msg, delay):
    """Auto-delete message after delay"""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Bot, message: Message):
    user_id = message.from_user.id

    print(f"\n{'='*50}")
    print(f"📨 /start command from user {user_id} ({message.from_user.first_name})")
    print(f"{'='*50}")

    # ✅ STEP 1: CHECK IF USER IS BANNED
    try:
        is_banned = await db.ban_user_exist(user_id)
        if is_banned:
            print(f"🚫 User {user_id} is BANNED")
            return await message.reply_text(
                f"<b>🚫 Yᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜsɪɴɢ ᴛʜɪs ʙᴏᴛ!</b>\n\n"
                f"<b>Cᴏɴᴛᴀᴄᴛ:</b> {BAN_SUPPORT if 'BAN_SUPPORT' in globals() else 'Bot Admin'}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        print(f"⚠️ Error checking ban status: {e}")

    # Check if user is temporarily banned (spam protection)
    if user_id in user_banned_until:
        if datetime.now() < user_banned_until[user_id]:
            print(f"⏳ User {user_id} temporarily banned until {user_banned_until[user_id]}")
            return await message.reply_text(
                "<b><blockquote expandable>You are temporarily banned from using commands due to spamming. Try again later.</blockquote></b>",
                parse_mode=ParseMode.HTML
            )
    
    # ✅ STEP 2: ADD USER TO DATABASE
    try:
        await add_user(user_id)
        print(f"✅ User {user_id} added/verified in database")
    except Exception as e:
        print(f"⚠️ Error adding user to database: {e}")

    # ✅ STEP 3: CHECK FORCE SUBSCRIPTION
    try:
        not_joined_channels = await get_fsub_channels_not_joined(client, user_id)
        
        if not_joined_channels:
            print(f"❌ User {user_id} needs to join {len(not_joined_channels)} channel(s)")
            print(f"   Channels: {[ch['title'] for ch in not_joined_channels]}")
            await show_fsub_panel(client, message, not_joined_channels)
            return
        else:
            print(f"✅ User {user_id} joined all FSub channels (or none configured)")
    except Exception as e:
        print(f"❌ Error checking FSub: {e}")
        import traceback
        traceback.print_exc()

    # ✅ STEP 4: PROCESS START PARAMETER (if any)
    text = message.text
    if len(text) > 7:
        print(f"🔗 Processing start parameter...")
        try:
            base64_string = text.split(" ", 1)[1]
            is_request = base64_string.startswith("req_")
            
            if is_request:
                base64_string = base64_string[4:]
                channel_id = await get_channel_by_encoded_link2(base64_string)
            else:
                channel_id = await get_channel_by_encoded_link(base64_string)
            
            if not channel_id:
                print(f"❌ Invalid encoded link: {base64_string}")
                return await message.reply_text(
                    "<b><blockquote expandable>Invalid or expired invite link.</blockquote></b>",
                    parse_mode=ParseMode.HTML
                )

            print(f"✅ Decoded channel_id: {channel_id}")

            # Check if this is a /genlink link (original_link exists)
            original_link = await get_original_link(channel_id)
            if original_link:
                print(f"🔗 Providing original link: {original_link}")
                button = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("• Proceed to Link •", url=original_link)]]
                )
                return await message.reply_text(
                    "<b><blockquote expandable>ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ</blockquote></b>",
                    reply_markup=button,
                    parse_mode=ParseMode.HTML
                )

            # Use a lock for this channel to prevent concurrent link generation
            async with channel_locks[channel_id]:
                # Check if we already have a valid link
                old_link_info = await get_current_invite_link(channel_id)
                current_time = datetime.now()
                
                # If we have an existing link and it's not expired yet (assuming 5 minutes validity)
                if old_link_info:
                    link_created_time = await get_link_creation_time(channel_id)
                    if link_created_time and (current_time - link_created_time).total_seconds() < 240:  # 4 minutes
                        # Use existing link
                        invite_link = old_link_info["invite_link"]
                        is_request_link = old_link_info["is_request"]
                        print(f"♻️ Reusing existing invite link")
                    else:
                        # Revoke old link and create new one
                        try:
                            await client.revoke_chat_invite_link(channel_id, old_link_info["invite_link"])
                            print(f"🗑️ Revoked old {'request' if old_link_info['is_request'] else 'invite'} link")
                        except Exception as e:
                            print(f"⚠️ Failed to revoke old link: {e}")
                        
                        # Create new link
                        invite = await client.create_chat_invite_link(
                            chat_id=channel_id,
                            expire_date=current_time + timedelta(minutes=10),
                            creates_join_request=is_request
                        )
                        invite_link = invite.invite_link
                        is_request_link = is_request
                        await save_invite_link(channel_id, invite_link, is_request_link)
                        print(f"✅ Created new {'request' if is_request else 'invite'} link")
                else:
                    # Create new link
                    invite = await client.create_chat_invite_link(
                        chat_id=channel_id,
                        expire_date=current_time + timedelta(minutes=10),
                        creates_join_request=is_request
                    )
                    invite_link = invite.invite_link
                    is_request_link = is_request
                    await save_invite_link(channel_id, invite_link, is_request_link)
                    print(f"✅ Created new {'request' if is_request else 'invite'} link")

            button_text = "• ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ •" if is_request_link else "• ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ •"
            button = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=invite_link)]])

            wait_msg = await message.reply_text("⏳", parse_mode=ParseMode.HTML)
            await wait_msg.delete()
            
            await message.reply_text(
                "<b><blockquote expandable>ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ</blockquote></b>",
                reply_markup=button,
                parse_mode=ParseMode.HTML
            )

            note_msg = await message.reply_text(
                "<u><b>Note: If the link is expired, please click the post link again to get a new one.</b></u>",
                parse_mode=ParseMode.HTML
            )

            # Auto-delete the note message after 5 minutes
            asyncio.create_task(delete_after_delay(note_msg, 300))
            asyncio.create_task(revoke_invite_after_5_minutes(client, channel_id, invite_link, is_request_link))

        except Exception as e:
            print(f"❌ Error processing start parameter: {e}")
            import traceback
            traceback.print_exc()
            await message.reply_text(
                "<b><blockquote expandable>Invalid or expired invite link.</blockquote></b>",
                parse_mode=ParseMode.HTML
            )
    else:
        # ✅ STEP 5: SEND WELCOME MESSAGE
        print(f"📬 Sending welcome message to user {user_id}")
        inline_buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
                 InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs", callback_data="channels")],
                [InlineKeyboardButton("• Close •", callback_data="close")]
            ]
        )
        
        try:
            await message.reply_photo(
                photo=START_PIC,
                caption=START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )
            print(f"✅ Welcome message sent successfully")
        except Exception as e:
            print(f"⚠️ Error sending photo, trying text: {e}")
            await message.reply_text(
                START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )


async def get_link_creation_time(channel_id):
    """Get the creation time of the current invite link for a channel."""
    try:
        if IS_POSTGRES:
            from database.database import get_connection
            async with get_connection() as conn:
                result = await conn.fetchval(
                    "SELECT invite_link_created_at FROM channels WHERE channel_id = $1 AND status = 'active'",
                    channel_id
                )
                return result
        else:
            from database.database import channels_collection
            channel = await channels_collection.find_one({"channel_id": channel_id, "status": "active"})
            if channel and "invite_link_created_at" in channel:
                return channel["invite_link_created_at"]
            return None
    except Exception as e:
        print(f"Error fetching link creation time for channel {channel_id}: {e}")
        return None

@Bot.on_callback_query(filters.regex("close"))
async def close_callback(client: Bot, callback_query):
    await callback_query.answer()
    await callback_query.message.delete()
    try:
        await callback_query.message.reply_to_message.delete()
    except:
        pass

@Bot.on_callback_query(filters.regex("check_sub"))
async def check_sub_callback(client: Bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    # Re-check subscription
    not_joined = await get_fsub_channels_not_joined(client, user_id)
    
    if not not_joined:
        await callback_query.message.edit_text(
            "<b>✅ You are subscribed to all required channels! Use /start to proceed.</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await show_fsub_panel(client, callback_query.message, not_joined)

@Bot.on_message(filters.command('status') & filters.private & is_owner_or_admin)
async def info(client: Bot, message: Message):   
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• Close •", callback_data="close")]])
    
    start_time = time.time()
    temp_msg = await message.reply("<b><i>Processing...</i></b>", quote=True, parse_mode=ParseMode.HTML)
    end_time = time.time()
    
    ping_time = (end_time - start_time) * 1000
    
    users = await full_userbase()
    now = datetime.now()
    delta = now - client.uptime
    bottime = get_readable_time(delta.seconds)
    
    await temp_msg.edit(
        f"<b>Users: {len(users)}\n\nUptime: {bottime}\n\nPing: {ping_time:.2f} ms</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Handler for the /cancel command
@Bot.on_message(filters.command('cancel') & filters.private & is_owner_or_admin)
async def cancel_broadcast(client: Bot, message: Message):
    global is_canceled
    async with cancel_lock:
        is_canceled = True
    await message.reply("<b>Broadcast will be canceled...</b>")

@Bot.on_message(filters.private & filters.command('broadcast') & is_owner_or_admin)
async def broadcast(client: Bot, message: Message):
    global is_canceled
    args = message.text.split()[1:]

    if not message.reply_to_message:
        msg = await message.reply(
            "Reply to a message to broadcast.\n\nUsage examples:\n"
            "`/broadcast normal`\n"
            "`/broadcast pin`\n"
            "`/broadcast delete 30`\n"
            "`/broadcast pin delete 30`\n"
            "`/broadcast silent`\n"
        )
        await asyncio.sleep(8)
        return await msg.delete()

    # Defaults
    do_pin = False
    do_delete = False
    duration = 0
    silent = False
    mode_text = []

    i = 0
    while i < len(args):
        arg = args[i].lower()
        if arg == "pin":
            do_pin = True
            mode_text.append("PIN")
        elif arg == "delete":
            do_delete = True
            try:
                duration = int(args[i + 1])
                i += 1
            except (IndexError, ValueError):
                return await message.reply("<b>Provide valid duration for delete mode.</b>\nUsage: `/broadcast delete 30`")
            mode_text.append(f"DELETE({duration}s)")
        elif arg == "silent":
            silent = True
            mode_text.append("SILENT")
        else:
            mode_text.append(arg.upper())
        i += 1

    if not mode_text:
        mode_text.append("NORMAL")

    # Reset cancel flag
    async with cancel_lock:
        is_canceled = False

    query = await full_userbase()
    broadcast_msg = message.reply_to_message
    total = len(query)
    successful = blocked = deleted = unsuccessful = 0

    pls_wait = await message.reply(f"<i>Broadcasting in <b>{' + '.join(mode_text)}</b> mode...</i>")

    bar_length = 20
    progress_bar = ''
    last_update_percentage = 0
    update_interval = 0.05  # 5%

    for i, chat_id in enumerate(query, start=1):
        async with cancel_lock:
            if is_canceled:
                await pls_wait.edit(f"›› BROADCAST ({' + '.join(mode_text)}) CANCELED ❌")
                return

        try:
            sent_msg = await broadcast_msg.copy(chat_id, disable_notification=silent)

            if do_pin:
                await client.pin_chat_message(chat_id, sent_msg.id, both_sides=True)
            if do_delete:
                asyncio.create_task(auto_delete(sent_msg, duration))

            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent_msg = await broadcast_msg.copy(chat_id, disable_notification=silent)
                if do_pin:
                    await client.pin_chat_message(chat_id, sent_msg.id, both_sides=True)
                if do_delete:
                    asyncio.create_task(auto_delete(sent_msg, duration))
                successful += 1
            except:
                unsuccessful += 1
        except UserIsBlocked:
            await del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await del_user(chat_id)
            deleted += 1
        except:
            unsuccessful += 1
            await del_user(chat_id)

        # Progress
        percent_complete = i / total
        if percent_complete - last_update_percentage >= update_interval or last_update_percentage == 0:
            num_blocks = int(percent_complete * bar_length)
            progress_bar = "●" * num_blocks + "○" * (bar_length - num_blocks)
            status_update = f"""<b>›› BROADCAST ({' + '.join(mode_text)}) IN PROGRESS...

<blockquote>⏳:</b> [{progress_bar}] <code>{percent_complete:.0%}</code></blockquote>

<b>›› Total Users: <code>{total}</code>
›› Successful: <code>{successful}</code>
›› Blocked: <code>{blocked}</code>
›› Deleted: <code>{deleted}</code>
›› Unsuccessful: <code>{unsuccessful}</code></b>

<i>➪ To stop broadcasting click: <b>/cancel</b></i>"""
            await pls_wait.edit(status_update)
            last_update_percentage = percent_complete

    # Final status
    final_status = f"""<b>›› BROADCAST ({' + '.join(mode_text)}) COMPLETED ✅

<blockquote>Dᴏɴᴇ:</b> [{progress_bar}] {percent_complete:.0%}</blockquote>

<b>›› Total Users: <code>{total}</code>
›› Successful: <code>{successful}</code>
›› Blocked: <code>{blocked}</code>
›› Deleted: <code>{deleted}</code>
›› Unsuccessful: <code>{unsuccessful}</code></b>"""
    return await pls_wait.edit(final_status)


async def auto_delete(sent_msg, duration):
    """Helper for delete mode"""
    await asyncio.sleep(duration)
    try:
        await sent_msg.delete()
    except:
        pass

@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data  
    
    if data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
    
    elif data == "about":
        user = await client.get_users(OWNER_ID)
        user_link = f"https://t.me/{user.username}" if user.username else f"tg://openmessage?user_id={OWNER_ID}"
        
        try:
            await query.edit_message_media(
                InputMediaPhoto(
                    "https://envs.sh/Wdj.jpg",
                    ABOUT_TXT
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton('ᴄʟᴏsᴇ •', callback_data='close')]
                ]),
            )
        except:
            await query.message.edit_text(
                ABOUT_TXT,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton('ᴄʟᴏsᴇ •', callback_data='close')]
                ]),
                parse_mode=ParseMode.HTML
            )

    elif data == "channels":
        try:
            await query.edit_message_media(
                InputMediaPhoto("https://envs.sh/Wdj.jpg", 
                                CHANNELS_TXT
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton('ᴄʟᴏsᴇ •', callback_data='close')]
                ]),
            )
        except:
            await query.message.edit_text(
                CHANNELS_TXT,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('• ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton('ᴄʟᴏsᴇ •', callback_data='close')]
                ]),
                parse_mode=ParseMode.HTML
            )
    
    elif data in ["start", "home"]:
        inline_buttons = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
                 InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs", callback_data="channels")],
                [InlineKeyboardButton("• Close •", callback_data="close")]
            ]
        )
        try:
            await query.edit_message_media(
                InputMediaPhoto(
                    START_PIC,
                    START_MSG
                ),
                reply_markup=inline_buttons
            )
        except Exception as e:
            print(f"Error sending start/home photo: {e}")
            await query.message.edit_text(
                START_MSG,
                reply_markup=inline_buttons,
                parse_mode=ParseMode.HTML
            )

    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            try:
                mode = await db.get_channel_mode(cid)
            except:
                mode = "off"
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        # Refresh the same channel's mode view
        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
        ]
        await query.message.edit_text(
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                try:
                    mode = await db.get_channel_mode(cid)
                except:
                    mode = "off"
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except:
                continue

        await query.message.edit_text(
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
