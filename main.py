import discord
from discord.ext import commands
import os
import json
import asyncio
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
import re

# ==============================================================================
# ⚙️ CONFIGURACIÓN Y CONSTANTES
# ==============================================================================

load_dotenv()

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_KEY = os.getenv("GROQ_API_KEY")
    
    # Validación de enteros segura
    try:
        GUILD_ID = int(os.getenv("GUILD_ID", 0))
        CONFESSION_CH_ID = int(os.getenv("CONFESSION_CHANNEL_ID", 0))
        LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
        MM_ROLE_ID = int(os.getenv("MM_ROLE_ID", 0))
        MOD_ROLE_ID = int(os.getenv("MODERATOR_ROLE_ID", 0))
    except ValueError:
        print("❌ ERROR CRÍTICO: Los IDs en el archivo .env deben ser números.")
        exit()

class Colors:
    GALAXY = 0x6A0DAD      # Morado Principal
    SUCCESS = 0x43B581     # Verde Éxito
    ERROR = 0xF04747       # Rojo Error
    WARNING = 0xFAA61A     # Naranja Alerta
    DARK = 0x2B2D31        # Fondo Discord (Embeds Anónimos)
    BAN = 0x000000         # Negro Ban
    MM = 0x5865F2          # Azul Middleman

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# ==============================================================================
# 💾 GESTOR DE DATOS (Persistencia JSON)
# ==============================================================================

class DataManager:
    @staticmethod
    def _check_files():
        if not os.path.exists("count.json"):
            with open("count.json", "w") as f: json.dump({"count": 1}, f)
        if not os.path.exists("blacklist.json"):
            with open("blacklist.json", "w") as f: json.dump({"banned": []}, f)

    @staticmethod
    def get_next_id():
        DataManager._check_files()
        with open("count.json", "r") as f:
            data = json.load(f)
        new_count = data.get("count", 1)
        with open("count.json", "w") as f:
            json.dump({"count": new_count + 1}, f)
        return new_count

    @staticmethod
    def is_banned(user_id):
        DataManager._check_files()
        with open("blacklist.json", "r") as f:
            return user_id in json.load(f).get("banned", [])

    @staticmethod
    def ban_user(user_id):
        DataManager._check_files()
        with open("blacklist.json", "r+") as f:
            data = json.load(f)
            if user_id not in data["banned"]:
                data["banned"].append(user_id)
                f.seek(0); json.dump(data, f); f.truncate()

# ==============================================================================
# 🧠 INTELIGENCIA ARTIFICIAL (Groq Wrapper)
# ==============================================================================

async def get_ai_joke():
    if not Config.GROQ_KEY: return "⚠️ API Key no configurada."
    try:
        client = Groq(api_key=Config.GROQ_KEY)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Di una frase corta, ingeniosa y graciosa en español."}],
            temperature=1.2,
            max_tokens=60
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"La IA está durmiendo... 😴"

# ==============================================================================
# 🧩 COMPONENTES DE INTERFAZ (Views & Modals)
# ==============================================================================

# --- 1. BOTÓN PÚBLICO (EL ETERNO) ---
class PersistentConfessionButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout None = Infinito

    @discord.ui.button(
        label="Enviar Confesión Anónima", 
        style=discord.ButtonStyle.primary, 
        emoji="📩", 
        custom_id="persistent_confess_btn"
    )
    async def open_confession_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar Ban antes de abrir modal
        if DataManager.is_banned(interaction.user.id):
            return await interaction.response.send_message(
                embed=discord.Embed(title="⛔ Acceso Denegado", description="Estás baneado del sistema.", color=Colors.BAN),
                ephemeral=True
            )
        await interaction.response.send_modal(ConfessionModal())

