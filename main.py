"""
╔═══════════════════════════════════════════════════════════════╗
║      🚀 GALAXY BOT ENTERPRISE & MM RANKING v4.0 (MONGO+AI)    ║
║    Sistema Unificado: Moderación, Confesiones, Proofs & IA    ║
╚═══════════════════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import pymongo
import pymongo.errors
from groq import Groq

# ==============================================================================
# 🌐 SERVIDOR WEB (KEEP ALIVE)
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "🚀 Súper Bot V4 Activo: Confesiones, Ranking y MongoDB IA al 100%"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
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
    
    GUILD_ID = int(os.getenv("GUILD_ID", 0))
    CONFESSION_CH_ID = int(os.getenv("CONFESSION_CHANNEL_ID", 0))
    LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID", 0))
    MM_ROLE_ID = int(os.getenv("MM_ROLE_ID", 0))
    MOD_ROLE_ID = int(os.getenv("MODERATOR_ROLE_ID", 0))
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    PROOF_CH_ID = int(os.getenv("PROOF_CHANNEL_ID", 0))

class Colors:
    GALAXY = 0x6A0DAD
    SUCCESS = 0x43B581
    ERROR = 0xF04747
    WARNING = 0xFAA61A
    DARK = 0x2B2D31
    BAN = 0x000000
    MM = 0x5865F2
    AI = 0x00FFDD

# ==============================================================================
# 💾 GESTOR DE DATOS MONGODB UNIFICADO
# ==============================================================================
class MongoDBManager:
    def __init__(self):
        try:
            self.client = pymongo.MongoClient(Config.MONGO_URI)
            self.db = self.client["GalaxyBotDB"]
            
            # Colecciones
            self.col_ranking = self.db["ranking"]
            self.col_confessions = self.db["confessions"]
            self.col_settings = self.db["settings"]
            self.col_memory = self.db["ai_memory"]
            
            # Setup inicial si no existe
            if not self.col_confessions.find_one({"_id": "metadata"}):
                self.col_confessions.insert_one({"_id": "metadata", "count": 1, "banned_users": []})
                
            logger.info("✅ Conectado a MongoDB Atlas exitosamente.")
        except pymongo.errors.ConfigurationError:
            logger.critical("❌ ERROR: URI de MongoDB inválida en el .env")
            exit(1)

    # --- Ranking ---
    async def increment_proof(self, user_id: int):
        self.col_ranking.update_one(
            {"_id": str(user_id)},
            {"$inc": {"count": 1}},
            upsert=True
        )

    async def get_ranking(self) -> list:
        data = self.col_ranking.find().sort("count", pymongo.DESCENDING)
        return [(int(doc["_id"]), doc["count"]) for doc in data]

    async def remove_user(self, user_id: int) -> bool:
        result = self.col_ranking.delete_one({"_id": str(user_id)})
        return result.deleted_count > 0

    # --- Confesiones ---
    async def get_next_confession_id(self):
        result = self.col_confessions.find_one_and_update(
            {"_id": "metadata"},
            {"$inc": {"count": 1}},
            return_document=pymongo.ReturnDocument.AFTER
        )
        return result["count"] - 1

    def is_banned(self, user_id: int) -> bool:
        meta = self.col_confessions.find_one({"_id": "metadata"})
        return user_id in meta.get("banned_users", [])

    async def ban_user(self, user_id: int):
        self.col_confessions.update_one(
            {"_id": "metadata"},
            {"$addToSet": {"banned_users": user_id}}
        )

    # --- Ajustes Bot (IA Chat) ---
    def set_setting(self, key: str, value: any):
        self.col_settings.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

    def get_setting(self, key: str, default=None):
        doc = self.col_settings.find_one({"_id": key})
        return doc["value"] if doc else default

    # --- Memoria IA ---
    def add_ai_message(self, role: str, content: str):
        self.col_memory.insert_one({"role": role, "content": content, "timestamp": datetime.now()})
        
    def get_ai_history(self, limit=20) -> list:
        docs = self.col_memory.find().sort("timestamp", pymongo.DESCENDING).limit(limit)
        return list(reversed(list(docs)))

db = MongoDBManager()

# ==============================================================================
# 🧠 UTILIDADES E IA
# ==============================================================================
class AIHandler:
    def __init__(self):
        self.client = Groq(
            api_key=Config.GROQ_KEY,
            default_headers={"Groq-Model-Version": "latest"}
        )
        
    def replace_mentions(self, message: discord.Message) -> str:
        """Cambia <@123> por @NombreUsuario para que la IA entienda de quién hablan."""
        content = message.content
        for mention in message.mentions:
            display = f"@{mention.display_name} (del servidor)"
            content = content.replace(f'<@{mention.id}>', display).replace(f'<@!{mention.id}>', display)
        return content

    async def generate_response(self, user_content: str) -> str:
        def fetch():
            # Construir mensajes con memoria global
            history = db.get_ai_history(limit=15)
            messages = [{"role": "system", "content": "Eres una IA compartida y amigable en un servidor de Discord. Respondes con carisma, en español correcto, y ayudas en lo que pidan."}]
            
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
            messages.append({"role": "user", "content": user_content})

            # Llamada exacta a la API solicitada
            completion = self.client.chat.completions.create(
                model="groq/compound-mini",
                messages=messages,
                temperature=1.11,
                max_completion_tokens=3281,
                top_p=1,
                stream=False,
                stop=None,
                compound_custom={"tools":{"enabled_tools":["web_search","code_interpreter","visit_website","browser_automation"]}}
            )
            return completion.choices[0].message.content

        # Guardar mensaje del usuario
        db.add_ai_message("user", user_content)
        
        # Generar respuesta sin bloquear Discord
        response = await asyncio.to_thread(fetch)
        
        # Guardar respuesta de la IA
        db.add_ai_message("assistant", response)
        return response

    async def get_joke(self) -> str:
        def fetch():
            comp = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Di una frase corta, ingeniosa y graciosa en español."}],
                temperature=1.2,
                max_tokens=60
            )
            return comp.choices[0].message.content.strip()
        try:
            return await asyncio.to_thread(fetch)
        except Exception:
            return "La IA está durmiendo... 😴"

ai = AIHandler()

class UltraProofDetector:
    @staticmethod
    def contains_proof_variant(text: str) -> bool:
        if not text: return False
        normalized = text.lower().strip()
        patterns = [r'pr[o0]f+', r'proof', r'proff', r'pr\s*[o0]\s*f+', r'p\s*r\s*[o0]\s*f+', r'#\d+', r'p[r0][o0]f{1,2}']
        return any(re.search(p, normalized, re.IGNORECASE) for p in patterns) or "proof" in normalized

    @staticmethod
    def has_attachments(message: discord.Message) -> bool:
        return len(message.attachments) > 0 or len(message.embeds) > 0

# ==============================================================================
# 🤖 BOT PRINCIPAL Y EVENTOS
# ==============================================================================
class SuperBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix=["$", "!"], help_command=None, intents=intents)

    async def setup_hook(self):
        # self.add_view(PersistentConfessionButton()) # Debes agregar tu UI de confesiones aquí igual que antes
        await self.tree.sync()
        logger.info("✅ Slash commands sincronizados y Hooks cargados.")

    async def on_ready(self):
        logger.info("="*50)
        logger.info(f"🚀 Súper Bot V4 Conectado | {self.user}")
        logger.info("MongoDB & Groq AI: ONLINE")
        logger.info("="*50)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return await self.process_commands(message)

        # 🔍 SISTEMA DE PROOFS
        if message.channel.id == Config.PROOF_CH_ID:
            if UltraProofDetector.contains_proof_variant(message.content) and UltraProofDetector.has_attachments(message):
                await db.increment_proof(message.author.id)
                await message.add_reaction("✅")

        # 🤖 SISTEMA DE CHAT IA GLOBAL
        ai_channel_id = db.get_setting("ai_chat_channel")
        if ai_channel_id and message.channel.id == ai_channel_id:
            if not message.content.startswith(("/", "!", "$")):
                # 1. Ghost Ping (etiqueta y borra al instante)
                ghost_ping = await message.channel.send(message.author.mention)
                await ghost_ping.delete()

                # 2. Reemplazar menciones en el texto
                clean_text = ai.replace_mentions(message)
                
                # 3. Embed de Carga Animado
                loading_gif = db.get_setting("ai_loading_gif")
                embed = discord.Embed(
                    title=f"🗣️ {message.author.display_name} preguntó:",
                    description=f"*{clean_text[:200]}...*\n\n🔄 **Procesando respuesta...**",
                    color=Colors.AI
                )
                if loading_gif:
                    embed.set_thumbnail(url=loading_gif)
                    
                status_msg = await message.channel.send(embed=embed)

                try:
                    # 4. Generar Respuesta
                    respuesta = await ai.generate_response(f"Usuario {message.author.display_name} dice: {clean_text}")
                    
                    # 5. Editar el mismo Embed
                    embed.description = f"**Respuesta:**\n{respuesta}"
                    embed.set_thumbnail(url=None) # Quitamos el logo de carga para dejarlo limpio
                    embed.set_footer(text=f"Respondido a {message.author.display_name}", icon_url=message.author.display_avatar.url)
                    await status_msg.edit(embed=embed)
                except Exception as e:
                    embed.description = "❌ Ocurrió un error al conectar con mis circuitos cerebrales."
                    embed.color = Colors.ERROR
                    await status_msg.edit(embed=embed)
                    logger.error(f"Error IA: {e}")

        await self.process_commands(message)

bot = SuperBot()

# ==============================================================================
# 🪄 COMANDOS SLASH (NUEVOS)
# ==============================================================================
@bot.tree.command(name="registrer-chat", description="Registra el canal actual como el chat principal de la IA.")
@app_commands.default_permissions(administrator=True)
async def register_chat(interaction: discord.Interaction):
    db.set_setting("ai_chat_channel", interaction.channel_id)
    embed = discord.Embed(
        title="🧠 Canal de IA Vinculado",
        description="Este canal ahora es el núcleo de mi memoria compartida. ¡Hablen conmigo sin usar comandos!",
        color=Colors.SUCCESS
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="carga-animacion", description="Añade un GIF para la pantalla de carga de la IA.")
@app_commands.describe(url="URL directa del GIF animado")
@app_commands.default_permissions(administrator=True)
async def carga_animacion(interaction: discord.Interaction, url: str):
    if not url.startswith("http"):
        return await interaction.response.send_message("❌ Debes proporcionar una URL válida.", ephemeral=True)
    
    db.set_setting("ai_loading_gif", url)
    embed = discord.Embed(
        title="✨ Animación Actualizada",
        description="Esta animación se mostrará mientras proceso las respuestas.",
        color=Colors.GALAXY
    )
    embed.set_thumbnail(url=url)
    await interaction.response.send_message(embed=embed)

# ==============================================================================
# 🛠️ COMANDOS CLÁSICOS (MOD/RANKING)
# ==============================================================================
@bot.command()
async def add(ctx, *, arg=None):
    if not ctx.author.get_role(Config.MM_ROLE_ID):
        return await ctx.send(embed=discord.Embed(description="🔒 Acceso Denegado.", color=Colors.ERROR))
    # ... Tu lógica de $add anterior aquí ...
    joke = await ai.get_joke()
    await ctx.send(embed=discord.Embed(description=f"🤖 **IA:** {joke}", color=Colors.GALAXY))

@bot.command(name='rank-mm')
async def rank_mm(ctx):
    ranking = await db.get_ranking()
    if not ranking:
        return await ctx.send(embed=discord.Embed(title="🏆 RANKING", description="Sin datos", color=Colors.WARNING))
    
    texto = ""
    for idx, (uid, count) in enumerate(ranking[:20], 1): # Top 20 de ejemplo
        texto += f"`#{idx:02d}` <@{uid}> • **{count}** ✅\n"
        
    embed = discord.Embed(title="🏆 RANKING DE PROOFS - GLOBAL", description=texto, color=Colors.GALAXY)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    logger.info("🛰️ Iniciando sistema...")
    keep_alive()
    bot.run(Config.TOKEN)
