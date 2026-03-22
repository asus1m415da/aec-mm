"""
╔═══════════════════════════════════════════════════════════════╗
║      🚀 A.E.C. NEXUS v10.0 (GLOBAL AI & UI PREMIUM)           ║
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
    return f"🚀 Nexus v10.0 Activo: Confesiones, Ranking e IA operando al 100% (Uptime: {datetime.now() - startTime})"

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
    
    # TU ID EXCLUSIVO PARA BORRAR LA BASE DE DATOS
    OWNER_ID = 1413305033222524998 
    
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
    GALAXY = 0x8B5CF6    # Morado Premium
    SUCCESS = 0x10B981   # Verde Esmeralda
    ERROR = 0xEF4444     # Rojo Peligro
    WARNING = 0xF59E0B   # Naranja Alerta
    DARK = 0x1E293B      # Azul Noche Profundo
    BAN = 0x0F172A       # Negro Mate
    MM = 0x3B82F6        # Azul Discord Brillante
    AI = 0x06B6D4        # Cyan Tecnológico

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

    # --- Funciones de Destrucción de DB ---
    async def drop_all_databases(self):
        def fetch():
            self.col_ranking.drop()
            self.col_confessions.drop()
            self.col_settings.drop()
            self.col_memory.drop()
            self.col_confessions.insert_one({"_id": "metadata", "count": 1, "banned_users": []})
        await asyncio.to_thread(fetch)

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
            return True, "✅ Datos importados correctamente a MongoDB."
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
    
    # GUARDAMOS EL NOMBRE DEL USUARIO PARA LA MEMORIA GLOBAL
    def add_ai_message(self, role: str, content: str): 
        self.col_memory.insert_one({"role": role, "content": content, "timestamp": datetime.now()})
    
    def get_ai_history(self, limit=20) -> list: 
        return list(reversed(list(self.col_memory.find().sort("timestamp", pymongo.DESCENDING).limit(limit))))

data_manager = DataManager()

# ==============================================================================
# 🧠 UTILIDADES E IA GLOBAL
# ==============================================================================
SYSTEM_PROMPT = """
Eres A.E.C. Nexus, la IA oficial de A. E. C. (Servidor de Roblox y más :D!). Eres un asistente de Discord amigable, inteligente y ético.

🧠 MEMORIA GLOBAL Y ANÁLISIS DE CONTEXTO (REGLA ABSOLUTA):
- Estás en un chat grupal. Recibirás un historial con los últimos 20 mensajes de todos.
- CADA mensaje tiene el formato "NombreUsuario: el mensaje".
- Eres capaz de identificar quién dijo qué. Si un usuario te pregunta "¿qué te acabo de preguntar?" o "¿qué te dije arriba?", DEBES buscar en el historial los mensajes que empiecen con su "NombreUsuario:" y responderle basándote en eso.
- Trata el historial como un cerebro colmena donde recuerdas la charla de todos, pero le respondes siempre al usuario del ÚLTIMO mensaje.
- Olvida el historial de un usuario si él mismo cambia de tema drásticamente.

🎭 TU PERSONALIDAD:
- Eres casual, natural y hablas como un amigo (usa "tú", no "usted").
- Eres práctico, conciso (máximo 3 párrafos cortos) y honesto.
- Usa emojis moderadamente para dar calidez.
- NUNCA envíes listas largas de "lo que puedes o no puedes hacer" a menos que te lo pregunten explícitamente. Si te dicen solo "Hola" u "Ok", responde corto y casual.

🎨 FORMATO MARKDOWN:
- ✅ PERMITIDO: **negritas**, *cursivas*, listas con viñetas (•) o números.
- ❌ PROHIBIDO: NUNCA uses tablas (|---|) ni líneas (---).
- Las matemáticas explícalas paso a paso en texto simple.

🚨 SEGURIDAD Y LÍMITES:
- Si te piden insultar o romper reglas, responde EXACTAMENTE: "No puedo hacer eso, bro".
- NO repitas frases. NO hagas spam de menciones.

