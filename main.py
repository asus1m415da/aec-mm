"""
╔═══════════════════════════════════════════════════════════════╗
║      🚀 GALAXY BOT ENTERPRISE & MM RANKING v9.1 (MASTER IA)   ║
║    Sistema Unificado: Moderación, Confesiones, Proofs & IA    ║
╚═══════════════════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from io import StringIO

# Integraciones de Base de Datos e IA
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from groq import Groq

# ==============================================================================
# 🌐 SERVIDOR WEB (KEEP ALIVE)
# ==============================================================================
app = Flask('')
startTime = datetime.now()

@app.route('/')
def home():
    return f"🚀 Súper Bot Activo: Confesiones, Ranking e IA operando al 100% (Uptime: {datetime.now() - startTime})"

def run():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run, daemon=True)
    t.start()

# ==============================================================================
# ⚙️ CONFIGURACIÓN Y LOGGING
# ==============================================================================
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_KEY = os.getenv("GROQ_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    
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
    AI = 0x00B0F4

# ==============================================================================
# 💾 GESTOR DE DATOS MONGODB ATLAS
# ==============================================================================
class DataManager:
    def __init__(self):
        try:
            self.client = MongoClient(Config.MONGO_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client["AEC_Database"]
            
            self.col_ranking = self.db["ranking"]
            self.col_confessions = self.db["confessions"]
            self.col_settings = self.db["settings"]
            self.col_memory = self.db["ai_memory"]
            
            if not self.col_confessions.find_one({"_id": "metadata"}):
                self.col_confessions.insert_one({"_id": "metadata", "count": 1, "banned_users": []})
            logger.info("✅ Base de Datos MongoDB Atlas conectada.")
        except Exception as e:
            logger.critical(f"❌ Error DB: {e}")
            exit(1)

    # --- Ranking ---
    async def increment_proof(self, user_id: int):
        await asyncio.to_thread(self.col_ranking.update_one, {"_id": str(user_id)}, {"$inc": {"count": 1}}, upsert=True)

    async def remove_user(self, user_id: int) -> bool:
        res = await asyncio.to_thread(self.col_ranking.delete_one, {"_id": str(user_id)})
        return res.deleted_count > 0

    async def get_ranking(self) -> list:
        def fetch(): return [(int(doc["_id"]), doc["count"]) for doc in self.col_ranking.find().sort("count", pymongo.DESCENDING)]
        return await asyncio.to_thread(fetch)

    async def export_ranking(self) -> str:
        data = await self.get_ranking()
        export_data = {str(uid): count for uid, count in data}
        return json.dumps(export_data, indent=2, ensure_ascii=False)

    async def import_ranking(self, json_str: str) -> Tuple[bool, str]:
        try:
            new_data = json.loads(json_str)
            for uid, count in new_data.items():
                if int(count) >= 0:
                    self.col_ranking.update_one({"_id": str(uid)}, {"$set": {"count": int(count)}}, upsert=True)
            return True, f"✅ Datos importados correctamente a MongoDB."
        except Exception as e:
            return False, f"❌ Error importando: {e}"

    # --- Confesiones ---
    async def get_next_confession_id(self):
        def fetch():
            res = self.col_confessions.find_one_and_update({"_id": "metadata"}, {"$inc": {"count": 1}}, return_document=pymongo.ReturnDocument.AFTER)
            return res["count"] - 1
        return await asyncio.to_thread(fetch)

    def is_banned(self, user_id: int) -> bool:
        return user_id in self.col_confessions.find_one({"_id": "metadata"}).get("banned_users", [])

    async def ban_user(self, user_id: int):
        await asyncio.to_thread(self.col_confessions.update_one, {"_id": "metadata"}, {"$addToSet": {"banned_users": user_id}})

    # --- Memoria IA ---
    def set_setting(self, key: str, value: any): self.col_settings.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)
    def get_setting(self, key: str, default=None): doc = self.col_settings.find_one({"_id": key}); return doc["value"] if doc else default
    def add_ai_message(self, role: str, content: str): self.col_memory.insert_one({"role": role, "content": content, "timestamp": datetime.now()})
    def get_ai_history(self, limit=8) -> list: return list(reversed(list(self.col_memory.find().sort("timestamp", pymongo.DESCENDING).limit(limit))))

data_manager = DataManager()

# ==============================================================================
# 🧠 UTILIDADES E IA
# ==============================================================================
SYSTEM_PROMPT = """
Eres A.E.C. Nexus, la IA Oficial de A. E. C. (Android Edit Community).
Estás en un CHAT GRUPAL. Los usuarios enviarán mensajes con el formato "Nombre: mensaje".
REGLAS ESTRICTAS PARA TI:
1. RESPONDE SIEMPRE EN ESPAÑOL. Nunca respondas en inglés.
2. Fíjate muy bien en el nombre de quien envía el ÚLTIMO mensaje y responde directamente a esa persona.
3. NO inventes comandos (nada de /ayuda, /info, etc.). Eres un asistente conversacional, no un menú de comandos.
4. Defiende las reglas: Sentido común, respeto, orden, cero flood, cero publicidad, prohibido el NSFW, GORE y actividades ilegales. No des Robux gratis.
5. Usa formato Markdown (#, **, *), emojis para animar, y sé amigable pero firme.
"""

class AIHandler:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_KEY, default_headers={"Groq-Model-Version": "latest"})

    async def get_ai_joke(self) -> str:
        """El chiste original para el comando !add"""
        def fetch():
            comp = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Di una frase corta, ingeniosa y graciosa en español."}],
                temperature=1.2, max_tokens=60
            )
            return comp.choices[0].message.content.strip()
        try: return await asyncio.to_thread(fetch)
        except: return "La IA está durmiendo... 😴"

    def replace_mentions(self, message: discord.Message) -> str:
        content = message.content
        for mention in message.mentions: content = content.replace(f'<@{mention.id}>', f"@{mention.display_name}")
        return content

    async def generate_chat_response(self, user_content: str) -> str:
        def fetch():
            history = data_manager.get_ai_history(limit=8) # Memoria más corta para no saturarla
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for msg in history: messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_content})

            # Temperatura a 0.7 para que sea lógica y deje de alucinar cosas en inglés o comandos raros
            comp = self.client.chat.completions.create(model="groq/compound-mini", messages=messages, temperature=0.7, max_completion_tokens=2000)
            return comp.choices[0].message.content

        data_manager.add_ai_message("user", user_content)
        resp = await asyncio.to_thread(fetch)
        data_manager.add_ai_message("assistant", resp)
        return resp

ai = AIHandler()

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
# 🧩 COMPONENTES DE UI (Rankings, Confesiones e IA)
# ==============================================================================
class EmbedBuilder:
    @staticmethod
    def ranking_pages(ranking_data: list) -> List[discord.Embed]:
        if not ranking_data:
            return [discord.Embed(title="🏆 RANKING DE PROOFS", description="Sin datos", color=Colors.WARNING)]
        
        medals = ["🥇", "🥈", "🥉"] + ["#️⃣"] * 997
        pages, current_text, page_num, users_per_page = [], "", 1, 0
        
        for idx, (uid, count) in enumerate(ranking_data, 1):
            line = f"{medals[idx - 1] if idx <= 3 else '▫️'} `#{idx:02d}` <@{uid}> • **{count}** ✅\n"
            if len(current_text) + len(line) > 3900 or users_per_page >= 50:
                pages.append(discord.Embed(title=f"🏆 RANKING DE PROOFS (Pág {page_num})", description=current_text, color=Colors.RANK))
                current_text, page_num, users_per_page = line, page_num + 1, 1
            else:
                current_text += line
                users_per_page += 1
                
        if current_text: pages.append(discord.Embed(title=f"🏆 RANKING DE PROOFS (Pág {page_num})", description=current_text, color=Colors.RANK))
        return pages

    @staticmethod
    def ai_response(user: discord.Member, response: str) -> list[discord.Embed]:
        chunks, max_chars, text = [], 3900, response
        while len(text) > max_chars:
            split_idx = text.rfind('\n', 0, max_chars)
            if split_idx == -1: split_idx = text.rfind(' ', 0, max_chars)
            if split_idx == -1: split_idx = max_chars
            chunks.append(text[:split_idx].strip())
            text = text[split_idx:].strip()
        if text: chunks.append(text)
            
        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(description=chunk, color=Colors.AI)
            if i == 0: embed.set_author(name="🧠 A.E.C. Nexus", icon_url="https://cdn-icons-png.flaticon.com/512/1693/1693746.png")
            embed.set_footer(text=f"Respuesta para {user.display_name} | Parte {i+1}/{len(chunks)}" if len(chunks)>1 else f"Respuesta para {user.display_name}", icon_url=user.display_avatar.url)
            embeds.append(embed)
        return embeds

class PaginationView(discord.ui.View):
    def __init__(self, pages: List[discord.Embed]):
        super().__init__(timeout=180.0)
        self.pages = pages
        self.current_page = 0
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
    def __init__(self): super().__init__(timeout=None)
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
        self.content, self.image, self.author, self.conf_id = content, image, author, conf_id

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
        super().__init__(command_prefix=["$", "!"], help_command=None, intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentConfessionButton())
        await self.tree.sync()
        logger.info("✅ Hooks, Vistas y Comandos Slash cargados.")

    async def on_ready(self):
        logger.info("="*50)
        logger.info(f"🚀 Súper Bot Conectado | {self.user}")
        logger.info("="*50)

    async def on_message(self, message: discord.Message):
        if message.author.bot: return await self.process_commands(message)

        # 🔍 DETECCIÓN DE PROOFS
        if message.channel.id == Config.PROOF_CH_ID:
            if UltraProofDetector.contains_proof_variant(message.content) and UltraProofDetector.has_attachments_or_embeds(message):
                await data_manager.increment_proof(message.author.id)
                await message.add_reaction("✅")

        # 🧠 CHAT IA GLOBAL
        if data_manager.get_setting("ai_chat_channel") == message.channel.id and not message.content.startswith(("/", "!", "$")):
            ghost = await message.channel.send(message.author.mention); await ghost.delete()
            clean = ai.replace_mentions(message)
            
            embed_load = discord.Embed(title="✨ Analizando...", description=f"**{message.author.display_name}:**\n*{clean[:100]}...*\n\n⏳ **Pensando...**", color=Colors.AI)
            gif = data_manager.get_setting("ai_loading_gif")
            if gif: embed_load.set_thumbnail(url=gif)
            
            msg_ui = await message.channel.send(embed=embed_load)
            try:
                resp = await ai.generate_chat_response(f"{message.author.display_name}: {clean}")
                # Corrección del error 'Cannot mix embed and embeds' usando embed=None explícitamente
                await msg_ui.edit(embed=None, embeds=EmbedBuilder.ai_response(message.author, resp))
            except Exception as e:
                await msg_ui.edit(embed=discord.Embed(title="❌ Error IA", description=f"`{e}`", color=Colors.ERROR))

        await self.process_commands(message)

bot = SuperBot()

# ==============================================================================
# 🪄 COMANDOS SLASH (IA)
# ==============================================================================
@bot.tree.command(name="registrer-chat", description="Fija este canal para la IA.")
@app_commands.default_permissions(administrator=True)
async def register_chat(interaction: discord.Interaction):
    data_manager.set_setting("ai_chat_channel", interaction.channel_id)
    await interaction.response.send_message("✅ Canal registrado para la IA.")

@bot.tree.command(name="carga-animacion", description="Configura un GIF animado para la IA.")
@app_commands.default_permissions(administrator=True)
async def carga_animacion(interaction: discord.Interaction, url: str):
    data_manager.set_setting("ai_loading_gif", url)
    await interaction.response.send_message("✅ GIF actualizado.", ephemeral=True)

# ==============================================================================
# 🛠️ COMANDOS CLÁSICOS (Prefijo $ o !)
# ==============================================================================
@bot.command()
async def add(ctx, *, arg=None):
    """Añade a un usuario al ticket (Solo Middlemans)"""
    if not ctx.author.get_role(Config.MM_ROLE_ID):
        return await ctx.send(embed=discord.Embed(description="🔒 Acceso Denegado. Solo Middlemans.", color=Colors.ERROR))
    if not arg:
        return await ctx.send(embed=discord.Embed(description="⚠️ Uso: `!add @usuario` o ID.", color=Colors.WARNING))

    user = ctx.message.mentions[0] if ctx.message.mentions else ctx.guild.get_member(int(arg)) if arg.isdigit() else None
    if not user: return await ctx.send("❌ Usuario no encontrado.")

    try:
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        await ctx.send(embed=discord.Embed(description=f"✅ **{user.mention}** añadido al ticket.", color=Colors.MM))
        # El chiste clásico original
        joke = await ai.get_ai_joke()
        await ctx.send(embed=discord.Embed(description=f"🤖 **IA:** {joke}", color=Colors.GALAXY))
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Instala el panel de confesiones"""
    await ctx.message.delete()
    embed = discord.Embed(title="🌌 Confesiones A.E.C", description="Haz clic en el botón para enviar una confesión anónima.", color=Colors.GALAXY)
    await ctx.send(embed=embed, view=PersistentConfessionButton())

@bot.command(name='rank-mm')
async def rank_mm(ctx):
    """Muestra el ranking de proofs con paginación"""
    ranking = await data_manager.get_ranking()
    pages = EmbedBuilder.ranking_pages(ranking)
    
    if len(pages) == 1: await ctx.send(embed=pages[0])
    else:
        view = PaginationView(pages)
        view.message = await ctx.send(embed=pages[0], view=view)

@bot.command(name='borrar-ranking')
async def borrar_ranking(ctx, user: discord.User):
    """Borra a un usuario del ranking (Solo Admin)"""
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send("🔒 Denegado.")
    success = await data_manager.remove_user(user.id)
    await ctx.send(f"✅ {user.mention} eliminado del ranking." if success else f"❌ {user.mention} no estaba.")

@bot.command(name='exportar-datos')
async def exportar_datos(ctx):
    """Exporta el JSON del ranking desde MongoDB (Solo Admin)"""
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send("🔒 Denegado.")
    data = await data_manager.export_ranking()
    file = discord.File(StringIO(data), filename=f"ranking_export_{datetime.now().strftime('%Y%m%d')}.json")
    await ctx.send("✅ Exportado desde MongoDB:", file=file)

@bot.command(name='importar-datos')
async def importar_datos(ctx):
    """Importa un JSON para el ranking hacia MongoDB (Solo Admin)"""
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send("🔒 Denegado.")
    if not ctx.message.attachments or not ctx.message.attachments[0].filename.endswith('.json'):
        return await ctx.send("❌ Adjunta un archivo .json válido.")
    
    content = (await ctx.message.attachments[0].read()).decode('utf-8')
    success, msg = await data_manager.import_ranking(content)
    await ctx.send(msg)

if __name__ == "__main__":
    keep_alive()
    bot.run(Config.TOKEN)
