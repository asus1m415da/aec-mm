import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
from flask import Flask
from threading import Thread

# Importaciones del Monitor
import requests
from fake_useragent import UserAgent
import random
import time

# ==============================================================================
# 🌐 SERVIDOR WEB (Keep Alive)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "Galaxy Bot + Monitor S23 Ultra Online 🚀"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==============================================================================
# ⚙️ CONFIGURACIÓN Y CONSTANTES
# ==============================================================================
load_dotenv()

class Config:
    # --- Discord & IA ---
    TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_KEY = os.getenv("GROQ_API_KEY")
    
    # --- IDs del Servidor ---
    try:
        GUILD_ID = int(os.getenv("GUILD_ID", 0))
        CONFESSION_CH_ID = int(os.getenv("CONFESSION_CHANNEL_ID", 0))
        LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
        MM_ROLE_ID = int(os.getenv("MM_ROLE_ID", 0))
        MOD_ROLE_ID = int(os.getenv("MODERATOR_ROLE_ID", 0))
    except ValueError:
        print("❌ ERROR: Revisa los IDs en tu .env")
        exit()

    # --- Configuración del Monitor S23 ---
    MONITOR_ADMIN_ID = 793224680231665674 # Tu ID
    STORE_URL = "https://www.reuse.pe"
    MODELOS = ["S23 Ultra"]
    INTERVALO_MONITOR = 300 # Segundos (5 min)
    USERS_FILE = "usuarios_notificacion.json"

class Colors:
    GALAXY = 0x6A0DAD
    SUCCESS = 0x43B581
    ERROR = 0xF04747
    WARNING = 0xFAA61A
    DARK = 0x2B2D31
    BAN = 0x000000
    MM = 0x5865F2

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# ==============================================================================
# 💾 GESTOR DE DATOS (Confesiones & Usuarios Monitor)
# ==============================================================================
class DataManager:
    @staticmethod
    def _check_files():
        if not os.path.exists("count.json"):
            with open("count.json", "w") as f: json.dump({"count": 1}, f)
        if not os.path.exists("blacklist.json"):
            with open("blacklist.json", "w") as f: json.dump({"banned": []}, f)
        if not os.path.exists(Config.USERS_FILE):
             with open(Config.USERS_FILE, "w") as f: json.dump({"usuarios": [Config.MONITOR_ADMIN_ID]}, f)

    @staticmethod
    def get_next_id():
        DataManager._check_files()
        with open("count.json", "r") as f: data = json.load(f)
        new_count = data.get("count", 1)
        with open("count.json", "w") as f: json.dump({"count": new_count + 1}, f)
        return new_count

    @staticmethod
    def is_banned(user_id):
        DataManager._check_files()
        with open("blacklist.json", "r") as f: return user_id in json.load(f).get("banned", [])

    @staticmethod
    def ban_user(user_id):
        DataManager._check_files()
        with open("blacklist.json", "r+") as f:
            data = json.load(f)
            if user_id not in data["banned"]:
                data["banned"].append(user_id)
                f.seek(0); json.dump(data, f); f.truncate()
    
    @staticmethod
    def get_monitor_users():
        DataManager._check_files()
        try:
            with open(Config.USERS_FILE, "r") as f:
                return json.load(f).get("usuarios", [])
        except: return [Config.MONITOR_ADMIN_ID]

# ==============================================================================
# 🕵️ LÓGICA DE SCRAPING (MONITOR S23)
# ==============================================================================
# Inicializamos sesión global para el scraper
scraper_session = requests.Session()
ua = UserAgent()

def obtener_headers_stealth():
    return {
        'User-Agent': ua.random,
        'Accept': 'application/json',
        'Referer': 'https://www.reuse.pe/',
        'Origin': 'https://www.reuse.pe',
        'X-Requested-With': 'XMLHttpRequest'
    }

def fetch_con_reintentos(url):
    reintentos = 3
    for i in range(reintentos):
        try:
            response = scraper_session.get(url, headers=obtener_headers_stealth(), timeout=15)
            if response.status_code == 200: return response.json()
            elif response.status_code in [403, 429]:
                print(f"⚠️ Bloqueo detectado ({response.status_code}). Esperando...")
                time.sleep(5 * (i + 1)) # Sleep seguro porque corre en hilo aparte
        except Exception as e:
            print(f"❌ Error conectando: {e}")
            time.sleep(5)
    return None

