"""
Universal Database Adapter
Supports both MongoDB and PostgreSQL (Neon) using the same DB_URI variable
Automatically detects database type from connection string
"""

import asyncio
import asyncpg
import os
from typing import List, Optional
from datetime import datetime, timedelta
import base64
from config import DB_URI, DB_NAME
import re

# Pattern for validating IDs
id_pattern = re.compile(r'^-?\d+$')

# Detect database type from connection string
IS_POSTGRES = DB_URI.startswith('postgresql://') or DB_URI.startswith('postgres://')
IS_MONGODB = DB_URI.startswith('mongodb://') or DB_URI.startswith('mongodb+srv://')

# Initialize database connections based on type
if IS_POSTGRES:
    print("🐘 Using PostgreSQL (Neon) database")
    import asyncpg
    from contextlib import asynccontextmanager
    
    # PostgreSQL connection pool
    _pg_pool = None
    
    async def init_postgres():
        """Initialize PostgreSQL connection pool"""
        global _pg_pool
        if _pg_pool is None:
            _pg_pool = await asyncpg.create_pool(
                DB_URI,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            await create_tables()
        return _pg_pool
    
    async def create_tables():
        """Create PostgreSQL tables if they don't exist"""
        pool = await init_postgres()
        async with pool.acquire() as conn:
            # Users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Channels table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id BIGINT PRIMARY KEY,
                    encoded_link TEXT,
                    req_encoded_link TEXT,
                    current_invite_link TEXT,
                    is_request_link BOOLEAN DEFAULT FALSE,
                    invite_link_created_at TIMESTAMP,
                    original_link TEXT,
                    approval_off BOOLEAN DEFAULT FALSE,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Admins table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY
                )
            ''')
            
            # FSub channels table - WITH MODE COLUMN
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS fsub_channels (
                    channel_id BIGINT PRIMARY KEY,
                    mode TEXT DEFAULT 'off',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Banned users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id BIGINT PRIMARY KEY,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Request FSub table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS request_fsub (
                    channel_id BIGINT,
                    user_id BIGINT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (channel_id, user_id)
                )
            ''')
        print("✅ PostgreSQL tables created/verified")
    
    @asynccontextmanager
    async def get_connection():
        """Get PostgreSQL connection from pool"""
        pool = await init_postgres()
        async with pool.acquire() as conn:
            yield conn

elif IS_MONGODB:
    print("🍃 Using MongoDB database")
    import motor.motor_asyncio
    
    dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
    database = dbclient[DB_NAME]
    
    # Collections
    user_data = database['users']
    channels_collection = database['channels']
    admins_collection = database['admins']
    fsub_channels_collection = database['fsub_channels']
    banned_users_collection = database['banned_users']
    request_fsub_collection = database['request_fsub']

else:
    raise ValueError(f"Invalid DB_URI: '{DB_URI}'. Must start with 'mongodb://', 'mongodb+srv://', or 'postgresql://'")


# ============================================
# DATABASE CLASS (For compatibility with existing code)
# ============================================

