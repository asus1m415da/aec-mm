"""
╔═══════════════════════════════════════════════════════════════╗
║          🚀 GALAXY BOT ENTERPRISE & MM RANKING v3.0           ║
║       Sistema Unificado de Moderación, Confesiones y Proofs   ║
╚═══════════════════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
import os
import json
import asyncio
import logging
import traceback
import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dotenv import load_dotenv
from pathlib import Path
from flask import Flask
from threading import Thread
from groq import Groq

# ==============================================================================
# 🌐 SERVIDOR WEB (KEEP ALIVE PARA KOYEB)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "🚀 Súper Bot Activo: Confesiones y Ranking operando al 100%"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==============================================================================
# ⚙️ CONFIGURACIÓN Y LOGGING
# ==============================================================================
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('super_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_KEY = os.getenv("GROQ_API_KEY")
    
    try:
        GUILD_ID = int(os.getenv("GUILD_ID", 0))
        CONFESSION_CH_ID = int(os.getenv("CONFESSION_CHANNEL_ID", 0))
        LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
        MM_ROLE_ID = int(os.getenv("MM_ROLE_ID", 0))
        MOD_ROLE_ID = int(os.getenv("MODERATOR_ROLE_ID", 0))
        ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
        PROOF_CH_ID = int(os.getenv("PROOF_CHANNEL_ID", 0))
    except (ValueError, TypeError):
        logger.critical("❌ ERROR CRÍTICO: Los IDs en el archivo .env deben ser números.")
        exit(1)

class Colors:
    GALAXY = 0x6A0DAD
    SUCCESS = 0x43B581
    ERROR = 0xF04747
    WARNING = 0xFAA61A
    DARK = 0x2B2D31
    BAN = 0x000000
    MM = 0x5865F2

# Rutas de datos consolidadas
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
RANKING_FILE = DATA_DIR / 'ranking_data.json'
CONFESSION_FILE = DATA_DIR / 'confession_data.json'
BACKUP_DIR = DATA_DIR / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)

# ==============================================================================
# 💾 GESTOR DE DATOS UNIFICADO (Thread-Safe)
# ==============================================================================
class DataManager:
    def __init__(self):
        self.ranking_data: Dict[int, int] = {}
        self.confession_count: int = 1
        self.banned_users: List[int] = []
        self.lock = asyncio.Lock()
        self._load_all()

    def _load_all(self):
        # Cargar Ranking
        if RANKING_FILE.exists():
            try:
                with open(RANKING_FILE, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                self.ranking_data = {int(uid): int(count) for uid, count in raw.items()}
            except Exception as e:
                logger.error(f"Error cargando ranking: {e}")
        
        # Cargar Confesiones y Bans
        if CONFESSION_FILE.exists():
            try:
                with open(CONFESSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.confession_count = data.get("count", 1)
                    self.banned_users = data.get("banned", [])
            except Exception as e:
                logger.error(f"Error cargando datos de confesiones: {e}")
        else:
            self._save_confessions()

    def _save_ranking(self):
        with open(RANKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.ranking_data, f, indent=2, ensure_ascii=False)

    def _save_confessions(self):
        with open(CONFESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump({"count": self.confession_count, "banned": self.banned_users}, f, indent=2)

    def _backup_ranking(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(BACKUP_DIR / f"ranking_{timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump(self.ranking_data, f, indent=2, ensure_ascii=False)

    # --- Métodos de Ranking ---
    async def increment_proof(self, user_id: int):
        async with self.lock:
            self.ranking_data[user_id] = self.ranking_data.get(user_id, 0) + 1
            self._backup_ranking()
            self._save_ranking()

    async def remove_user(self, user_id: int) -> bool:
        async with self.lock:
            if user_id in self.ranking_data:
                del self.ranking_data[user_id]
                self._save_ranking()
                return True
            return False

    async def get_ranking(self) -> list:
        return sorted(self.ranking_data.items(), key=lambda x: x[1], reverse=True)

    async def export_ranking(self) -> str:
        return json.dumps(self.ranking_data, indent=2, ensure_ascii=False)

    async def import_ranking(self, json_str: str) -> Tuple[bool, str]:
        try:
            new_data = json.loads(json_str)
            validated = {int(uid): int(count) for uid, count in new_data.items() if int(count) >= 0}
            async with self.lock:
                self._backup_ranking()
                self.ranking_data = validated
                self._save_ranking()
            return True, f"✅ {len(validated)} usuarios importados"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"

    # --- Métodos de Confesiones ---
    async def get_next_confession_id(self):
        async with self.lock:
            current = self.confession_count
            self.confession_count += 1
            self._save_confessions()
            return current

    def is_banned(self, user_id: int) -> bool:
        return user_id in self.banned_users

    async def ban_user(self, user_id: int):
        async with self.lock:
            if user_id not in self.banned_users:
                self.banned_users.append(user_id)
                self._save_confessions()

data_manager = DataManager()

# ==============================================================================
# 🧠 UTILIDADES E IA
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
    except Exception:
        return "La IA está durmiendo... 😴"

class UltraProofDetector:
    @staticmethod
    def contains_proof_variant(text: str) -> bool:
        if not text: return False
        normalized = text.lower().strip()
        patterns = [r'pr[o0]f+', r'proof', r'proff', r'pr\s*[o0]\s*f+', r'p\s*r\s*[o0]\s*f+', r'#\d+', r'p[r0][o0]f{1,2}']
        return any(re.search(p, normalized, re.IGNORECASE) for p in patterns) or "proof" in normalized or "proff" in normalized

    @staticmethod
    def has_attachments_or_embeds(message: discord.Message) -> bool:
        return len(message.attachments) > 0 or len(message.embeds) > 0

# ==============================================================================
# 🧩 COMPONENTES DE UI (Rankings y Confesiones)
# ==============================================================================
class EmbedBuilder:
    @staticmethod
    def ranking_pages(ranking_data: list) -> List[discord.Embed]:
        if not ranking_data:
            return [discord.Embed(title="🏆 RANKING DE PROOFS - MM", description="Sin datos registrados", color=discord.Color.gold())]
        
        medals = ["🥇", "🥈", "🥉"] + ["#️⃣"] * 997
        pages, current_text, page_num, users_per_page, start_idx = [], "", 1, 0, 0
        
        for idx, (uid, count) in enumerate(ranking_data, 1):
            line = f"{medals[idx - 1] if idx <= 3 else '▫️'} `#{idx:02d}` <@{uid}> • **{count}** ✅\n"
            if len(current_text) + len(line) > 3900 or users_per_page >= 50:
                embed = discord.Embed(title=f"🏆 RANKING DE PROOFS (Página {page_num})", description=current_text, color=discord.Color.gold())
                pages.append(embed)
                current_text, page_num, users_per_page, start_idx = line, page_num + 1, 1, idx - 1
            else:
                if users_per_page == 0: start_idx = idx - 1
                current_text += line
                users_per_page += 1
                
        if current_text:
            embed = discord.Embed(title=f"🏆 RANKING DE PROOFS (Página {page_num})", description=current_text, color=discord.Color.gold())
            pages.append(embed)
        return pages

class PaginationView(discord.ui.View):
    def __init__(self, pages: List[discord.Embed]):
        super().__init__(timeout=180.0)
        self.pages = pages
        self.current_page = 0
        self.message = None
        if len(pages) <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True

    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= len(self.pages) - 1

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Siguiente ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

class PersistentConfessionButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enviar Confesión Anónima", style=discord.ButtonStyle.primary, emoji="📩", custom_id="persistent_confess_btn")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if data_manager.is_banned(interaction.user.id):
            return await interaction.response.send_message(embed=discord.Embed(title="⛔ Denegado", description="Estás baneado.", color=Colors.BAN), ephemeral=True)
        await interaction.response.send_modal(ConfessionModal())

class ConfessionModal(discord.ui.Modal, title="🤫 Tu Secreto"):
    text_input = discord.ui.TextInput(label="Confesión", style=discord.TextStyle.paragraph, required=True, max_length=3500)
    img_input = discord.ui.TextInput(label="URL Imagen (Opcional)", style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        conf_id = await data_manager.get_next_confession_id()
        log_channel = interaction.guild.get_channel(Config.LOG_CH_ID)
        
        embed = discord.Embed(description=f"📄 **Contenido:**\n{self.text_input.value}", color=Colors.WARNING, timestamp=datetime.now())
        embed.set_author(name=f"Expediente #{conf_id}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Autor", value=f"{interaction.user.mention}\n`{interaction.user.id}`")
        if self.img_input.value: embed.set_image(url=self.img_input.value)

        view = AdminControlPanel(self.text_input.value, self.img_input.value, interaction.user, conf_id)
        await log_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Confesión #{conf_id} enviada a revisión.", ephemeral=True)

class AdminControlPanel(discord.ui.View):
    def __init__(self, content, image, author, conf_id):
        super().__init__(timeout=None)
        self.content = content
        self.image = image
        self.author = author
        self.conf_id = conf_id

    async def interaction_check(self, interaction: discord.Interaction):
        if not interaction.user.get_role(Config.MOD_ROLE_ID):
            await interaction.response.send_message("🔒 Solo moderadores.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, emoji="✅", custom_id="adm_approve")
    async def approve(self, interaction: discord.Interaction, button):
        pub_channel = interaction.guild.get_channel(Config.CONFESSION_CH_ID)
        embed_pub = discord.Embed(description=self.content, color=Colors.DARK)
        embed_pub.set_author(name=f"Confesión #{self.conf_id}", icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png")
        if self.image: embed_pub.set_image(url=self.image)
        
        await pub_channel.send(embed=embed_pub, view=PersistentConfessionButton())
        
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.SUCCESS
        embed_log.set_field_at(0, name="📊 Estado", value=f"🟢 **APROBADO**\n👮 {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message("✅ Publicado.", ephemeral=True)

    @discord.ui.button(label="Banear", style=discord.ButtonStyle.secondary, emoji="🔨", custom_id="adm_ban")
    async def ban(self, interaction: discord.Interaction, button):
        await data_manager.ban_user(self.author.id)
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.BAN
        embed_log.set_field_at(0, name="📊 Estado", value=f"⚫ **BANEADO**\n👤 {self.author.mention}", inline=False)
        await interaction.message.edit(embed=embed_log, view=None)
        await interaction.response.send_message(f"⛔ Usuario bloqueado.", ephemeral=True)

# ==============================================================================
# 🤖 BOT PRINCIPAL (Núcleo)
# ==============================================================================
class SuperBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        # Soporta los prefijos de ambos bots antiguos
        super().__init__(command_prefix=["$", "!"], help_command=None, intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentConfessionButton())
        logger.info("✅ Hooks de UI persistente cargados.")

    async def on_ready(self):
        logger.info("="*50)
        logger.info(f"🚀 Súper Bot Conectado | {self.user}")
        logger.info("🛡️ Módulo A.E.C MM: ONLINE")
        logger.info("🏆 Módulo Ranking: ONLINE")
        logger.info("="*50)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return await self.process_commands(message)

        # 🔍 SISTEMA DE DETECCIÓN DE PROOFS AUTOMÁTICO
        if message.channel.id == Config.PROOF_CH_ID:
            if UltraProofDetector.contains_proof_variant(message.content) and UltraProofDetector.has_attachments_or_embeds(message):
                await data_manager.increment_proof(message.author.id)
                await message.add_reaction("✅")
                logger.info(f"✅ PROOF AÑADIDO: {message.author}")

        await self.process_commands(message)

bot = SuperBot()

# ==============================================================================
# 🛠️ COMANDOS DE MODERACIÓN Y CONFESIONES (Prefijo $)
# ==============================================================================
@bot.command()
async def add(ctx, *, arg=None):
    """Añade a un usuario al ticket (Solo Middlemans)"""
    if not ctx.author.get_role(Config.MM_ROLE_ID):
        return await ctx.send(embed=discord.Embed(description="🔒 Acceso Denegado. Solo Middlemans.", color=Colors.ERROR))
    if not arg:
        return await ctx.send(embed=discord.Embed(description="⚠️ Uso: `$add @usuario` o ID.", color=Colors.WARNING))

    user = ctx.message.mentions[0] if ctx.message.mentions else ctx.guild.get_member(int(arg)) if arg.isdigit() else None
    if not user: return await ctx.send("❌ Usuario no encontrado.")

    try:
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        await ctx.send(embed=discord.Embed(description=f"✅ **{user.mention}** añadido al ticket.", color=Colors.MM))
        joke = await get_ai_joke()
        await ctx.send(embed=discord.Embed(description=f"🤖 **IA:** {joke}", color=Colors.GALAXY))
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Instala el panel de confesiones"""
    await ctx.message.delete()
    embed = discord.Embed(title="🌌 Confesiones A.E.C MM", description="Haz clic en el botón para enviar una confesión anónima.", color=Colors.GALAXY)
    await ctx.send(embed=embed, view=PersistentConfessionButton())

