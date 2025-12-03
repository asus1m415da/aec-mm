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
# ⚙️ CONFIGURACIÓN
# ==========================================

load_dotenv()

# Credenciales
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# IDs
try:
    GUILD_ID = int(os.getenv("GUILD_ID"))
    CONFESSION_CHANNEL_ID = int(os.getenv("CONFESSION_CHANNEL_ID"))
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
    MM_ROLE_ID = int(os.getenv("MM_ROLE_ID"))           # Rol para comando $add
    MODERATOR_ROLE_ID = int(os.getenv("MODERATOR_ROLE_ID")) # Rol para Aprobar Logs
except (TypeError, ValueError):
    print("❌ ERROR FATAL: Faltan IDs en el archivo .env")
    exit()

# Paleta de Colores Aesthetic
class Colors:
    DARK = 0x2B2D31       # Fondo Discord (Para confesiones anónimas)
    LOG_PENDING = 0xFAA61A # Naranja (Pendiente)
    LOG_APPROVE = 0x43B581 # Verde (Aprobado)
    LOG_DENY = 0xF04747    # Rojo (Denegado)
    LOG_BAN = 0x000000     # Negro (Ban)
    MM_SUCCESS = 0x5865F2  # Azul (Middleman)

# Configuración del Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class GalaxyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="$", help_command=None, intents=intents)

    async def setup_hook(self):
        # Esto hace que el botón "Confesar" funcione incluso si reinicias el bot
        self.add_view(PublicConfessionView())
        print("✅ Vistas persistentes cargadas.")

bot = GalaxyBot()

# ==========================================
# 📂 BASE DE DATOS (JSON)
# ==========================================

def check_files():
    if not os.path.exists("count.json"):
        with open("count.json", "w") as f: json.dump({"count": 1}, f)
    if not os.path.exists("blacklist.json"):
        with open("blacklist.json", "w") as f: json.dump({"banned": []}, f)

def get_next_id():
    with open("count.json", "r") as f: 
        c = json.load(f).get("count", 1)
    with open("count.json", "w") as f: 
        json.dump({"count": c + 1}, f)
    return c

def is_user_banned(user_id):
    with open("blacklist.json", "r") as f: 
        return user_id in json.load(f).get("banned", [])

def ban_user_id(user_id):
    with open("blacklist.json", "r+") as f:
        data = json.load(f)
        if user_id not in data["banned"]:
            data["banned"].append(user_id)
            f.seek(0); json.dump(data, f); f.truncate()

# ==========================================
# 🧩 COMPONENTES UI (Botones y Modales)
# ==========================================

# --- 1. VISTA PÚBLICA (El botón que ve todo el mundo) ---
class PublicConfessionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistente para siempre

    @discord.ui.button(label="Enviar Confesión Anónima", style=discord.ButtonStyle.primary, emoji="📩", custom_id="public_confess_btn")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Abrimos el modal
        await interaction.response.send_modal(ConfessionModal())

