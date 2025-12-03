import discord
from discord.ext import commands
import os
import re
import json
import asyncio
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime

# ==========================================
# 🛠️ CONFIGURACIÓN Y CONSTANTES
# ==========================================

load_dotenv()

# Credenciales
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# IDs del Servidor
try:
    GUILD_ID = int(os.getenv("GUILD_ID"))
    CONFESSION_CHANNEL_ID = int(os.getenv("CONFESSION_CHANNEL_ID"))
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
    MM_ROLE_ID = int(os.getenv("MM_ROLE_ID"))           # Rol para $add
    MODERATOR_ROLE_ID = int(os.getenv("MODERATOR_ROLE_ID")) # Rol para Logs
except (TypeError, ValueError):
    print("❌ ERROR: Faltan IDs en el archivo .env. Revisa tu configuración.")
    exit()

# Paleta de Colores (Theme)
class Theme:
    DARK = 0x2B2D31       # Fondo oscuro Discord
    SUCCESS = 0x43B581    # Verde
    ERROR = 0xF04747      # Rojo
    WARN = 0xFAA61A       # Naranja
    MM_COLOR = 0x5865F2   # Azul Blurple (Middleman)
    GALAXY = 0x6A0DAD     # Morado
    BAN = 0x000000        # Negro

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="$", help_command=None, intents=intents)

# ==========================================
# 💾 SISTEMA DE DATOS (JSON)
# ==========================================

def init_files():
    if not os.path.exists("count.json"):
        with open("count.json", "w") as f: json.dump({"count": 1}, f)
    if not os.path.exists("blacklist.json"):
        with open("blacklist.json", "w") as f: json.dump({"banned": []}, f)

def get_count():
    with open("count.json", "r") as f: return json.load(f).get("count", 1)

def inc_count():
    c = get_count()
    with open("count.json", "w") as f: json.dump({"count": c + 1}, f)
    return c

def is_banned(uid):
    with open("blacklist.json", "r") as f: return uid in json.load(f).get("banned", [])

def ban_user(uid):
    with open("blacklist.json", "r+") as f:
        d = json.load(f)
        if uid not in d["banned"]:
            d["banned"].append(uid)
            f.seek(0); json.dump(d, f); f.truncate()

# ==========================================
# 🧠 IA (GROQ)
# ==========================================

def get_random_joke():
    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b", # O usa 'llama3-70b-8192' si ese no va
            messages=[{"role": "system", "content": "Eres un bot gracioso. Di una frase corta y chistosa en español."}, 
                      {"role": "user", "content": "di algo"}],
            temperature=1.2, max_tokens=100
        )
        return completion.choices[0].message.content.strip()
    except: return "Mi cerebro IA se reinició... 🤖"

def parse_user(arg, guild):
    arg = arg.strip()
    if re.match(r'^\d{17,20}$', arg): return guild.get_member(int(arg))
    if arg.startswith("<@"): 
        mid = re.search(r'\d+', arg)
        if mid: return guild.get_member(int(mid.group()))
    return discord.utils.find(lambda m: m.name == arg, guild.members)

# ==========================================
# 🛡️ SISTEMA DE CONFESIONES (UI)
# ==========================================

class DenyReasonModal(discord.ui.Modal, title="Motivo del Rechazo"):
    reason = discord.ui.TextInput(label="Razón", style=discord.TextStyle.paragraph, required=True)
    
    def __init__(self, embed_log, author):
        super().__init__()
        self.embed_log = embed_log
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        self.embed_log.color = Theme.ERROR
        self.embed_log.set_field_at(0, name="📊 Estado", value=f"🔴 **DENEGADO**\n👮 Por: {interaction.user.mention}\n📝 Razón: {self.reason.value}", inline=False)
        await interaction.message.edit(embed=self.embed_log, view=None)
        try: await self.author.send(f"❌ Tu confesión fue denegada: {self.reason.value}")
        except: pass
        await interaction.response.send_message("✅ Denegado con motivo.", ephemeral=True)