# ==============================================================================
# 🏆 COMANDOS DE RANKING (Prefijo !)
# ==============================================================================
@bot.command(name='rank-mm')
async def rank_mm(ctx):
    """Muestra el ranking de proofs"""
    ranking = await data_manager.get_ranking()
    pages = EmbedBuilder.ranking_pages(ranking)
    
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
    else:
        view = PaginationView(pages)
        view.message = await ctx.send(embed=pages[0], view=view)

@bot.command(name='borrar-ranking')
async def borrar_ranking(ctx, user: discord.User):
    """Borra a un usuario del ranking (Solo Admin)"""
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send("🔒 Denegado.")
    success = await data_manager.remove_user(user.id)
    await ctx.send(f"✅ {user.mention} eliminado del ranking." if success else f"❌ {user.mention} no estaba en el ranking.")

@bot.command(name='exportar-datos')
async def exportar_datos(ctx):
    """Exporta el JSON del ranking (Solo Admin)"""
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send("🔒 Denegado.")
    data = await data_manager.export_ranking()
    filename = BACKUP_DIR / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f: f.write(data)
    await ctx.send("✅ Exportado:", file=discord.File(filename))

@bot.command(name='importar-datos')
async def importar_datos(ctx):
    """Importa un JSON para el ranking (Solo Admin)"""
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send("🔒 Denegado.")
    if not ctx.message.attachments or not ctx.message.attachments[0].filename.endswith('.json'):
        return await ctx.send("❌ Adjunta un archivo .json válido.")
    
    content = (await ctx.message.attachments[0].read()).decode('utf-8')
    success, msg = await data_manager.import_ranking(content)
    await ctx.send(msg)

# ==============================================================================
# 🚀 INICIO DEL SISTEMA
# ==============================================================================
if __name__ == "__main__":
    logger.info("🛰️ Iniciando servidor Flask (Keep-Alive)...")
    keep_alive()
    try:
        bot.run(Config.TOKEN)
    except Exception as e:
        logger.critical(f"❌ Fallo al iniciar Discord: {e}")
