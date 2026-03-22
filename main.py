"""
╔═══════════════════════════════════════════════════════════════╗
║      🚀 GALAXY BOT ENTERPRISE & MM RANKING v7.0 (MASTER)      ║
║    Sistema Unificado: Moderación, Confesiones, Proofs & IA    ║
║           Motor: MongoDB Atlas (ServerApi v1) + Groq          ║
╚═══════════════════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Importaciones de MongoDB (Plantilla Oficial Estricta)
import pymongo
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Importación de IA
from groq import Groq

# ==============================================================================
# 🌐 SERVIDOR WEB (KEEP ALIVE BLINDADO)
# ==============================================================================
app = Flask(__name__)
startTime = datetime.now()

@app.route('/')
def home():
    uptime = datetime.now() - startTime
    return f"<h2>✨ GALAXY BOT v7.0 MASTER ONLINE</h2><p>Uptime: {uptime}</p><p>Estado: Sistemas de IA y MongoDB Operativos al 100%.</p>"

def run_web_server():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Apagamos logs molestos de la web
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==============================================================================
# ⚙️ CONFIGURACIÓN GLOBAL Y LOGGING
# ==============================================================================
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-7s | %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('GalaxyBot')

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    GROQ_KEY = os.getenv("GROQ_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    
    # IDs de la comunidad A.E.C.
    GUILD_ID = int(os.getenv("GUILD_ID", 0))
    MM_ROLE_ID = int(os.getenv("MM_ROLE_ID", 0))
    PROOF_CH_ID = int(os.getenv("PROOF_CHANNEL_ID", 0))

class Colors:
    MAIN = 0x2B2D31
    SUCCESS = 0x43B581
    ERROR = 0xF04747
    AI = 0x00B0F4     # Azul Cyan para la IA
    RANK = 0xFFD700   # Dorado para el Top

# ==============================================================================
# 🎨 EMBED FACTORY (Interfaz Premium y División Inteligente)
# ==============================================================================
class EmbedFactory:
    @staticmethod
    def ai_loading(user: discord.Member, query: str, gif_url: str = None) -> discord.Embed:
        clean_query = query[:100] + "..." if len(query) > 100 else query
        embed = discord.Embed(
            title="✨ ¡Analizando tu mensaje!",
            description=f"**{user.display_name} dice:**\n*{clean_query}*\n\n⏳ **La IA está procesando una respuesta genial...**",
            color=Colors.AI
        )
        if gif_url:
            embed.set_thumbnail(url=gif_url)
        return embed

    @staticmethod
    def ai_response(user: discord.Member, response: str) -> list[discord.Embed]:
        """Divide textos inmensos en múltiples Embeds sin cortar palabras por la mitad."""
        chunks = []
        max_chars = 3900 # Límite ultra-seguro
        text = response
        
        while len(text) > max_chars:
            # Buscar el último salto de línea para cortar un párrafo limpio
            split_idx = text.rfind('\n', 0, max_chars)
            if split_idx == -1:
                # Si no hay saltos, buscar el último espacio
                split_idx = text.rfind(' ', 0, max_chars)
            if split_idx == -1:
                # Corte forzado si es una cadena sin espacios (raro)
                split_idx = max_chars
            
            chunks.append(text[:split_idx].strip())
            text = text[split_idx:].strip()
        
        if text:
            chunks.append(text)
            
        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(description=chunk, color=Colors.AI)
            
            # Solo el primer fragmento lleva el título general
            if i == 0:
                embed.set_author(name="🧠 A.E.C. Inteligencia Artificial", icon_url="https://cdn-icons-png.flaticon.com/512/1693/1693746.png")
            
            # Numeración de partes si hay más de un fragmento
            footer_text = f"Respuesta para {user.display_name} ✨"
            if len(chunks) > 1:
                footer_text += f" | Parte {i+1}/{len(chunks)}"
                
            embed.set_footer(text=footer_text, icon_url=user.display_avatar.url)
            embeds.append(embed)
            
        return embeds

    @staticmethod
    def success(title: str, desc: str) -> discord.Embed:
        return discord.Embed(title=f"✅ {title}", description=desc, color=Colors.SUCCESS)

    @staticmethod
    def error(title: str, desc: str) -> discord.Embed:
        return discord.Embed(title=f"❌ {title}", description=desc, color=Colors.ERROR)

# ==============================================================================
# 💾 MONGODB MANAGER (Motor Oficial Atlas v1 Estricto)
# ==============================================================================
class MongoDBManager:
    def __init__(self):
        try:
            self.client = MongoClient(
                Config.MONGO_URI, 
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=5000
            )
            self.client.admin.command('ping')
            logger.info("✅ Ping exitoso. Conectado a MongoDB Atlas (API v1).")

            self.db = self.client["AEC_Database"]
            self.col_ranking = self.db["ranking"]
            self.col_settings = self.db["settings"]
            self.col_memory = self.db["ai_memory"]
            
        except Exception as e:
            logger.critical(f"❌ ERROR CRÍTICO MONGODB: {e}")
            exit(1)

    async def increment_proof(self, user_id: int):
        await asyncio.to_thread(
            self.col_ranking.update_one,
            {"_id": str(user_id)},
            {"$inc": {"count": 1}},
            upsert=True
        )

    async def get_ranking(self) -> list:
        def fetch():
            cursor = self.col_ranking.find().sort("count", pymongo.DESCENDING)
            return [(int(doc["_id"]), doc["count"]) for doc in cursor]
        return await asyncio.to_thread(fetch)

    def set_setting(self, key: str, value: any):
        self.col_settings.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

    def get_setting(self, key: str, default=None):
        doc = self.col_settings.find_one({"_id": key})
        return doc["value"] if doc else default

    def add_ai_message(self, role: str, content: str):
        self.col_memory.insert_one({"role": role, "content": content, "timestamp": datetime.now()})

    def get_ai_history(self, limit=12) -> list:
        docs = self.col_memory.find().sort("timestamp", pymongo.DESCENDING).limit(limit)
        return list(reversed(list(docs)))

db = MongoDBManager()

# ==============================================================================
# 🧠 CEREBRO IA (GROQ) Y SYSTEM PROMPT DE A.E.C.
# ==============================================================================
SYSTEM_PROMPT = """
Eres el Asistente Oficial de A. E. C. (Android Edit Community). Eres alegre, respetuoso y enérgico ✨.
Reglamento a defender:
1. Sentido común: reportar si algo incomoda.
2. Respeto y buen comportamiento (sino, warns/bans).
3. Orden: no flood, no spam de emojis.
4. Seguir normativas de Discord.
5. Cero publicidad y links ajenos.
6. Prohibido enviar scripts/código ejecutable.
7. Cero conflictos y respeto absoluto al staff 👮.
8. Prohibido NSFW, GORE, SPAM e ILEGALIDADES.
Sanciones: 3 warns = 1 kick. 1 kick + 3 warns = Ban definitivo.
Formato OBLIGATORIO: Usa Markdown (#, ##, **, *), emojis para animar el texto, || para secretos y ` ` para comandos. NO ofrezcas debatir castigos, diles que abran un ticket 🎫.
"""

class AIHandler:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_KEY, default_headers={"Groq-Model-Version": "latest"})
        
    def replace_mentions(self, message: discord.Message) -> str:
        content = message.content
        for mention in message.mentions:
            display = f"@{mention.display_name}"
            content = content.replace(f'<@{mention.id}>', display).replace(f'<@!{mention.id}>', display)
        return content

    async def generate_response(self, user_content: str) -> str:
        def fetch():
            history = db.get_ai_history()
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": user_content})

            completion = self.client.chat.completions.create(
                model="groq/compound-mini",
                messages=messages,
                temperature=1.1,
                max_completion_tokens=3281,
                top_p=1,
                stream=False
            )
            return completion.choices[0].message.content

        db.add_ai_message("user", user_content)
        response = await asyncio.to_thread(fetch)
        db.add_ai_message("assistant", response)
        return response

ai = AIHandler()

# ==============================================================================
# 🤖 NÚCLEO DEL BOT Y EVENTOS PRINCIPALES
# ==============================================================================
class SuperBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=["$", "!"], help_command=None, intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("✅ Comandos de barra (Slash) sincronizados con éxito.")

    async def on_ready(self):
        logger.info("="*50)
        logger.info(f"🚀 A.E.C. BOT v7.0 ONLINE | Identidad: {self.user}")
        logger.info("="*50)

    async def on_command_error(self, ctx, error):
        """Manejo global de errores para evitar crasheos y dar feedback bonito."""
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=EmbedFactory.error("¡Demasiado rápido! ⏳", f"Por favor, espera `{error.retry_after:.1f}` segundos antes de volver a usar este comando."), delete_after=6)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=EmbedFactory.error("Acceso Denegado 🛑", "Tus permisos no son suficientes para ejecutar esta acción."))

    async def on_message(self, message: discord.Message):
        if message.author.bot: return

        # --- 1. RANKING AUTOMÁTICO DE PROOFS ---
        if message.channel.id == Config.PROOF_CH_ID:
            # Validación estricta: debe contener la palabra proof y tener una imagen/archivo
            if "proof" in message.content.lower() and message.attachments:
                await db.increment_proof(message.author.id)
                await message.add_reaction("✅")
                logger.info(f"Proof sumada a: {message.author.display_name}")

        # --- 2. CHAT IA GLOBAL CON GHOST PING Y DIVISIÓN DE EMBEDS ---
        ai_channel_id = db.get_setting("ai_chat_channel")
        if ai_channel_id and message.channel.id == ai_channel_id:
            # Ignoramos mensajes que empiezan con prefijos de comandos
            if not message.content.startswith(("/", "!", "$")):
                
                # Ghost Ping silencioso
                ghost = await message.channel.send(message.author.mention)
                await ghost.delete()

                # Limpieza de tags e inicio de carga
                clean_text = ai.replace_mentions(message)
                gif = db.get_setting("ai_loading_gif")
                status_msg = await message.channel.send(embed=EmbedFactory.ai_loading(message.author, clean_text, gif))

                try:
                    respuesta = await ai.generate_response(f"{message.author.display_name} dice: {clean_text}")
                    # Magia: Pasamos la lista de Embeds (soporta respuestas kilométricas)
                    await status_msg.edit(embed=None, embeds=EmbedFactory.ai_response(message.author, respuesta))
                except Exception as e:
                    await status_msg.edit(embed=EmbedFactory.error("Fallo Neuronal 🧠", f"Hubo un cortocircuito en la IA.\n**Detalle técnico:** `{str(e)[:150]}`"))
                    logger.error(f"Error de Groq: {e}")

        # Procesar comandos normales después de los eventos
        await self.process_commands(message)

bot = SuperBot()

# ==============================================================================
# 🪄 COMANDOS SLASH (CONFIGURACIÓN PARA ADMINS)
# ==============================================================================
@bot.tree.command(name="registrer-chat", description="Fija este canal como el cerebro interactivo de la IA 🧠")
@app_commands.default_permissions(administrator=True)
async def register_chat(interaction: discord.Interaction):
    db.set_setting("ai_chat_channel", interaction.channel_id)
    await interaction.response.send_message(embed=EmbedFactory.success(
        "Núcleo IA Vinculado", 
        "¡Configuración exitosa! La IA ahora leerá y responderá a todo en este canal sin necesidad de comandos. ✨"
    ))

@bot.tree.command(name="carga-animacion", description="Añade un GIF espectacular para cuando la IA está pensando ⏳")
@app_commands.describe(url="Enlace directo a una imagen (terminada en .gif, .png, etc)")
@app_commands.default_permissions(administrator=True)
async def carga_animacion(interaction: discord.Interaction, url: str):
    if not url.startswith("http"):
        return await interaction.response.send_message("❌ La URL es inválida. Asegúrate de que empiece con http:// o https://", ephemeral=True)
    db.set_setting("ai_loading_gif", url)
    embed = EmbedFactory.success("Animación de Carga Lista", "¡La interfaz lucirá mucho más dinámica a partir de ahora! 🚀")
    embed.set_thumbnail(url=url)
    await interaction.response.send_message(embed=embed)

# ==============================================================================
# 🛠️ COMANDOS CLÁSICOS (RANKING CON PAGINACIÓN Y COOLDOWN)
# ==============================================================================
@bot.command(name='rank-mm')
@commands.cooldown(1, 5, commands.BucketType.user) # Anti-Spam: 1 uso cada 5 segundos por usuario
async def rank_mm(ctx):
    ranking = await db.get_ranking()
    if not ranking:
        return await ctx.send(embed=EmbedFactory.error("Ranking Vacío", "No hay registros de proofs en la base de datos central."))
    
    # Diseño estético del Top 20
    texto = ""
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 17
    
    for idx, (uid, count) in enumerate(ranking[:20]):
        medal = medals[idx] if idx < len(medals) else "🔹"
        texto += f"{medal} `#{idx+1:02d}` <@{uid}> • **{count}** Proofs ✅\n"
        
    embed = discord.Embed(title="🏆 RANKING OFICIAL DE PROOFS", description=texto, color=Colors.RANK)
    embed.set_footer(text=f"Total de miembros rankeados: {len(ranking)} ✨")
    await ctx.send(embed=embed)

# ==============================================================================
# 🚀 INICIADOR DEL SISTEMA
# ==============================================================================
if __name__ == "__main__":
    keep_alive()
    if not Config.TOKEN:
        logger.critical("❌ FATAL: No se encontró el DISCORD_TOKEN en el archivo .env")
    else:
        bot.run(Config.TOKEN)