class AdminView(discord.ui.View):
    def __init__(self, content, img, author, number):
        super().__init__(timeout=None)
        self.content = content
        self.img = img
        self.author = author
        self.number = number

    # Solo usuarios con MODERATOR_ROLE_ID pueden tocar botones
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.get_role(MODERATOR_ROLE_ID):
            await interaction.response.send_message("🔒 Solo Moderadores pueden gestionar esto.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, emoji="✅", custom_id="conf_approve")
    async def approve(self, interaction: discord.Interaction, button):
        chn = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)
        if not chn: return await interaction.response.send_message("❌ Canal público no encontrado.", ephemeral=True)

        # Embed Público (Anónimo)
        embed = discord.Embed(description=self.content, color=Theme.DARK, timestamp=datetime.now())
        embed.set_author(name=f"Confesión #{self.number}", icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png")
        if self.img: embed.set_image(url=self.img)
        embed.set_footer(text="A.E.C MM • ¡Envía la tuya!")
        
        await chn.send(embed=embed)
        
        # Log Update
        log = interaction.message.embeds[0]
        log.color = Theme.SUCCESS
        log.set_field_at(0, name="📊 Estado", value=f"🟢 **APROBADO**\n👮 Por: {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=log, view=None)
        await interaction.response.send_message("✅ Publicada.", ephemeral=True)

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.secondary, emoji="✖️", custom_id="conf_deny")
    async def deny(self, interaction: discord.Interaction, button):
        log = interaction.message.embeds[0]
        log.color = Theme.ERROR
        log.set_field_at(0, name="📊 Estado", value=f"🔴 **DENEGADO**\n👮 Por: {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=log, view=None)
        await interaction.response.send_message("🗑️ Denegada.", ephemeral=True)

    @discord.ui.button(label="Motivo", style=discord.ButtonStyle.primary, emoji="💬", custom_id="conf_reason")
    async def reason(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(DenyReasonModal(interaction.message.embeds[0], self.author))

    @discord.ui.button(label="BAN", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="conf_ban")
    async def ban(self, interaction: discord.Interaction, button):
        ban_user(self.author.id)
        log = interaction.message.embeds[0]
        log.color = Theme.BAN
        log.set_field_at(0, name="📊 Estado", value=f"⚫ **BANEADO**\n👮 Por: {interaction.user.mention}\n👤 {self.author.mention}", inline=False)
        await interaction.message.edit(embed=log, view=None)
        await interaction.response.send_message(f"⛔ {self.author.name} ha sido baneado.", ephemeral=True)

class ConfessionModal(discord.ui.Modal, title="Enviar Confesión"):
    content = discord.ui.TextInput(label="Confesión", style=discord.TextStyle.paragraph, placeholder="Escribe aquí...", min_length=5, max_length=3000)
    attachment = discord.ui.TextInput(label="Imagen (URL)", required=False, placeholder="https://...")

    async def on_submit(self, interaction: discord.Interaction):
        if is_banned(interaction.user.id):
            return await interaction.response.send_message("⛔ Estás baneado.", ephemeral=True)
        
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        num = inc_count()
        img = self.attachment.value if self.attachment.value else None

        # Embed Log (Visible para Mods)
        embed = discord.Embed(title=f"📝 Pendiente #{num}", description=f"``````", color=Theme.WARN, timestamp=datetime.now())
        embed.set_author(name=f"{interaction.user}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="📊 Estado", value="⏳ **Esperando Revisión**", inline=False)
        embed.add_field(name="👤 Autor", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        if img: embed.set_image(url=img)

        await log_channel.send(embed=embed, view=AdminView(self.content.value, img, interaction.user, num))
        await interaction.response.send_message(f"✅ Confesión **#{num}** enviada a revisión.", ephemeral=True)

class StartView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Crear una confesión", style=discord.ButtonStyle.primary, emoji="📩", custom_id="start_btn_main")
    async def start(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(ConfessionModal())

# ==========================================
# 🚀 COMANDOS Y EVENTOS
# ==========================================

@bot.event
async def on_ready():
    init_files()
    bot.add_view(StartView()) # Persistencia del botón
    print(f"🌌 A.E.C MM BOT ACTIVO | {bot.user}")
    print(f"🔹 Middleman Role: {MM_ROLE_ID}")
    print(f"🔹 Moderator Role: {MODERATOR_ROLE_ID}")

# --- COMANDO MIDDLEMAN ($ADD) ---
@bot.command(name="add")
async def add_user(ctx, *, arg=None):
    # 1. Verificar Rol Middleman
    if not ctx.author.get_role(MM_ROLE_ID):
        return await ctx.send(embed=discord.Embed(title="🔒 Acceso Denegado", description="Solo **Middlemans** pueden usar esto.", color=Theme.ERROR))

    if not arg: return await ctx.send(embed=discord.Embed(description="❌ Uso: `$add @usuario`", color=Theme.ERROR))

    # 2. Buscar Usuario
    user = parse_user(arg, ctx.guild)
    if not user: return await ctx.send(embed=discord.Embed(description="❌ Usuario no encontrado.", color=Theme.ERROR))

    try:
        # 3. Dar Permisos
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True)
        
        # 4. Embed Éxito Aesthetic
        embed = discord.Embed(description=f"👋 **{user.mention}** ha sido añadido al ticket.", color=Theme.MM_COLOR)
        embed.set_footer(text=f"Añadido por {ctx.author.display_name} | A.E.C MM")
        await ctx.send(embed=embed)

        # 5. Frase Groq
        joke = await asyncio.to_thread(get_random_joke)
        await ctx.send(embed=discord.Embed(description=f"🤖 *{joke}*", color=Theme.GALAXY))

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

# --- COMANDO SETUP CONFESIONES ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🔮 Confesiones A.E.C MM",
        description="Envía tu confesión de forma **100% anónima**.\n\n🔹 Nadie verá tu nombre en el canal público.\n🔹 Los moderadores revisarán el contenido antes de publicarlo.",
        color=Theme.GALAXY
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1011326049646030968/1169336487616122940/confessions_banner.png") # Pon tu banner aquí
    await ctx.send(embed=embed, view=StartView())

if __name__ == "__main__":
    bot.run(TOKEN)