# --- 2. EL MODAL (Formulario) ---
class ConfessionModal(discord.ui.Modal, title="🤫 Tu Secreto es Seguro"):
    
    confession = discord.ui.TextInput(
        label="Escribe tu confesión",
        style=discord.TextStyle.paragraph,
        placeholder="Escribe aquí... (Nadie sabrá que fuiste tú)",
        min_length=5,
        max_length=3500,
        required=True
    )
    
    image = discord.ui.TextInput(
        label="Imagen (Opcional)",
        style=discord.TextStyle.short,
        placeholder="https://i.imgur.com/...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Verificar Ban
        if is_user_banned(interaction.user.id):
            return await interaction.response.send_message("⛔ **Acceso Denegado:** Has sido vetado del sistema de confesiones.", ephemeral=True)

        # 2. Capturar datos
        text_content = self.confession.value
        img_content = self.image.value if self.image.value else None
        conf_id = get_next_id()
        
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        # 3. Crear Embed de Log (Estilo Expediente)
        embed = discord.Embed(
            description=f"📄 **Contenido:**\n{text_content}",
            color=Colors.LOG_PENDING,
            timestamp=datetime.now()
        )
        embed.set_author(name=f"Confesión Pendiente #{conf_id}", icon_url="https://cdn-icons-png.flaticon.com/512/1022/1022300.png")
        
        # Datos del usuario (Solo para admins)
        embed.add_field(name="👤 Autor", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
        embed.add_field(name="📅 Antigüedad", value=f"<t:{int(interaction.user.created_at.timestamp())}:R>", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        if img_content:
            embed.set_image(url=img_content)
            embed.set_footer(text="⚠️ Contiene imagen adjunta")

        # 4. Enviar a Logs con Botones de Admin
        view = AdminLogView(text_content, img_content, interaction.user, conf_id)
        await log_channel.send(embed=embed, view=view)

        await interaction.response.send_message(f"✅ **Confesión #{conf_id} recibida.** Esperando aprobación.", ephemeral=True)

# --- 3. VISTA DE ADMIN (Botones de Aprobar/Denegar) ---
class AdminLogView(discord.ui.View):
    def __init__(self, content, image, author, conf_id):
        super().__init__(timeout=None)
        self.content = content
        self.image = image
        self.author = author
        self.conf_id = conf_id

    # Verificación de seguridad: Solo MODERADORES pueden tocar
    async def interaction_check(self, interaction: discord.Interaction):
        if not interaction.user.get_role(MODERATOR_ROLE_ID):
            await interaction.response.send_message("🔒 **Acceso Denegado:** No eres moderador de confesiones.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, emoji="✅", custom_id="adm_approve")
    async def approve(self, interaction: discord.Interaction, button):
        public_channel = interaction.guild.get_channel(CONFESSION_CHANNEL_ID)
        
        # --- EL EMBED PÚBLICO (BONITO) ---
        embed_pub = discord.Embed(
            description=self.content,
            color=Colors.DARK, # Color oscuro minimalista
            timestamp=datetime.now()
        )
        embed_pub.set_author(name=f"Confesión Anónima #{self.conf_id}", icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png")
        if self.image: embed_pub.set_image(url=self.image)
        embed_pub.set_footer(text="A.E.C MM • Secretos Anónimos")

        # 🔥 AQUÍ ESTÁ LA MAGIA: Adjuntamos el botón de confesión al mensaje público
        await public_channel.send(embed=embed_pub, view=PublicConfessionView())

        # Actualizar Log a Verde
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.LOG_APPROVE
        embed_log.set_field_at(0, name="📊 Estado", value=f"🟢 **APROBADO**\n👮 {interaction.user.mention}", inline=False)
        # Quitamos datos sensibles del log visual si quieres, o los dejas. Aquí los dejo.
        
        await interaction.message.edit(embed=embed_log, view=None) # Quitamos botones
        await interaction.response.send_message("✅ Publicada con éxito.", ephemeral=True)

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="adm_deny")
    async def deny(self, interaction: discord.Interaction, button):
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.LOG_DENY
        embed_log.set_field_at(0, name="📊 Estado", value=f"🔴 **DENEGADO**\n👮 {interaction.user.mention}", inline=False)
        
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message("🗑️ Confesión eliminada.", ephemeral=True)

    @discord.ui.button(label="Banear Usuario", style=discord.ButtonStyle.secondary, emoji="🔨", custom_id="adm_ban")
    async def ban(self, interaction: discord.Interaction, button):
        ban_user_id(self.author.id)
        
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.LOG_BAN
        embed_log.set_field_at(0, name="📊 Estado", value=f"⚫ **BANEADO**\n👤 {self.author.mention}", inline=False)
        
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message(f"⛔ El usuario {self.author.name} ha sido bloqueado.", ephemeral=True)

# ==========================================
# 🚀 COMANDOS DEL BOT
# ==========================================

@bot.event
async def on_ready():
    check_files()
    print(f"🌌 Galaxy Bot v3.5 Listo | {bot.user}")

# --- COMANDO MIDDLEMAN ($ADD) ---
@bot.command(name="add")
async def add_user(ctx, *, arg=None):
    # Verificar si tiene el Rol de Middleman
    if not ctx.author.get_role(MM_ROLE_ID):
        return await ctx.send(embed=discord.Embed(description="🔒 No tienes permisos de Middleman.", color=Colors.LOG_DENY))
    
    if not arg: return await ctx.send("⚠️ Debes mencionar a alguien o poner su ID.")

    # Buscar usuario (Lógica simple)
    user = None
    if arg.isdigit(): user = ctx.guild.get_member(int(arg))
    elif "<@" in arg: user = ctx.guild.get_member(int(re.search(r'\d+', arg).group()))
    
    if not user: return await ctx.send("❌ Usuario no encontrado.")

    # Dar permisos
    try:
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        
        # Embed Bonito
        embed = discord.Embed(description=f"👋 **{user.mention}** añadido al ticket.", color=Colors.MM_SUCCESS)
        embed.set_footer(text=f"Añadido por {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
        # IA Joke
        try:
            client = Groq(api_key=GROQ_API_KEY)
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":"Dime una frase corta y graciosa random en español."}])
            joke = chat.choices[0].message.content
            await ctx.send(f"> 🤖 *{joke}*")
        except: pass
        
    except Exception as e:
        await ctx.send(f"Error de permisos: {e}")

# --- COMANDO SETUP (Solo Admin) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🌙 Confesiones Anónimas",
        description="Envía tus secretos sin revelar tu identidad.\n\n🛡️ **100% Seguro:** Tu nombre está oculto al público.\n👁️ **Moderado:** Todo pasa por revisión.",
        color=Colors.GALAXY
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1011326049646030968/1169336487616122940/confessions_banner.png") # Puedes cambiar esto
    
    await ctx.send(embed=embed, view=PublicConfessionView())

if __name__ == "__main__":
    bot.run(TOKEN)