def ejecutar_scraping():
    """Esta función corre todo el proceso pesado de scraping"""
    todos_los_productos = []
    
    # ESTRATEGIA A: Paginación
    page = 1
    exito_A = False
    while page <= 5:
        url = f"{Config.STORE_URL}/products.json?limit=250&page={page}"
        data = fetch_con_reintentos(url)
        if data and 'products' in data and len(data['products']) > 0:
            todos_los_productos.extend(data['products'])
            exito_A = True
            if len(data['products']) < 250: break
            page += 1
        else:
            break
            
    # ESTRATEGIA B: Backup
    if not exito_A or len(todos_los_productos) == 0:
        url_backup = f"{Config.STORE_URL}/collections/all/products.json?limit=1000"
        data = fetch_con_reintentos(url_backup)
        if data and 'products' in data:
            todos_los_productos.extend(data['products'])

    # Filtrado
    dispositivos = []
    seen = set()
    for producto in todos_los_productos:
        if producto['id'] in seen: continue
        seen.add(producto['id'])
        
        titulo = producto.get('title', '')
        match = any(m.lower() in titulo.lower() for m in Config.MODELOS)
        
        if match:
            variants = producto.get('variants', [])
            for v in variants:
                if v.get('available', False):
                    dispositivos.append({
                        "titulo": f"{titulo} ({v.get('title', 'Único')})",
                        "precio": f"S/ {v.get('price', '0')}",
                        "link": f"{Config.STORE_URL}/products/{producto['handle']}"
                    })
                    break 
    return dispositivos

# ==============================================================================
# 🧠 INTELIGENCIA ARTIFICIAL
# ==============================================================================
async def get_ai_joke():
    if not Config.GROQ_KEY: return "⚠️ API Key no configurada."
    try:
        client = Groq(api_key=Config.GROQ_KEY)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Di una frase corta, ingeniosa y graciosa,evita ser deprimido o opaco, eres bien feliz y dar chistes felices y positivos en español,bueno eres un poco deprimido y te quejas de ls vida de toda manera."}],
            temperature=1.23, max_tokens=142
        )
        return response.choices[0].message.content.strip()
    except: return "La IA está durmiendo... 😴"
        