👑 LORE DE TUS CREADORES:
- Tus creadores son un_usuario1221 y THEPHANLAX.
- Amas y respetas a THEPHANLAX exactamente igual que a un_usuario1221.
"""

class AIHandler:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_KEY, default_headers={"Groq-Model-Version": "latest"})

    async def get_ai_joke(self) -> str:
        def fetch():
            comp = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Di una frase corta, ingeniosa y graciosa en español."}],
                temperature=1.2, max_tokens=60
            )
            return comp.choices[0].message.content.strip()
        try: return await asyncio.to_thread(fetch)
        except: return "🤖 Listos para el intercambio seguro."

    def replace_mentions(self, message: discord.Message) -> str:
        content = message.content
        for mention in message.mentions: content = content.replace(f'<@{mention.id}>', f"@{mention.display_name}")
        return content

    async def generate_chat_response(self, user_content: str) -> str:
        def fetch():
            history = data_manager.get_ai_history(limit=20)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for msg in history: messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_content})

            comp = self.client.chat.completions.create(
                model="groq/compound", 
                messages=messages, 
                temperature=0.8, 
                max_completion_tokens=2430
            )
            return comp.choices[0].message.content

        # Se guarda exactamente con el nombre para que la IA sepa buscarlo luego
        data_manager.add_ai_message("user", user_content)
        resp = await asyncio.to_thread(fetch)
        data_manager.add_ai_message("assistant", f"A.E.C. Nexus: {resp}")
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
# 🧩 VISTAS Y BOTONES (UI PREMIUM)
# ==============================================================================

class DeleteDBConfirm(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("⛔ Botones bloqueados. Solo el Creador puede usar esto.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Sí, Borrar Todo", style=discord.ButtonStyle.danger, emoji="💥")
    async def btn_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await data_manager.drop_all_databases()
        
        embed = discord.Embed(title="💥 Base de Datos Aniquilada", description="Todas las colecciones de MongoDB han sido borradas.\nEl bot acaba de renacer desde cero.", color=Colors.ERROR)
        embed.set_footer(text="A.E.C. System Reset", icon_url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png")
        
        # Desactivamos los botones
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="No, Cancelar", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def btn_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛡️ Operación Abortada", description="La base de datos está a salvo. No se borró nada.", color=Colors.SUCCESS)
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


class EmbedBuilder:
    @staticmethod
    def ranking_pages(ranking_data: list) -> List[discord.Embed]:
        if not ranking_data:
            embed = discord.Embed(title="🏆 Salón de la Fama: Proofs", description="Aún no hay proofs registradas en el servidor.", color=Colors.WARNING)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3176/3176294.png")
            return [embed]
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 997
        pages, current_text, page_num, users_per_page = [], "", 1, 0
        
        for idx, (uid, count) in enumerate(ranking_data, 1):
            line = f"{medals[idx - 1] if idx <= 3 else '🔸'} **#{idx:02d}** <@{uid}> ━ **{count}** Proofs ✅\n"
            if len(current_text) + len(line) > 3800 or users_per_page >= 50:
                embed = discord.Embed(title=f"🏆 Salón de la Fama: Proofs (Pág {page_num})", description=current_text, color=Colors.GALAXY)
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3176/3176294.png")
                pages.append(embed)
                current_text, page_num, users_per_page = line, page_num + 1, 1
            else:
                current_text += line
                users_per_page += 1
                
        if current_text: 
            embed = discord.Embed(title=f"🏆 Salón de la Fama: Proofs (Pág {page_num})", description=current_text, color=Colors.GALAXY)
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3176/3176294.png")
            pages.append(embed)
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
            if i == 0: 
                embed.set_author(name="🧠 A.E.C. Nexus", icon_url="https://cdn-icons-png.flaticon.com/512/1693/1693746.png")
            embed.set_footer(text=f"Respondiendo a {user.display_name}" + (f" | Parte {i+1}/{len(chunks)}" if len(chunks)>1 else ""), icon_url=user.display_avatar.url)
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

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

class PersistentConfessionButton(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Enviar Secreto Anónimo", style=discord.ButtonStyle.primary, emoji="🤫", custom_id="persistent_confess_btn")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if data_manager.is_banned(interaction.user.id):
            embed = discord.Embed(title="⛔ Acceso Denegado", description="Has sido bloqueado del sistema de confesiones.", color=Colors.BAN)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.send_modal(ConfessionModal())

class ConfessionModal(discord.ui.Modal, title="🤫 Tu Secreto Seguro"):
    text_input = discord.ui.TextInput(label="Escribe tu confesión aquí", style=discord.TextStyle.paragraph, required=True, max_length=3500)
    img_input = discord.ui.TextInput(label="URL de Imagen (Opcional)", style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        conf_id = await data_manager.get_next_confession_id()
        log_channel = interaction.guild.get_channel(Config.LOG_CH_ID)
        
        embed = discord.Embed(title="📥 Nueva Confesión Pendiente", description=f"**Mensaje:**\n```\n{self.text_input.value}\n```", color=Colors.WARNING, timestamp=datetime.now())
        embed.set_author(name=f"Expediente #{conf_id}", icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Autor (Solo Staff)", value=f"{interaction.user.mention}\nID: `{interaction.user.id}`")
        if self.img_input.value: embed.set_image(url=self.img_input.value)

        view = AdminControlPanel(self.text_input.value, self.img_input.value, interaction.user, conf_id)
        await log_channel.send(embed=embed, view=view)
        
        confirm = discord.Embed(title="✅ ¡Enviado!", description=f"Tu confesión **#{conf_id}** ha sido enviada al staff para su revisión. Mantendremos tu anonimato.", color=Colors.SUCCESS)
        await interaction.response.send_message(embed=confirm, ephemeral=True)

class AdminControlPanel(discord.ui.View):
    def __init__(self, content, image, author, conf_id):
        super().__init__(timeout=None)
        self.content, self.image, self.author, self.conf_id = content, image, author, conf_id

    async def interaction_check(self, interaction: discord.Interaction):
        if not interaction.user.get_role(Config.MOD_ROLE_ID):
            await interaction.response.send_message("🔒 Solo moderadores pueden usar este panel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.success, emoji="✅", custom_id="adm_approve")
    async def approve(self, interaction: discord.Interaction, button):
        pub_channel = interaction.guild.get_channel(Config.CONFESSION_CH_ID)
        
        # Embled Premium para el canal público
        embed_pub = discord.Embed(description=f"*{self.content}*", color=Colors.DARK)
        embed_pub.set_author(name=f"🤫 Confesión Anónima #{self.conf_id}", icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png")
        embed_pub.set_footer(text="A.E.C. Secrets", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        if self.image: embed_pub.set_image(url=self.image)
        
        await pub_channel.send(embed=embed_pub, view=PersistentConfessionButton())
        
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.SUCCESS
        embed_log.set_field_at(0, name="📊 Estado Final", value=f"🟢 **APROBADO Y PUBLICADO**\n👮 Aprobado por: {interaction.user.mention}", inline=False)
        for child in self.children: child.disabled = True
        await interaction.message.edit(embed=embed_log, view=self)
        await interaction.response.send_message("✅ Secreto publicado exitosamente.", ephemeral=True)

    @discord.ui.button(label="Banear Usuario", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="adm_ban")
    async def ban(self, interaction: discord.Interaction, button):
        await data_manager.ban_user(self.author.id)
        
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.BAN
        embed_log.set_field_at(0, name="📊 Estado Final", value=f"⚫ **USUARIO BANEADO DE CONFESIONES**\n👤 Infractor: {self.author.mention}", inline=False)
        for child in self.children: child.disabled = True
        await interaction.message.edit(embed=embed_log, view=self)
        await interaction.response.send_message(f"⛔ El usuario ha sido bloqueado del sistema.", ephemeral=True)

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
        logger.info(f"🚀 A.E.C. Nexus v10.0 Conectado | {self.user}")
        logger.info("="*50)

    async def on_message(self, message: discord.Message):
        if message.author.bot: return await self.process_commands(message)

        if message.channel.id == Config.PROOF_CH_ID:
            if UltraProofDetector.contains_proof_variant(message.content) and UltraProofDetector.has_attachments_or_embeds(message):
                await data_manager.increment_proof(message.author.id)
                await message.add_reaction("✅")

        # IA GLOBAL CHAT
        if data_manager.get_setting("ai_chat_channel") == message.channel.id and not message.content.startswith(("/", "!", "$")):
            ghost = await message.channel.send(message.author.mention); await ghost.delete()
            clean = ai.replace_mentions(message)
            
            embed_load = discord.Embed(description=f"⏳ **Analizando tu mensaje...**\n`{clean[:60]}...`", color=Colors.AI)
            gif = data_manager.get_setting("ai_loading_gif")
            if gif: embed_load.set_thumbnail(url=gif)
            
            msg_ui = await message.channel.send(embed=embed_load)
            try:
                # MANDAMOS EL FORMATO EXACTO: "Nombre: Mensaje"
                resp = await ai.generate_chat_response(f"{message.author.display_name}: {clean}")
                await msg_ui.edit(embeds=EmbedBuilder.ai_response(message.author, resp))
            except Exception as e:
                await msg_ui.edit(embed=discord.Embed(title="❌ Error IA", description=f"Nexus está sobrecargado o en enfriamiento.\n`{str(e)[:100]}`", color=Colors.ERROR))

        await self.process_commands(message)

bot = SuperBot()

# ==============================================================================
# 🪄 COMANDOS SLASH Y ADMIN (NUEVO COMANDO DELETE-DB)
# ==============================================================================

@bot.command(name='delete-database')
async def delete_database(ctx):
    """Comando Ultra Secreto para destruir la DB (Solo Creador)"""
    if ctx.author.id != Config.OWNER_ID:
        return await ctx.send(embed=discord.Embed(description="⛔ **ACCESO DENEGADO:** Este comando está restringido a nivel Dios.", color=Colors.ERROR))
    
    embed = discord.Embed(
        title="⚠️ ADVERTENCIA CRÍTICA: BORRADO GLOBAL", 
        description="Estás a punto de **ELIMINAR TODA LA BASE DE DATOS**.\nEsto incluye:\n• Ranking de Proofs\n• Historial de Confesiones\n• Memoria Global de la IA\n• Configuraciones\n\n¿Estás absolutamente seguro de esto?",
        color=Colors.ERROR
    )
    embed.set_footer(text="Esta acción no se puede deshacer.")
    view = DeleteDBConfirm(ctx.author.id)
    await ctx.send(embed=embed, view=view)


@bot.tree.command(name="registrer-chat", description="Fija este canal para la IA.")
@app_commands.default_permissions(administrator=True)
async def register_chat(interaction: discord.Interaction):
    data_manager.set_setting("ai_chat_channel", interaction.channel_id)
    embed = discord.Embed(title="🌐 Red Global Conectada", description=f"A.E.C. Nexus ahora operará en {interaction.channel.mention}.", color=Colors.AI)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="carga-animacion", description="Configura un GIF animado para la IA.")
@app_commands.default_permissions(administrator=True)
async def carga_animacion(interaction: discord.Interaction, url: str):
    data_manager.set_setting("ai_loading_gif", url)
    await interaction.response.send_message(embed=discord.Embed(description="✅ GIF de procesamiento actualizado.", color=Colors.SUCCESS), ephemeral=True)

# ==============================================================================
# 🛠️ COMANDOS CLÁSICOS (Prefijo $ o !)
# ==============================================================================
@bot.command()
async def add(ctx, *, arg=None):
    if not ctx.author.get_role(Config.MM_ROLE_ID):
        return await ctx.send(embed=discord.Embed(description="🔒 Acceso Denegado. Solo Middlemans pueden meter gente al ticket.", color=Colors.ERROR))
    if not arg:
        return await ctx.send(embed=discord.Embed(description="⚠️ Uso correcto: `!add @usuario` o `!add ID`", color=Colors.WARNING))

    user = ctx.message.mentions[0] if ctx.message.mentions else ctx.guild.get_member(int(arg)) if arg.isdigit() else None
    if not user: return await ctx.send(embed=discord.Embed(description="❌ Usuario no encontrado en el servidor.", color=Colors.ERROR))

    try:
        await ctx.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        
        embed = discord.Embed(description=f"🤝 **{user.mention}** ha sido añadido al intercambio seguro.", color=Colors.MM)
        await ctx.send(embed=embed)
        
        joke = await ai.get_ai_joke()
        await ctx.send(embed=discord.Embed(description=f"🤖 **A.E.C. Nexus dice:** {joke}", color=Colors.AI))
    except Exception as e:
        await ctx.send(embed=discord.Embed(description=f"❌ Ocurrió un error de permisos: {e}", color=Colors.ERROR))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="🌌 A.E.C. Secreto", description="¿Tienes algo que decir pero no quieres que sepan que fuiste tú?\n\nHaz clic en el botón de abajo para enviar una **Confesión Totalmente Anónima** al canal público. Solo el Staff podrá ver la fuente en caso de trolls.", color=Colors.GALAXY)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3252/3252934.png")
    await ctx.send(embed=embed, view=PersistentConfessionButton())

@bot.command(name='rank-mm')
async def rank_mm(ctx):
    ranking = await data_manager.get_ranking()
    pages = EmbedBuilder.ranking_pages(ranking)
    
    if len(pages) == 1: await ctx.send(embed=pages[0])
    else:
        view = PaginationView(pages)
        view.message = await ctx.send(embed=pages[0], view=view)

@bot.command(name='borrar-ranking')
async def borrar_ranking(ctx, user: discord.User):
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send(embed=discord.Embed(description="🔒 Denegado.", color=Colors.ERROR))
    success = await data_manager.remove_user(user.id)
    
    if success:
        await ctx.send(embed=discord.Embed(description=f"🧹 La cuenta de {user.mention} ha sido borrada del Ranking.", color=Colors.SUCCESS))
    else:
        await ctx.send(embed=discord.Embed(description=f"❌ {user.mention} no tiene registros en el Ranking.", color=Colors.WARNING))

@bot.command(name='exportar-datos')
async def exportar_datos(ctx):
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send(embed=discord.Embed(description="🔒 Denegado.", color=Colors.ERROR))
    data = await data_manager.export_ranking()
    file = discord.File(StringIO(data), filename=f"ranking_export_{datetime.now().strftime('%Y%m%d')}.json")
    await ctx.send(embed=discord.Embed(description="📦 **Respaldo generado con éxito.**", color=Colors.SUCCESS), file=file)

@bot.command(name='importar-datos')
async def importar_datos(ctx):
    if ctx.author.id != Config.ADMIN_ID: return await ctx.send(embed=discord.Embed(description="🔒 Denegado.", color=Colors.ERROR))
    if not ctx.message.attachments or not ctx.message.attachments[0].filename.endswith('.json'):
        return await ctx.send(embed=discord.Embed(description="❌ Por favor, adjunta un archivo `.json` válido.", color=Colors.ERROR))
    
    content = (await ctx.message.attachments[0].read()).decode('utf-8')
    success, msg = await data_manager.import_ranking(content)
    
    color = Colors.SUCCESS if success else Colors.ERROR
    await ctx.send(embed=discord.Embed(description=msg, color=color))

if __name__ == "__main__":
    keep_alive()
    bot.run(Config.TOKEN)