# --- 2. MODAL DE ESCRITURA ---
class ConfessionModal(discord.ui.Modal, title="🤫 Tu Secreto"):
    
    text_input = discord.ui.TextInput(
        label="Escribe tu confesión",
        style=discord.TextStyle.paragraph,
        placeholder="Escribe aquí... (Totalmente anónimo)",
        min_length=5,
        max_length=3500,
        required=True
    )
    
    img_input = discord.ui.TextInput(
        label="URL de Imagen (Opcional)",
        style=discord.TextStyle.short,
        placeholder="https://...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Capturamos datos
        content = self.text_input.value
        image = self.img_input.value if self.img_input.value else None
        conf_id = DataManager.get_next_id()
        
        log_channel = interaction.guild.get_channel(Config.LOG_CH_ID)
        if not log_channel:
            return await interaction.response.send_message("❌ Error: Canal de logs no encontrado.", ephemeral=True)

        # Embed para LOGS (Estilo Expediente)
        embed = discord.Embed(
            description=f"📄 **Contenido:**\n{content}",
            color=Colors.WARNING,
            timestamp=datetime.now()
        )
        embed.set_author(name=f"Expediente #{conf_id}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Autor", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
        embed.add_field(name="📅 Cuenta", value=f"<t:{int(interaction.user.created_at.timestamp())}:R>", inline=True)
        embed.set_footer(text="Sistema de Moderación A.E.C MM")
        
        if image: embed.set_image(url=image)

        # Enviar a Logs con panel de control
        view = AdminControlPanel(content, image, interaction.user, conf_id)
        await log_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(f"✅ **Confesión #{conf_id} recibida.** Pendiente de revisión.", ephemeral=True)

# --- 3. PANEL DE CONTROL ADMIN ---
class AdminControlPanel(discord.ui.View):
    def __init__(self, content, image, author, conf_id):
        super().__init__(timeout=None)
        self.content = content
        self.image = image
        self.author = author
        self.conf_id = conf_id

    # Check de seguridad: SOLO MODERADORES
    async def interaction_check(self, interaction: discord.Interaction):
        if not interaction.user.get_role(Config.MOD_ROLE_ID):
            await interaction.response.send_message("🔒 **Acceso Denegado:** Solo moderadores.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, emoji="✅", custom_id="adm_approve")
    async def approve(self, interaction: discord.Interaction, button):
        public_channel = interaction.guild.get_channel(Config.CONFESSION_CH_ID)
        
        # Embed Público Aesthetic
        embed_pub = discord.Embed(
            description=self.content,
            color=Colors.DARK,
            timestamp=datetime.now()
        )
        embed_pub.set_author(name=f"Confesión Anónima #{self.conf_id}", icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png")
        if self.image: embed_pub.set_image(url=self.image)
        embed_pub.set_footer(text="A.E.C MM • Secretos Anónimos")

        # 🔥 AQUÍ ESTÁ LA MAGIA: Enviamos el botón junto con el mensaje
        await public_channel.send(embed=embed_pub, view=PersistentConfessionButton())

        # Actualizar Log
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.SUCCESS
        embed_log.set_field_at(0, name="📊 Estado", value=f"🟢 **APROBADO**\n👮 {interaction.user.mention}", inline=False)
        
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message("✅ Publicado.", ephemeral=True)

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="adm_deny")
    async def deny(self, interaction: discord.Interaction, button):
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.ERROR
        embed_log.set_field_at(0, name="📊 Estado", value=f"🔴 **DENEGADO**\n👮 {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message("🗑️ Rechazado.", ephemeral=True)

    @discord.ui.button(label="Banear", style=discord.ButtonStyle.secondary, emoji="🔨", custom_id="adm_ban")
    async def ban(self, interaction: discord.Interaction, button):
        DataManager.ban_user(self.author.id)
        
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.BAN
        embed_log.set_field_at(0, name="📊 Estado", value=f"⚫ **BANEADO**\n👤 {self.author.mention}", inline=False)
        
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message(f"⛔ Usuario {self.author.name} bloqueado.", ephemeral=True)

# ==============================================================================
# 🤖 CLASE PRINCIPAL DEL BOT
# ==============================================================================

class GalaxyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="$", help_command=None, intents=intents)

    async def setup_hook(self):
        # Esto regenera el botón al reiniciar el bot para que no muera nunca
        self.add_view(PersistentConfessionButton())
        print("✅ Hook de persistencia cargado correctamente.")

    async def on_ready(self):
        print("------------------------------------------------")
        print(f"🚀 Galaxy Bot v4.0 Enterprise | {self.user}")
        print(f"🌍 Guild ID: {Config.GUILD_ID}")
        print("------------------------------------------------")

bot = GalaxyBot()

# ==============================================================================
# 🚀 COMANDOS
# ==============================================================================

@bot.command(name="add")
async def add_middleman(ctx, *, arg=None):
    """Comando exclusivo para Middlemans"""
    
    # 1. Validar Rol
    if not ctx.author.get_role(Config.MM_ROLE_ID):
        embed = discord.Embed(title="🔒 Acceso Denegado", description="No tienes el rol de **Middleman**.", color=Colors.ERROR)
        return await ctx.send(embed=embed)
    
    # 2. Validar Argumento
    if not arg:
        return await ctx.send(embed=discord.Embed(description="⚠️ Uso: `$add @usuario` o ID.", color=Colors.WARNING))

    # 3. Encontrar Usuario
    user = None
    # Buscar por mención
    if ctx.message.mentions:
        user = ctx.message.mentions[0]
    # Buscar por ID
    elif arg.isdigit():
        user = ctx.guild.get_member(int(arg))
    
    if not user:
        return await ctx.send(embed=discord.Embed(description="❌ Usuario no encontrado en el servidor.", color=Colors.ERROR))

    # 4. Ejecutar Acción (Dar permisos)
    try:
        await ctx.channel.set_permissions(
            user, 
            view_channel=True, 
            send_messages=True, 
            read_message_history=True, 
            attach_files=True,
            embed_links=True
        )
        
        # 5. Feedback Visual
        embed = discord.Embed(
            description=f"✅ **{user.mention}** ha sido añadido correctamente al ticket.",
            color=Colors.MM
        )
        embed.set_footer(text=f"Moderado por {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
        # 6. Chiste IA
        joke = await get_ai_joke()
        await ctx.send(embed=discord.Embed(description=f"🤖 **Galaxy AI:** {joke}", color=Colors.GALAXY))

    except Exception as e:
        await ctx.send(f"❌ Error de Discord: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Instala el panel de confesiones"""
    await ctx.message.delete()
    
    embed = discord.Embed(
        title="🌌 Confesiones A.E.C MM",
        description=(
            "**Bienvenido al espacio de secretos anónimos.**\n\n"
            "🔹 **Anonimato Total:** Tu nombre se elimina automáticamente.\n"
            "🔹 **Seguridad:** Todo contenido es revisado por humanos.\n"
            "🔹 **Instrucciones:** Haz clic en el botón para empezar."
        ),
        color=Colors.GALAXY
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1011326049646030968/1169336487616122940/confessions_banner.png")
    embed.set_footer(text="Powered by Galaxy Bot System")
    
    await ctx.send(embed=embed, view=PersistentConfessionButton())

# ==============================================================================
# 🔥 EJECUCIÓN
# ==============================================================================

if __name__ == "__main__":
    try:
        bot.run(Config.TOKEN)
    except Exception as e:
        print(f"❌ El bot se detuvo por un error: {e}")