# ==============================================================================
# 🧩 COMPONENTES DE INTERFAZ (CONFESIONES)
# ==============================================================================
class PersistentConfessionButton(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Enviar Confesión Anónima", style=discord.ButtonStyle.primary, emoji="📩", custom_id="persistent_confess_btn")
    async def open_confession_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if DataManager.is_banned(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(title="⛔", description="Estás baneado.", color=Colors.BAN), ephemeral=True)
        await interaction.response.send_modal(ConfessionModal())

class ConfessionModal(discord.ui.Modal, title="🤫 Tu Secreto"):
    text_input = discord.ui.TextInput(label="Confesión", style=discord.TextStyle.paragraph, min_length=5, max_length=3500)
    img_input = discord.ui.TextInput(label="URL Imagen (Opcional)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        conf_id = DataManager.get_next_id()
        log_channel = interaction.guild.get_channel(Config.LOG_CH_ID)
        
        embed = discord.Embed(description=f"📄 **Contenido:**\n{self.text_input.value}", color=Colors.WARNING, timestamp=datetime.now())
        embed.set_author(name=f"Expediente #{conf_id}", icon_url=interaction.user.display_avatar.url)
        if self.img_input.value: embed.set_image(url=self.img_input.value)
        
        view = AdminControlPanel(self.text_input.value, self.img_input.value, interaction.user, conf_id)
        if log_channel: await log_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Confesión #{conf_id} enviada.", ephemeral=True)

class AdminControlPanel(discord.ui.View):
    def __init__(self, content, image, author, conf_id):
        super().__init__(timeout=None)
        self.content = content; self.image = image; self.author = author; self.conf_id = conf_id

    async def interaction_check(self, interaction):
        if not interaction.user.get_role(Config.MOD_ROLE_ID):
            await interaction.response.send_message("🔒 Solo moderadores.", ephemeral=True); return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, emoji="✅", custom_id="adm_approve")
    async def approve(self, interaction, button):
        ch = interaction.guild.get_channel(Config.CONFESSION_CH_ID)
        embed = discord.Embed(description=self.content, color=Colors.DARK, timestamp=datetime.now())
        embed.set_author(name=f"Confesión #{self.conf_id}", icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png")
        if self.image: embed.set_image(url=self.image)
        embed.set_footer(text="A.E.C MM")
        await ch.send(embed=embed, view=PersistentConfessionButton())
        await interaction.message.delete() # Borra el log para limpieza o edítalo como antes
        await interaction.response.send_message("✅ Publicado.", ephemeral=True)

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="adm_deny")
    async def deny(self, interaction, button):
        await interaction.message.delete()
        await interaction.response.send_message("🗑️ Rechazado.", ephemeral=True)

# ==============================================================================
# 🤖 CLASE PRINCIPAL DEL BOT (FUSIÓN)
# ==============================================================================

class GalaxyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="$", help_command=None, intents=intents)

    async def setup_hook(self):
        # 1. Botón Confesiones
        self.add_view(PersistentConfessionButton())
        # 2. Iniciar Tarea de Monitoreo
        self.monitor_task.start()
        print("✅ Sistemas (Botones + Monitor) iniciados.")

    async def on_ready(self):
        print(f"🚀 {self.user} está en línea | S23 Monitor Activo")
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} comandos Slash sincronizados.")
        except Exception as e:
            print(e)

    # --- TAREA DE MONITOREO EN BUCLE ---
    @tasks.loop(seconds=Config.INTERVALO_MONITOR)
    async def monitor_task(self):
        print(f"🔍 [Monitor] Buscando {Config.MODELOS}...")
        
        # IMPORTANTE: Ejecutar scraping en un hilo aparte para no congelar el bot
        try:
            dispositivos = await asyncio.to_thread(ejecutar_scraping)
            
            if dispositivos:
                print(f"🎯 ¡{len(dispositivos)} S23 ENCONTRADOS!")
                users = DataManager.get_monitor_users()
                
                for user_id in users:
                    try:
                        user = await self.fetch_user(user_id)
                        embed = discord.Embed(title="🚨 ¡STOCK S23 ULTRA! 🚨", color=discord.Color.green())
                        for d in dispositivos[:5]:
                            embed.add_field(name=d['titulo'], value=f"💰 **{d['precio']}**\n[Link]({d['link']})", inline=False)
                        await user.send(embed=embed)
                    except Exception as e:
                        print(f"❌ No se pudo enviar DM a {user_id}: {e}")
            else:
                print("💤 [Monitor] Sin stock.")
                
        except Exception as e:
            print(f"❌ Error en Loop Monitor: {e}")

    @monitor_task.before_loop
    async def before_monitor(self):
        await self.wait_until_ready()

bot = GalaxyBot()

# ==============================================================================
# 🚀 COMANDOS (MODERACIÓN + UTILS)
# ==============================================================================

@bot.tree.command(name="monitor_status", description="📊 Ver estado del monitor S23")
async def monitor_status(interaction: discord.Interaction):
    embed = discord.Embed(title="📊 Estado Monitor S23", color=Colors.MM)
    embed.add_field(name="Objetivo", value=str(Config.MODELOS), inline=False)
    embed.add_field(name="Intervalo", value=f"{Config.INTERVALO_MONITOR} seg", inline=True)
    embed.add_field(name="Estado", value="🟢 Corriendo en segundo plano", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="add")
async def add_middleman(ctx, *, arg=None):
    if not ctx.author.get_role(Config.MM_ROLE_ID): return
    if not arg: return await ctx.send("⚠️ Uso: `$add @usuario`")
    user = ctx.message.mentions[0] if ctx.message.mentions else ctx.guild.get_member(int(arg)) if arg.isdigit() else None
    if user:
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True)
        await ctx.send(embed=discord.Embed(description=f"✅ {user.mention} añadido.", color=Colors.MM))
        await ctx.send(f"🤖 **AI:** {await get_ai_joke()}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="🌌 Confesiones", description="Envía tu secreto anónimamente con el botón.", color=Colors.GALAXY)
    await ctx.send(embed=embed, view=PersistentConfessionButton())

# ==============================================================================
# 🔥 EJECUCIÓN
# ==============================================================================
if __name__ == "__main__":
    keep_alive()
    bot.run(Config.TOKEN)
    