class Database:
    def __init__(self):
        if IS_MONGODB:
            self.user_data = user_data
            self.channels_data = channels_collection
            self.admins_data = admins_collection
            self.fsub_data = fsub_channels_collection
            self.banned_user_data = banned_users_collection
            self.rqst_fsub_Channel_data = request_fsub_collection
    
    # ============================================
    # BAN USER MANAGEMENT
    # ============================================
    
    async def ban_user_exist(self, user_id: int):
        """Check if user is banned"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM banned_users WHERE user_id = $1)',
                    user_id
                )
                return result
        else:
            found = await self.banned_user_data.find_one({'_id': user_id})
            return bool(found)

    async def add_ban_user(self, user_id: int):
        """Ban a user"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                try:
                    await conn.execute(
                        'INSERT INTO banned_users (user_id) VALUES ($1)',
                        user_id
                    )
                except asyncpg.UniqueViolationError:
                    pass
        else:
            if not await self.ban_user_exist(user_id):
                await self.banned_user_data.insert_one({'_id': user_id})

    async def del_ban_user(self, user_id: int):
        """Unban a user"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute(
                    'DELETE FROM banned_users WHERE user_id = $1',
                    user_id
                )
        else:
            if await self.ban_user_exist(user_id):
                await self.banned_user_data.delete_one({'_id': user_id})

    async def get_ban_users(self):
        """Get all banned user IDs"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                rows = await conn.fetch('SELECT user_id FROM banned_users')
                return [row['user_id'] for row in rows]
        else:
            users_docs = await self.banned_user_data.find().to_list(length=None)
            user_ids = [doc['_id'] for doc in users_docs]
            return user_ids
    
    async def get_all_admins(self):
        """Get all admin user IDs"""
        return await list_admins()

    # ============================================
    # FORCE SUBSCRIBE CHANNEL MANAGEMENT
    # ============================================
    
    async def channel_exist(self, channel_id: int):
        """Check if channel exists in force-sub list"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM fsub_channels WHERE channel_id = $1)',
                    channel_id
                )
                return result
        else:
            found = await self.fsub_data.find_one({'_id': channel_id})
            return bool(found)

    async def add_channel(self, channel_id: int):
        """Add channel to force-sub list"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                try:
                    await conn.execute(
                        'INSERT INTO fsub_channels (channel_id, mode) VALUES ($1, $2)',
                        channel_id, 'off'
                    )
                except asyncpg.UniqueViolationError:
                    pass
        else:
            if not await self.channel_exist(channel_id):
                await self.fsub_data.insert_one({'_id': channel_id, 'mode': 'off'})

    async def rem_channel(self, channel_id: int):
        """Remove channel from force-sub list"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute(
                    'DELETE FROM fsub_channels WHERE channel_id = $1',
                    channel_id
                )
        else:
            if await self.channel_exist(channel_id):
                await self.fsub_data.delete_one({'_id': channel_id})
    
    # Alias for compatibility
    async def del_channel(self, channel_id: int):
        """Alias for rem_channel"""
        return await self.rem_channel(channel_id)

    async def show_channels(self):
        """Get all force-sub channel IDs"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                rows = await conn.fetch('SELECT channel_id FROM fsub_channels')
                return [row['channel_id'] for row in rows]
        else:
            channel_docs = await self.fsub_data.find().to_list(length=None)
            channel_ids = [doc['_id'] for doc in channel_docs]
            return channel_ids

    async def get_channel_mode(self, channel_id: int):
        """Get current mode of a channel"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT mode FROM fsub_channels WHERE channel_id = $1',
                    channel_id
                )
                return result if result else "off"
        else:
            data = await self.fsub_data.find_one({'_id': channel_id})
            return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        """Set mode of a channel"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute('''
                    INSERT INTO fsub_channels (channel_id, mode)
                    VALUES ($1, $2)
                    ON CONFLICT (channel_id) DO UPDATE
                    SET mode = $2
                ''', channel_id, mode)
        else:
            await self.fsub_data.update_one(
                {'_id': channel_id},
                {'$set': {'mode': mode}},
                upsert=True
            )

    # ============================================
    # REQUEST FORCE-SUB MANAGEMENT
    # ============================================
    
    async def req_user(self, channel_id: int, user_id: int):
        """Add user to channel's join request list"""
        try:
            if IS_POSTGRES:
                async with get_connection() as conn:
                    try:
                        await conn.execute(
                            'INSERT INTO request_fsub (channel_id, user_id) VALUES ($1, $2)',
                            channel_id, user_id
                        )
                    except asyncpg.UniqueViolationError:
                        pass
            else:
                await self.rqst_fsub_Channel_data.update_one(
                    {'_id': int(channel_id)},
                    {'$addToSet': {'user_ids': int(user_id)}},
                    upsert=True
                )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user to request list: {e}")

    async def del_req_user(self, channel_id: int, user_id: int):
        """Remove user from channel's join request list"""
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute(
                    'DELETE FROM request_fsub WHERE channel_id = $1 AND user_id = $2',
                    channel_id, user_id
                )
        else:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': channel_id}, 
                {'$pull': {'user_ids': user_id}}
            )

    async def req_user_exist(self, channel_id: int, user_id: int):
        """Check if user exists in channel's join request list"""
        try:
            if IS_POSTGRES:
                async with get_connection() as conn:
                    result = await conn.fetchval(
                        'SELECT EXISTS(SELECT 1 FROM request_fsub WHERE channel_id = $1 AND user_id = $2)',
                        channel_id, user_id
                    )
                    return result
            else:
                found = await self.rqst_fsub_Channel_data.find_one({
                    '_id': int(channel_id),
                    'user_ids': int(user_id)
                })
                return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request list: {e}")
            return False

    async def reqChannel_exist(self, channel_id: int):
        """Check if channel exists in force-sub list"""
        channel_ids = await self.show_channels()
        return channel_id in channel_ids


# Create global db instance
db = Database()


# ============================================================================
# UNIFIED DATABASE FUNCTIONS (Work with both MongoDB and PostgreSQL)
# ============================================================================

async def add_user(user_id: int) -> bool:
    """Add a user to the database if they don't exist."""
    if not isinstance(user_id, int) or user_id <= 0:
        print(f"Invalid user_id: {user_id}")
        return False
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                try:
                    await conn.execute(
                        'INSERT INTO users (user_id, created_at) VALUES ($1, $2)',
                        user_id, datetime.utcnow()
                    )
                    return True
                except asyncpg.UniqueViolationError:
                    return False
        else:  # MongoDB
            existing_user = await user_data.find_one({'_id': user_id})
            if existing_user:
                return False
            await user_data.insert_one({'_id': user_id, 'created_at': datetime.utcnow()})
            return True
    except Exception as e:
        print(f"Error adding user {user_id}: {e}")
        return False

async def present_user(user_id: int) -> bool:
    """Check if a user exists in the database."""
    if not isinstance(user_id, int):
        return False
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)',
                    user_id
                )
                return result
        else:  # MongoDB
            return bool(await user_data.find_one({'_id': user_id}))
    except Exception as e:
        print(f"Error checking user {user_id}: {e}")
        return False

async def full_userbase() -> List[int]:
    """Get all user IDs from the database."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                rows = await conn.fetch('SELECT user_id FROM users')
                return [row['user_id'] for row in rows]
        else:  # MongoDB
            user_docs = user_data.find()
            return [doc['_id'] async for doc in user_docs]
    except Exception as e:
        print(f"Error fetching userbase: {e}")
        return []

async def del_user(user_id: int) -> bool:
    """Delete a user from the database."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.execute(
                    'DELETE FROM users WHERE user_id = $1',
                    user_id
                )
                return result != 'DELETE 0'
        else:  # MongoDB
            result = await user_data.delete_one({'_id': user_id})
            return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting user {user_id}: {e}")
        return False

async def is_admin(user_id: int) -> bool:
    """Check if a user is an admin."""
    try:
        user_id = int(user_id)
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM admins WHERE user_id = $1)',
                    user_id
                )
                return result
        else:  # MongoDB
            return bool(await admins_collection.find_one({'_id': user_id}))
    except Exception as e:
        print(f"Error checking admin status for {user_id}: {e}")
        return False

async def add_admin(user_id: int) -> bool:
    """Add a user as admin."""
    try:
        user_id = int(user_id)
        if IS_POSTGRES:
            async with get_connection() as conn:
                try:
                    await conn.execute(
                        'INSERT INTO admins (user_id) VALUES ($1)',
                        user_id
                    )
                    return True
                except asyncpg.UniqueViolationError:
                    return False
        else:  # MongoDB
            await admins_collection.update_one(
                {'_id': user_id},
                {'$set': {'_id': user_id}},
                upsert=True
            )
            return True
    except Exception as e:
        print(f"Error adding admin {user_id}: {e}")
        return False

async def remove_admin(user_id: int) -> bool:
    """Remove a user from admins."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.execute(
                    'DELETE FROM admins WHERE user_id = $1',
                    user_id
                )
                return result != 'DELETE 0'
        else:  # MongoDB
            result = await admins_collection.delete_one({'_id': user_id})
            return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing admin {user_id}: {e}")
        return False

async def list_admins() -> list:
    """List all admin user IDs."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                rows = await conn.fetch('SELECT user_id FROM admins')
                return [row['user_id'] for row in rows]
        else:  # MongoDB
            admins = await admins_collection.find().to_list(None)
            return [admin['_id'] for admin in admins]
    except Exception as e:
        print(f"Error listing admins: {e}")
        return []

async def save_channel(channel_id: int) -> bool:
    """Save a channel to the database."""
    if not isinstance(channel_id, int):
        print(f"Invalid channel_id: {channel_id}")
        return False
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute('''
                    INSERT INTO channels (channel_id, status, created_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (channel_id) DO UPDATE
                    SET updated_at = $3
                ''', channel_id, 'active', datetime.utcnow())
        else:  # MongoDB
            await channels_collection.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "channel_id": channel_id,
                        "invite_link_expiry": None,
                        "created_at": datetime.utcnow(),
                        "status": "active"
                    }
                },
                upsert=True
            )
        return True
    except Exception as e:
        print(f"Error saving channel {channel_id}: {e}")
        return False

async def get_channels() -> List[int]:
    """Get all active channel IDs from the database."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                rows = await conn.fetch(
                    "SELECT channel_id FROM channels WHERE status = 'active'"
                )
                return [row['channel_id'] for row in rows]
        else:  # MongoDB
            channels = await channels_collection.find({"status": "active"}).to_list(None)
            valid_channels = []
            for channel in channels:
                if isinstance(channel, dict) and "channel_id" in channel:
                    valid_channels.append(channel["channel_id"])
            return valid_channels
    except Exception as e:
        print(f"Error fetching channels: {e}")
        return []

async def delete_channel(channel_id: int) -> bool:
    """Delete a channel from the database."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.execute(
                    'DELETE FROM channels WHERE channel_id = $1',
                    channel_id
                )
                return result != 'DELETE 0'
        else:  # MongoDB
            result = await channels_collection.delete_one({"channel_id": channel_id})
            return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting channel {channel_id}: {e}")
        return False

async def save_encoded_link(channel_id: int) -> Optional[str]:
    """Save an encoded link for a channel and return it."""
    if not isinstance(channel_id, int):
        print(f"Invalid channel_id: {channel_id}")
        return None
    
    try:
        encoded_link = base64.urlsafe_b64encode(str(channel_id).encode()).decode()
        
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute('''
                    INSERT INTO channels (channel_id, encoded_link, status, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (channel_id) DO UPDATE
                    SET encoded_link = $2, status = $3, updated_at = $4
                ''', channel_id, encoded_link, 'active', datetime.utcnow())
        else:  # MongoDB
            await channels_collection.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "encoded_link": encoded_link,
                        "status": "active",
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        return encoded_link
    except Exception as e:
        print(f"Error saving encoded link for channel {channel_id}: {e}")
        return None

async def get_channel_by_encoded_link(encoded_link: str) -> Optional[int]:
    """Get a channel ID by its encoded link."""
    if not isinstance(encoded_link, str):
        return None
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    "SELECT channel_id FROM channels WHERE encoded_link = $1 AND status = 'active'",
                    encoded_link
                )
                return result
        else:  # MongoDB
            channel = await channels_collection.find_one({"encoded_link": encoded_link, "status": "active"})
            return channel["channel_id"] if channel and "channel_id" in channel else None
    except Exception as e:
        print(f"Error fetching channel by encoded link {encoded_link}: {e}")
        return None

async def save_encoded_link2(channel_id: int, encoded_link: str) -> Optional[str]:
    """Save a secondary encoded link for a channel."""
    if not isinstance(channel_id, int) or not isinstance(encoded_link, str):
        print(f"Invalid input: channel_id={channel_id}, encoded_link={encoded_link}")
        return None
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute('''
                    INSERT INTO channels (channel_id, req_encoded_link, status, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (channel_id) DO UPDATE
                    SET req_encoded_link = $2, status = $3, updated_at = $4
                ''', channel_id, encoded_link, 'active', datetime.utcnow())
        else:  # MongoDB
            await channels_collection.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "req_encoded_link": encoded_link,
                        "status": "active",
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        return encoded_link
    except Exception as e:
        print(f"Error saving secondary encoded link for channel {channel_id}: {e}")
        return None

async def get_channel_by_encoded_link2(encoded_link: str) -> Optional[int]:
    """Get a channel ID by its secondary encoded link."""
    if not isinstance(encoded_link, str):
        return None
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    "SELECT channel_id FROM channels WHERE req_encoded_link = $1 AND status = 'active'",
                    encoded_link
                )
                return result
        else:  # MongoDB
            channel = await channels_collection.find_one({"req_encoded_link": encoded_link, "status": "active"})
            return channel["channel_id"] if channel and "channel_id" in channel else None
    except Exception as e:
        print(f"Error fetching channel by secondary encoded link {encoded_link}: {e}")
        return None

async def save_invite_link(channel_id: int, invite_link: str, is_request: bool) -> bool:
    """Save the current invite link for a channel and its type."""
    if not isinstance(channel_id, int) or not isinstance(invite_link, str):
        print(f"Invalid input: channel_id={channel_id}, invite_link={invite_link}")
        return False
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute('''
                    INSERT INTO channels (channel_id, current_invite_link, is_request_link, 
                                         invite_link_created_at, status)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (channel_id) DO UPDATE
                    SET current_invite_link = $2, is_request_link = $3, 
                        invite_link_created_at = $4, status = $5
                ''', channel_id, invite_link, is_request, datetime.utcnow(), 'active')
        else:  # MongoDB
            await channels_collection.update_one(
                {"channel_id": channel_id},
                {
                    "$set": {
                        "current_invite_link": invite_link,
                        "is_request_link": is_request,
                        "invite_link_created_at": datetime.utcnow(),
                        "status": "active"
                    }
                },
                upsert=True
            )
        return True
    except Exception as e:
        print(f"Error saving invite link for channel {channel_id}: {e}")
        return False

async def get_current_invite_link(channel_id: int) -> Optional[dict]:
    """Get the current invite link and its type for a channel."""
    if not isinstance(channel_id, int):
        return None
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT current_invite_link, is_request_link FROM channels WHERE channel_id = $1 AND status = 'active'",
                    channel_id
                )
                if row and row['current_invite_link']:
                    return {
                        "invite_link": row['current_invite_link'],
                        "is_request": row['is_request_link'] or False
                    }
                return None
        else:  # MongoDB
            channel = await channels_collection.find_one({"channel_id": channel_id, "status": "active"})
            if channel and "current_invite_link" in channel:
                return {
                    "invite_link": channel["current_invite_link"],
                    "is_request": channel.get("is_request_link", False)
                }
            return None
    except Exception as e:
        print(f"Error fetching current invite link for channel {channel_id}: {e}")
        return None

async def get_link_creation_time(channel_id: int):
    """Get the creation time of the current invite link for a channel."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    "SELECT invite_link_created_at FROM channels WHERE channel_id = $1 AND status = 'active'",
                    channel_id
                )
                return result
        else:  # MongoDB
            channel = await channels_collection.find_one({"channel_id": channel_id, "status": "active"})
            if channel and "invite_link_created_at" in channel:
                return channel["invite_link_created_at"]
            return None
    except Exception as e:
        print(f"Error fetching link creation time for channel {channel_id}: {e}")
        return None

async def add_fsub_channel(channel_id: int) -> bool:
    """Add a channel to the FSub list."""
    if not isinstance(channel_id, int):
        print(f"Invalid channel_id: {channel_id}")
        return False
    
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                try:
                    await conn.execute(
                        'INSERT INTO fsub_channels (channel_id, mode, status, created_at) VALUES ($1, $2, $3, $4)',
                        channel_id, 'off', 'active', datetime.utcnow()
                    )
                    return True
                except asyncpg.UniqueViolationError:
                    return False
        else:  # MongoDB
            existing_channel = await fsub_channels_collection.find_one({'channel_id': channel_id})
            if existing_channel:
                return False
            await fsub_channels_collection.insert_one({
                'channel_id': channel_id,
                'mode': 'off',
                'created_at': datetime.utcnow(),
                'status': 'active'
            })
            return True
    except Exception as e:
        print(f"Error adding FSub channel {channel_id}: {e}")
        return False

async def remove_fsub_channel(channel_id: int) -> bool:
    """Remove a channel from the FSub list."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.execute(
                    'DELETE FROM fsub_channels WHERE channel_id = $1',
                    channel_id
                )
                return result != 'DELETE 0'
        else:  # MongoDB
            result = await fsub_channels_collection.delete_one({'channel_id': channel_id})
            return result.deleted_count > 0
    except Exception as e:
        print(f"Error removing FSub channel {channel_id}: {e}")
        return False

async def get_fsub_channels() -> List[int]:
    """Get all active FSub channel IDs."""
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                rows = await conn.fetch(
                    "SELECT channel_id FROM fsub_channels WHERE status = 'active'"
                )
                return [row['channel_id'] for row in rows]
        else:  # MongoDB
            channels = await fsub_channels_collection.find({'status': 'active'}).to_list(None)
            return [channel['channel_id'] for channel in channels]
    except Exception as e:
        print(f"Error fetching FSub channels: {e}")
        return []

async def get_original_link(channel_id: int) -> Optional[str]:
    """Get the original link stored for a channel (used by /genlink)."""
    if not isinstance(channel_id, int):
        return None
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    "SELECT original_link FROM channels WHERE channel_id = $1 AND status = 'active'",
                    channel_id
                )
                return result
        else:  # MongoDB
            channel = await channels_collection.find_one({"channel_id": channel_id, "status": "active"})
            return channel.get("original_link") if channel and "original_link" in channel else None
    except Exception as e:
        print(f"Error fetching original link for channel {channel_id}: {e}")
        return None

async def set_approval_off(channel_id: int, off: bool = True) -> bool:
    """Set approval_off flag for a channel."""
    if not isinstance(channel_id, int):
        print(f"Invalid channel_id: {channel_id}")
        return False
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                await conn.execute('''
                    INSERT INTO channels (channel_id, approval_off)
                    VALUES ($1, $2)
                    ON CONFLICT (channel_id) DO UPDATE
                    SET approval_off = $2
                ''', channel_id, off)
        else:  # MongoDB
            await channels_collection.update_one(
                {"channel_id": channel_id},
                {"$set": {"approval_off": off}},
                upsert=True
            )
        return True
    except Exception as e:
        print(f"Error setting approval_off for channel {channel_id}: {e}")
        return False

async def is_approval_off(channel_id: int) -> bool:
    """Check if approval_off flag is set for a channel."""
    if not isinstance(channel_id, int):
        return False
    try:
        if IS_POSTGRES:
            async with get_connection() as conn:
                result = await conn.fetchval(
                    'SELECT approval_off FROM channels WHERE channel_id = $1',
                    channel_id
                )
                return bool(result)
        else:  # MongoDB
            channel = await channels_collection.find_one({"channel_id": channel_id})
            return bool(channel and channel.get("approval_off", False))
    except Exception as e:
        print(f"Error checking approval_off for channel {channel_id}: {e}")
        return False

async def migrate_database():
    """Add missing 'mode' column to fsub_channels table"""
    
    if not DB_URI:
        print("❌ Error: DB_URI environment variable not set")
        return False
    
    print("🔧 Starting database migration...")
    print(f"📊 Database: PostgreSQL (Neon)")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DB_URI)
        print("✅ Connected to database")
        
        # Check if mode column exists
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'fsub_channels' 
            AND column_name = 'mode'
        """
        
        result = await conn.fetchval(check_query)
        
        if result:
            print("✅ Column 'mode' already exists in fsub_channels table")
        else:
            print("📝 Adding 'mode' column to fsub_channels table...")
            
            # Add mode column with default value 'off'
            alter_query = """
                ALTER TABLE fsub_channels 
                ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'off'
            """
            
            await conn.execute(alter_query)
            print("✅ Column 'mode' added successfully")
        
        # Verify the column exists now
        verify_query = """
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name = 'fsub_channels'
            ORDER BY ordinal_position
        """
        
        columns = await conn.fetch(verify_query)
        
        print("\n📋 Current fsub_channels table structure:")
        print("=" * 60)
        for col in columns:
            default = col['column_default'] or 'NULL'
            print(f"  {col['column_name']:20} | {col['data_type']:15} | {default}")
        print("=" * 60)
        
        await conn.close()
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
