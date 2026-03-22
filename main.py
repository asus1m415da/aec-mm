"""
╔═══════════════════════════════════════════════════════════════╗
║   🚀 A.E.C. NEXUS v10.1 — FALLBACK CASCADE + UI PREMIUM     ║
║   5 Motores IA · Moderación · Confesiones · Proofs           ║
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
    uptime = datetime.now() - startTime
    return (
        f"🚀 A.E.C. Nexus v10.1 Activo | Uptime: {uptime} | "
        f"5 Motores IA en Cascada operando al 100%"
    )

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger("AEC.Nexus")

class Config:
    TOKEN     = os.getenv("DISCORD_TOKEN")
    GROQ_KEY  = os.getenv("GROQ_API_KEY")
    MONGO_URI = os.getenv("MONGO_URI")

    # ──────────────────────────────────────────────────────────────
    # TU ID EXCLUSIVO — USADO PARA DELETE-DB Y REPORTE DE ERRORES
    # ──────────────────────────────────────────────────────────────
    OWNER_ID = 1413305033222524998

    try:
        GUILD_ID          = int(os.getenv("GUILD_ID", 0))
        CONFESSION_CH_ID  = int(os.getenv("CONFESSION_CHANNEL_ID", 0))
        LOG_CH_ID         = int(os.getenv("LOG_CHANNEL_ID", 0))
        MM_ROLE_ID        = int(os.getenv("MM_ROLE_ID", 0))
        MOD_ROLE_ID       = int(os.getenv("MODERATOR_ROLE_ID", 0))
        ADMIN_ID          = int(os.getenv("ADMIN_ID", 0))
        PROOF_CH_ID       = int(os.getenv("PROOF_CHANNEL_ID", 0))
    except (ValueError, TypeError):
        logger.critical("❌ ERROR CRÍTICO: Los IDs en el archivo .env deben ser números.")
        exit(1)

class Colors:
    GALAXY   = 0x8B5CF6   # Morado Premium
    SUCCESS  = 0x10B981   # Verde Esmeralda
    ERROR    = 0xEF4444   # Rojo Peligro
    WARNING  = 0xF59E0B   # Naranja Alerta
    DARK     = 0x1E293B   # Azul Noche
    BAN      = 0x0F172A   # Negro Mate
    MM       = 0x3B82F6   # Azul Discord
    AI       = 0x06B6D4   # Cyan Tecnológico
    CRITICAL = 0xFF0000   # Rojo Crítico Puro

# ==============================================================================
# 🚨 EXCEPCIÓN CRÍTICA DE IA
# ==============================================================================
class CriticalAIFailure(Exception):
    """Se lanza cuando los 5 modelos de fallback han fallado."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Todos los motores de IA fallaron ({len(errors)} errores)")

# ==============================================================================
# 🧠 CASCADA DE MODELOS — ORDEN ESTRICTO
# ==============================================================================
#   Agrega aquí un "display" name para mostrarlo en el footer del embed de respuesta.
#   Los parámetros extra (top_p, reasoning_effort) solo se pasan al modelo que los soporta.
AI_MODELS: List[Dict] = [
    {
        "model":                "groq/compound",
        "display":              "Compound (Principal)",
        "temperature":          0.8,
        "max_completion_tokens": 2400,
    },
    {
        "model":                "openai/gpt-oss-120b",
        "display":              "GPT-OSS 120B (FB-1)",
        "temperature":          0.86,
        "max_completion_tokens": 4000,
        "top_p":                1,
        "reasoning_effort":     "medium",
    },
    {
        "model":                "qwen/qwen3-32b",
        "display":              "Qwen3-32B (FB-2)",
        "temperature":          0.8,
        "max_completion_tokens": 2400,
    },
    {
        "model":                "meta-llama/llama-4-scout-17b-16e-instruct",
        "display":              "Llama 4 Scout (FB-3)",
        "temperature":          0.8,
        "max_completion_tokens": 2400,
    },
    {
        "model":                "moonshotai/kimi-k2-instruct-0905",
        "display":              "Kimi K2 (FB-4 · Último Recurso)",
        "temperature":          0.8,
        "max_completion_tokens": 2400,
    },
]

# ==============================================================================
# 💾 GESTOR DE DATOS MONGODB ATLAS
# ==============================================================================
class DataManager:
    def __init__(self):
        try:
            self.client = MongoClient(
                Config.MONGO_URI,
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=5000
            )
            self.client.admin.command('ping')
            self.db = self.client["AEC_Database"]

            self.col_ranking     = self.db["ranking"]
            self.col_confessions = self.db["confessions"]
            self.col_settings    = self.db["settings"]
            self.col_memory      = self.db["ai_memory"]

            if not self.col_confessions.find_one({"_id": "metadata"}):
                self.col_confessions.insert_one({"_id": "metadata", "count": 1, "banned_users": []})
            logger.info("✅ Base de Datos MongoDB Atlas conectada.")
        except Exception as e:
            logger.critical(f"❌ Error DB: {e}")
            exit(1)

    # ── Destrucción de DB ──────────────────────────────────────────
    async def drop_all_databases(self):
        def fetch():
            self.col_ranking.drop()
            self.col_confessions.drop()
            self.col_settings.drop()
            self.col_memory.drop()
            self.col_confessions.insert_one({"_id": "metadata", "count": 1, "banned_users": []})
        await asyncio.to_thread(fetch)

    # ── Ranking ───────────────────────────────────────────────────
    async def increment_proof(self, user_id: int):
        await asyncio.to_thread(
            self.col_ranking.update_one,
            {"_id": str(user_id)}, {"$inc": {"count": 1}}, upsert=True
        )

    async def remove_user(self, user_id: int) -> bool:
        res = await asyncio.to_thread(self.col_ranking.delete_one, {"_id": str(user_id)})
        return res.deleted_count > 0

    async def get_ranking(self) -> list:
        def fetch():
            return [
                (int(doc["_id"]), doc["count"])
                for doc in self.col_ranking.find().sort("count", pymongo.DESCENDING)
            ]
        return await asyncio.to_thread(fetch)

    async def export_ranking(self) -> str:
        data = await self.get_ranking()
        return json.dumps({str(uid): count for uid, count in data}, indent=2, ensure_ascii=False)

    async def import_ranking(self, json_str: str) -> Tuple[bool, str]:
        try:
            new_data = json.loads(json_str)
            for uid, count in new_data.items():
                if int(count) >= 0:
                    self.col_ranking.update_one(
                        {"_id": str(uid)}, {"$set": {"count": int(count)}}, upsert=True
                    )
            return True, "✅ Datos importados correctamente a MongoDB."
        except Exception as e:
            return False, f"❌ Error importando: {e}"

    # ── Confesiones ───────────────────────────────────────────────
    async def get_next_confession_id(self):
        def fetch():
            res = self.col_confessions.find_one_and_update(
                {"_id": "metadata"},
                {"$inc": {"count": 1}},
                return_document=pymongo.ReturnDocument.AFTER
            )
            return res["count"] - 1
        return await asyncio.to_thread(fetch)

    def is_banned(self, user_id: int) -> bool:
        doc = self.col_confessions.find_one({"_id": "metadata"})
        return user_id in doc.get("banned_users", [])

    async def ban_user(self, user_id: int):
        await asyncio.to_thread(
            self.col_confessions.update_one,
            {"_id": "metadata"}, {"$addToSet": {"banned_users": user_id}}
        )

    # ── Configuración y Memoria ───────────────────────────────────
    def set_setting(self, key: str, value):
        self.col_settings.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)

    def get_setting(self, key: str, default=None):
        doc = self.col_settings.find_one({"_id": key})
        return doc["value"] if doc else default

    def add_ai_message(self, role: str, content: str):
        self.col_memory.insert_one({"role": role, "content": content, "timestamp": datetime.now()})

    def get_ai_history(self, limit=20) -> list:
        return list(reversed(
            list(self.col_memory.find().sort("timestamp", pymongo.DESCENDING).limit(limit))
        ))

data_manager = DataManager()

# ==============================================================================
# 🗣️ SYSTEM PROMPT
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

# ==============================================================================
# 🤖 IA HANDLER CON CASCADA DE FALLBACKS
# ==============================================================================
class AIHandler:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_KEY)

    async def get_ai_joke(self) -> str:
        def fetch():
            comp = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": "Di una frase corta, ingeniosa y graciosa en español."}],
                temperature=1.2,
                max_tokens=60
            )
            return comp.choices[0].message.content.strip()
        try:
            return await asyncio.to_thread(fetch)
        except Exception:
            return "🤖 Listos para el intercambio seguro."

    def replace_mentions(self, message: discord.Message) -> str:
        content = message.content
        for mention in message.mentions:
            content = content.replace(f'<@{mention.id}>', f"@{mention.display_name}")
        return content

    async def generate_chat_response(self, user_content: str) -> Tuple[str, str]:
        """
        Intenta obtener respuesta iterando los modelos en cascada.
        Devuelve (texto_respuesta, nombre_display_del_modelo).
        Lanza CriticalAIFailure si todos los modelos fallan.
        """
        # Construir historial de mensajes una sola vez
        history  = data_manager.get_ai_history(limit=20)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_content})

        errors: List[str] = []

        for idx, model_cfg in enumerate(AI_MODELS, start=1):
            model_name   = model_cfg["model"]
            model_display = model_cfg.get("display", model_name)
            # Filtrar solo los parámetros de la API (excluir claves internas)
            api_params   = {k: v for k, v in model_cfg.items() if k not in ("model", "display")}

            try:
                logger.info(f"🧠 [{idx}/{len(AI_MODELS)}] Intentando: {model_name}")

                # Closure con argumentos por defecto para evitar captura tardía de variables
                def make_request(m=model_name, p=api_params, msgs=messages):
                    return self.client.chat.completions.create(
                        model=m,
                        messages=msgs,
                        **p
                    ).choices[0].message.content

                response_text = await asyncio.to_thread(make_request)

                # Guardar en memoria solo si obtuvimos respuesta exitosa
                data_manager.add_ai_message("user", user_content)
                data_manager.add_ai_message("assistant", response_text)

                logger.info(f"✅ Respuesta obtenida de: {model_name}")
                return response_text, model_display

            except Exception as e:
                error_entry = f"[Motor {idx}] **{model_display}**: `{str(e)[:250]}`"
                errors.append(error_entry)
                logger.warning(f"⚠️ Falló {model_name} → {str(e)[:120]}")

        # Si llegamos aquí: todos fallaron
        raise CriticalAIFailure(errors)

ai = AIHandler()

# ==============================================================================
# 🔍 DETECTOR DE PROOFS
# ==============================================================================
class UltraProofDetector:
    @staticmethod
    def contains_proof_variant(text: str) -> bool:
        if not text:
            return False
        normalized = text.lower().strip()
        patterns = [
            r'pr[o0]f+', r'proof', r'proff',
            r'pr\s*[o0]\s*f+', r'p\s*r\s*[o0]\s*f+',
            r'#\d+', r'p[r0][o0]f{1,2}'
        ]
        return (
            any(re.search(p, normalized, re.IGNORECASE) for p in patterns)
            or "proof" in normalized
            or "proff" in normalized
        )

    @staticmethod
    def has_attachments_or_embeds(message: discord.Message) -> bool:
        return len(message.attachments) > 0 or len(message.embeds) > 0

# ==============================================================================
# 🧩 VISTAS Y BOTONES (UI PREMIUM)
# ==============================================================================

class DeleteDBConfirm(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ Solo el Creador puede usar estos botones.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Sí, Borrar Todo", style=discord.ButtonStyle.danger, emoji="💥")
    async def btn_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await data_manager.drop_all_databases()
        embed = discord.Embed(
            title="💥 Base de Datos Aniquilada",
            description=(
                "Todas las colecciones de MongoDB han sido eliminadas.\n"
                "El sistema ha renacido desde cero. ✨"
            ),
            color=Colors.ERROR,
            timestamp=datetime.now()
        )
        embed.set_footer(
            text="A.E.C. System Reset",
            icon_url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png"
        )
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="No, Cancelar", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def btn_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛡️ Operación Abortada",
            description="La base de datos está a salvo. No se borró nada.",
            color=Colors.SUCCESS,
            timestamp=datetime.now()
        )
        embed.set_footer(text="A.E.C. Nexus — Sistema de Seguridad")
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


# ==============================================================================
# 🏗️ EMBED BUILDER (UI PREMIUM)
# ==============================================================================
class EmbedBuilder:

    # ── Ranking ───────────────────────────────────────────────────
    @staticmethod
    def ranking_pages(ranking_data: list) -> List[discord.Embed]:
        if not ranking_data:
            embed = discord.Embed(
                title="🏆 Salón de la Fama: Proofs",
                description="Aún no hay proofs registradas.\n¡Sé el primero en aparecer aquí! 🚀",
                color=Colors.WARNING,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3176/3176294.png")
            embed.set_footer(text="A.E.C. Ranking System • ¡Compite por el #1!")
            return [embed]

        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 997
        pages, current_text, page_num, users_per_page = [], "", 1, 0

        for idx, (uid, count) in enumerate(ranking_data, 1):
            medal = medals[idx - 1] if idx <= 3 else "🔸"
            suffix = "s" if count != 1 else ""
            line = f"{medal} **#{idx:02d}** <@{uid}> ━ **{count}** Proof{suffix} ✅\n"

            if len(current_text) + len(line) > 3800 or users_per_page >= 50:
                embed = discord.Embed(
                    title=f"🏆 Salón de la Fama: Proofs — Página {page_num}",
                    description=current_text,
                    color=Colors.GALAXY,
                    timestamp=datetime.now()
                )
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3176/3176294.png")
                embed.set_footer(
                    text=f"A.E.C. Ranking System • Pág {page_num} | {len(ranking_data)} usuarios"
                )
                pages.append(embed)
                current_text, page_num, users_per_page = line, page_num + 1, 1
            else:
                current_text += line
                users_per_page += 1

        if current_text:
            embed = discord.Embed(
                title=f"🏆 Salón de la Fama: Proofs — Página {page_num}",
                description=current_text,
                color=Colors.GALAXY,
                timestamp=datetime.now()
            )
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3176/3176294.png")
            embed.set_footer(
                text=f"A.E.C. Ranking System • Pág {page_num}/{page_num} | {len(ranking_data)} usuarios"
            )
            pages.append(embed)

        return pages

    # ── Respuesta IA ──────────────────────────────────────────────
    @staticmethod
    def ai_response(
        user: discord.Member,
        response: str,
        model_display: str = "Desconocido"
    ) -> List[discord.Embed]:
        chunks, max_chars, text = [], 3900, response
        while len(text) > max_chars:
            split_idx = text.rfind('\n', 0, max_chars)
            if split_idx == -1:
                split_idx = text.rfind(' ', 0, max_chars)
            if split_idx == -1:
                split_idx = max_chars
            chunks.append(text[:split_idx].strip())
            text = text[split_idx:].strip()
        if text:
            chunks.append(text)

        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(description=chunk, color=Colors.AI, timestamp=datetime.now())
            if i == 0:
                embed.set_author(
                    name="🧠 A.E.C. Nexus",
                    icon_url="https://cdn-icons-png.flaticon.com/512/1693/1693746.png"
                )
            footer = f"⚡ Motor: {model_display} • @{user.display_name}"
            if len(chunks) > 1:
                footer += f" • Parte {i + 1}/{len(chunks)}"
            embed.set_footer(text=footer, icon_url=user.display_avatar.url)
            embeds.append(embed)
        return embeds

    # ── Error Crítico Público ─────────────────────────────────────
    @staticmethod
    def critical_error_public() -> discord.Embed:
        embed = discord.Embed(
            title="⚠️ Caída Global de Motores IA",
            description=(
                "**Todos los núcleos de procesamiento se han sobrecargado.** 🔴\n\n"
                "Se ha enviado un reporte automático a los creadores.\n"
                "Por favor, intenta de nuevo en unos minutos. 🔄"
            ),
            color=Colors.CRITICAL,
            timestamp=datetime.now()
        )
        embed.set_footer(
            text="A.E.C. Nexus v10.1 — Sistema de Alertas Automáticas",
            icon_url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png"
        )
        return embed

    # ── Reporte DM al Owner ───────────────────────────────────────
    @staticmethod
    def critical_error_dm(
        user: discord.Member,
        question: str,
        errors: List[str]
    ) -> discord.Embed:
        embed = discord.Embed(
            title="🚨 REPORTE CRÍTICO — Caída Total de IA",
            description=(
                f"**{len(errors)}/{len(AI_MODELS)} motores fallaron en cascada.**\n"
                "Revisa las API keys, límites de tasa y estado de los servicios."
            ),
            color=Colors.CRITICAL,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="👤 Usuario Afectado",
            value=f"{user.mention}\n`{user.display_name}` • ID: `{user.id}`",
            inline=True
        )
        embed.add_field(
            name="🏠 Servidor",
            value=f"`{user.guild.name if hasattr(user, 'guild') else 'N/A'}`",
            inline=True
        )
        embed.add_field(
            name="💬 Pregunta del Usuario",
            value=f"```\n{question[:450]}\n```",
            inline=False
        )
        errors_text = "\n".join(errors)
        embed.add_field(
            name=f"🔴 Log de Errores ({len(errors)} motores)",
            value=f"```\n{errors_text[:900]}\n```",
            inline=False
        )
        embed.set_footer(
            text="A.E.C. Nexus v10.1 — Monitor de Sistemas",
            icon_url="https://cdn-icons-png.flaticon.com/512/1008/1008928.png"
        )
        return embed


# ==============================================================================
# 🔘 VISTAS DE PAGINACIÓN Y CONFESIONES
# ==============================================================================
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
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Enviar Secreto Anónimo",
        style=discord.ButtonStyle.primary,
        emoji="🤫",
        custom_id="persistent_confess_btn"
    )
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if data_manager.is_banned(interaction.user.id):
            embed = discord.Embed(
                title="⛔ Acceso Denegado",
                description=(
                    "Has sido bloqueado del sistema de confesiones.\n"
                    "Contacta al Staff si crees que es un error."
                ),
                color=Colors.BAN
            )
            embed.set_footer(text="A.E.C. Sistema de Confesiones")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.send_modal(ConfessionModal())


class ConfessionModal(discord.ui.Modal, title="🤫 Tu Secreto Seguro"):
    text_input = discord.ui.TextInput(
        label="Escribe tu confesión aquí",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=3500,
        placeholder="Nadie sabrá que fuiste tú... 🔒"
    )
    img_input = discord.ui.TextInput(
        label="URL de Imagen (Opcional)",
        style=discord.TextStyle.short,
        required=False,
        placeholder="https://i.imgur.com/ejemplo.png"
    )

    async def on_submit(self, interaction: discord.Interaction):
        conf_id     = await data_manager.get_next_confession_id()
        log_channel = interaction.guild.get_channel(Config.LOG_CH_ID)

        embed = discord.Embed(
            title="📥 Nueva Confesión Pendiente",
            description=f"**Contenido:**\n```\n{self.text_input.value}\n```",
            color=Colors.WARNING,
            timestamp=datetime.now()
        )
        embed.set_author(
            name=f"Expediente #{conf_id} — Solo Staff",
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(
            name="👤 Autor (Solo Staff)",
            value=f"{interaction.user.mention}\nID: `{interaction.user.id}`",
            inline=True
        )
        embed.add_field(
            name="📊 Estado",
            value="⏳ Pendiente de revisión",
            inline=True
        )
        embed.set_footer(text=f"A.E.C. Confesiones • Expediente #{conf_id}")
        if self.img_input.value:
            embed.set_image(url=self.img_input.value)

        view = AdminControlPanel(
            self.text_input.value, self.img_input.value,
            interaction.user, conf_id
        )
        await log_channel.send(embed=embed, view=view)

        confirm = discord.Embed(
            title="✅ ¡Enviado con Éxito!",
            description=(
                f"Tu confesión **#{conf_id}** fue enviada al staff. 🔒\n"
                "Tu identidad permanece completamente anónima."
            ),
            color=Colors.SUCCESS,
            timestamp=datetime.now()
        )
        confirm.set_footer(text="A.E.C. Confesiones • Anonimato garantizado")
        await interaction.response.send_message(embed=confirm, ephemeral=True)


class AdminControlPanel(discord.ui.View):
    def __init__(self, content: str, image: str, author: discord.Member, conf_id: int):
        super().__init__(timeout=None)
        self.content  = content
        self.image    = image
        self.author   = author
        self.conf_id  = conf_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.get_role(Config.MOD_ROLE_ID):
            await interaction.response.send_message(
                "🔒 Solo moderadores pueden usar este panel.", ephemeral=True
            )
            return False
        return True

    def _disable_all(self):
        for child in self.children:
            child.disabled = True

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.success, custom_id="adm_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        pub_channel = interaction.guild.get_channel(Config.CONFESSION_CH_ID)

        embed_pub = discord.Embed(
            description=f"*{self.content}*",
            color=Colors.DARK,
            timestamp=datetime.now()
        )
        embed_pub.set_author(
            name=f"🤫 Confesión Anónima #{self.conf_id}",
            icon_url="https://cdn-icons-png.flaticon.com/512/4645/4645949.png"
        )
        embed_pub.set_footer(
            text="A.E.C. Secrets • Identidad protegida 🔒",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        if self.image:
            embed_pub.set_image(url=self.image)

        await pub_channel.send(embed=embed_pub, view=PersistentConfessionButton())

        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.SUCCESS
        embed_log.set_field_at(
            1,
            name="📊 Estado Final",
            value=f"🟢 **APROBADO Y PUBLICADO**\n👮 Por: {interaction.user.mention}",
            inline=True
        )
        self._disable_all()
        await interaction.message.edit(embed=embed_log, view=self)
        await interaction.response.send_message("✅ Confesión publicada exitosamente.", ephemeral=True)

    @discord.ui.button(label="🗑️ Rechazar", style=discord.ButtonStyle.secondary, custom_id="adm_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.WARNING
        embed_log.set_field_at(
            1,
            name="📊 Estado Final",
            value=f"🟡 **RECHAZADO SIN PUBLICAR**\n👮 Por: {interaction.user.mention}",
            inline=True
        )
        self._disable_all()
        await interaction.message.edit(embed=embed_log, view=self)
        await interaction.response.send_message("🗑️ Confesión rechazada.", ephemeral=True)

    @discord.ui.button(label="🔨 Banear", style=discord.ButtonStyle.danger, custom_id="adm_ban")
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await data_manager.ban_user(self.author.id)

        embed_log = interaction.message.embeds[0]
        embed_log.color = Colors.BAN
        embed_log.set_field_at(
            1,
            name="📊 Estado Final",
            value=f"⚫ **USUARIO BANEADO**\n👤 Infractor: {self.author.mention}",
            inline=True
        )
        self._disable_all()
        await interaction.message.edit(embed=embed_log, view=self)
        await interaction.response.send_message(
            "⛔ Usuario bloqueado permanentemente de confesiones.", ephemeral=True
        )

# ==============================================================================
# 🤖 BOT PRINCIPAL
# ==============================================================================
class SuperBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members          = True
        intents.guilds           = True
        super().__init__(command_prefix=["$", "!"], help_command=None, intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentConfessionButton())
        await self.tree.sync()
        logger.info("✅ Hooks, Vistas Persistentes y Slash Commands sincronizados.")

    async def on_ready(self):
        logger.info("=" * 60)
        logger.info(f"🚀 A.E.C. Nexus v10.1 Online | {self.user}")
        logger.info(f"   IA: {len(AI_MODELS)} motores en cascada de fallbacks")
        logger.info("=" * 60)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"A.E.C. • {len(AI_MODELS)} Motores IA 🧠"
            )
        )

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return await self.process_commands(message)

        # ── Sistema de Proofs ──────────────────────────────────────
        if message.channel.id == Config.PROOF_CH_ID:
            if (UltraProofDetector.contains_proof_variant(message.content)
                    and UltraProofDetector.has_attachments_or_embeds(message)):
                await data_manager.increment_proof(message.author.id)
                await message.add_reaction("✅")

        # ── IA Global Chat con Cascada de Fallbacks ────────────────
        ai_channel = data_manager.get_setting("ai_chat_channel")
        if (ai_channel == message.channel.id
                and not message.content.startswith(("/", "!", "$"))):

            clean        = ai.replace_mentions(message)
            user_content = f"{message.author.display_name}: {clean}"

            # Embed de carga animado
            embed_load = discord.Embed(
                description=(
                    f"⏳ **Procesando consulta...**\n"
                    f"`{clean[:75]}{'...' if len(clean) > 75 else ''}`"
                ),
                color=Colors.AI
            )
            embed_load.set_author(
                name="🧠 A.E.C. Nexus — Iniciando motores",
                icon_url="https://cdn-icons-png.flaticon.com/512/1693/1693746.png"
            )
            embed_load.set_footer(
                text=f"Motor 1/{len(AI_MODELS)}: Compound (Principal) • Verificando..."
            )
            gif = data_manager.get_setting("ai_loading_gif")
            if gif:
                embed_load.set_thumbnail(url=gif)

            msg_ui = await message.channel.send(embed=embed_load)

            try:
                # ✅ Respuesta exitosa desde algún motor de la cascada
                resp_text, model_display = await ai.generate_chat_response(user_content)
                await msg_ui.edit(
                    embeds=EmbedBuilder.ai_response(message.author, resp_text, model_display)
                )

            except CriticalAIFailure as critical:
                # ────────────────────────────────────────────────────
                # 🔴 FALLO CRÍTICO: todos los motores fallaron
                # ────────────────────────────────────────────────────
                logger.error(f"🔴 FALLO CRÍTICO DE IA — {len(critical.errors)} errores acumulados.")

                # 1️⃣ Mensaje público en el canal
                await msg_ui.edit(embed=EmbedBuilder.critical_error_public())

                # 2️⃣ DM privado al owner con el reporte completo
                try:
                    owner     = await self.fetch_user(Config.OWNER_ID)
                    dm_embed  = EmbedBuilder.critical_error_dm(
                        user=message.author,
                        question=clean,
                        errors=critical.errors
                    )
                    await owner.send(embed=dm_embed)
                    logger.info("📨 Reporte de fallo crítico enviado al owner por DM.")
                except discord.Forbidden:
                    logger.error("❌ DM bloqueado: el owner tiene los DMs desactivados.")
                except Exception as dm_err:
                    logger.error(f"❌ No se pudo enviar DM al owner: {dm_err}")

            except Exception as unexpected:
                logger.error(f"❌ Error inesperado en IA: {unexpected}")
                await msg_ui.edit(
                    embed=discord.Embed(
                        title="❌ Error Inesperado",
                        description=f"Ocurrió un error interno.\n`{str(unexpected)[:150]}`",
                        color=Colors.ERROR,
                        timestamp=datetime.now()
                    ).set_footer(text="A.E.C. Nexus — Contacta al Staff")
                )

        await self.process_commands(message)

bot = SuperBot()

# ==============================================================================
# 🪄 COMANDOS SLASH Y ADMIN
# ==============================================================================

@bot.command(name='delete-database')
async def delete_database(ctx: commands.Context):
    """Comando Ultra Secreto — Solo el Creador (OWNER_ID)."""
    if ctx.author.id != Config.OWNER_ID:
        return await ctx.send(
            embed=discord.Embed(
                description="⛔ **ACCESO DENEGADO:** Comando restringido al nivel Dios.",
                color=Colors.ERROR,
                timestamp=datetime.now()
            ).set_footer(text="A.E.C. Nexus — Seguridad Máxima")
        )

    embed = discord.Embed(
        title="⚠️ ADVERTENCIA CRÍTICA: BORRADO GLOBAL",
        description=(
            "Estás a punto de **ELIMINAR TODA LA BASE DE DATOS** de forma permanente.\n\n"
            "**Esto incluye:**\n"
            "• 🏆 Ranking completo de Proofs\n"
            "• 🤫 Historial de Confesiones\n"
            "• 🧠 Memoria Global de la IA\n"
            "• ⚙️ Todas las Configuraciones\n\n"
            "**⛔ Esta acción NO se puede deshacer.**"
        ),
        color=Colors.ERROR,
        timestamp=datetime.now()
    )
    embed.set_footer(text="A.E.C. Nexus — Sistema de Seguridad de Nivel Dios")
    await ctx.send(embed=embed, view=DeleteDBConfirm(ctx.author.id))


@bot.tree.command(name="registrer-chat", description="Fija este canal como la sala de IA global.")
@app_commands.default_permissions(administrator=True)
async def register_chat(interaction: discord.Interaction):
    data_manager.set_setting("ai_chat_channel", interaction.channel_id)
    embed = discord.Embed(
        title="🌐 Canal de IA Registrado",
        description=(
            f"A.E.C. Nexus operará en {interaction.channel.mention}.\n"
            f"Mensajes procesados por **{len(AI_MODELS)} motores en cascada**."
        ),
        color=Colors.AI,
        timestamp=datetime.now()
    )
    embed.set_footer(text="A.E.C. Nexus — Administración")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="carga-animacion", description="Configura un GIF animado de carga para la IA.")
@app_commands.default_permissions(administrator=True)
async def carga_animacion(interaction: discord.Interaction, url: str):
    data_manager.set_setting("ai_loading_gif", url)
    embed = discord.Embed(
        description="✅ GIF de procesamiento actualizado correctamente.",
        color=Colors.SUCCESS,
        timestamp=datetime.now()
    ).set_footer(text="A.E.C. Nexus — Configuración")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==============================================================================
# 🛠️ COMANDOS CLÁSICOS (Prefijo $ o !)
# ==============================================================================

@bot.command()
async def add(ctx: commands.Context, *, arg=None):
    if not ctx.author.get_role(Config.MM_ROLE_ID):
        return await ctx.send(
            embed=discord.Embed(
                description="🔒 Solo Middlemans pueden agregar usuarios al ticket.",
                color=Colors.ERROR
            ).set_footer(text="A.E.C. MM System")
        )
    if not arg:
        return await ctx.send(
            embed=discord.Embed(
                description="⚠️ **Uso correcto:** `!add @usuario` o `!add ID`",
                color=Colors.WARNING
            )
        )

    user = (
        ctx.message.mentions[0] if ctx.message.mentions
        else ctx.guild.get_member(int(arg)) if arg.isdigit()
        else None
    )
    if not user:
        return await ctx.send(
            embed=discord.Embed(
                description="❌ Usuario no encontrado en el servidor.",
                color=Colors.ERROR
            )
        )

    try:
        await ctx.channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )
        await ctx.send(
            embed=discord.Embed(
                description=f"🤝 **{user.mention}** ha sido añadido al intercambio seguro.",
                color=Colors.MM,
                timestamp=datetime.now()
            ).set_footer(text="A.E.C. Middleman System")
        )
        joke = await ai.get_ai_joke()
        await ctx.send(
            embed=discord.Embed(
                description=f"🤖 **A.E.C. Nexus dice:** {joke}",
                color=Colors.AI
            ).set_footer(text="A.E.C. Nexus — Bienvenida automática")
        )
    except Exception as e:
        await ctx.send(
            embed=discord.Embed(
                description=f"❌ Error de permisos: `{e}`",
                color=Colors.ERROR
            )
        )


@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx: commands.Context):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🌌 A.E.C. Secreto — Confesiones Anónimas",
        description=(
            "¿Tienes algo que decir pero no quieres que sepan que fuiste tú?\n\n"
            "Haz clic abajo para enviar una **Confesión Totalmente Anónima**. "
            "Solo el Staff verá la fuente en caso de infracciones."
        ),
        color=Colors.GALAXY,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3252/3252934.png")
    embed.set_footer(text="A.E.C. Nexus — Tu identidad está protegida 🔒")
    await ctx.send(embed=embed, view=PersistentConfessionButton())


@bot.command(name='rank-mm')
async def rank_mm(ctx: commands.Context):
    ranking = await data_manager.get_ranking()
    pages   = EmbedBuilder.ranking_pages(ranking)
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
    else:
        view = PaginationView(pages)
        view.message = await ctx.send(embed=pages[0], view=view)


@bot.command(name='borrar-ranking')
async def borrar_ranking(ctx: commands.Context, user: discord.User):
    if ctx.author.id != Config.ADMIN_ID:
        return await ctx.send(
            embed=discord.Embed(description="🔒 Solo el Admin puede borrar registros.", color=Colors.ERROR)
        )
    success = await data_manager.remove_user(user.id)
    color   = Colors.SUCCESS if success else Colors.WARNING
    msg     = (
        f"🧹 La cuenta de {user.mention} fue borrada del Ranking."
        if success else
        f"❌ {user.mention} no tiene registros en el Ranking."
    )
    await ctx.send(
        embed=discord.Embed(description=msg, color=color, timestamp=datetime.now())
        .set_footer(text="A.E.C. Ranking System")
    )


@bot.command(name='exportar-datos')
async def exportar_datos(ctx: commands.Context):
    if ctx.author.id != Config.ADMIN_ID:
        return await ctx.send(
            embed=discord.Embed(description="🔒 Denegado.", color=Colors.ERROR)
        )
    data = await data_manager.export_ranking()
    file = discord.File(
        StringIO(data),
        filename=f"ranking_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    await ctx.send(
        embed=discord.Embed(
            description="📦 **Respaldo generado con éxito.** Archivo adjunto. 📎",
            color=Colors.SUCCESS,
            timestamp=datetime.now()
        ).set_footer(text="A.E.C. Data Manager"),
        file=file
    )


@bot.command(name='importar-datos')
async def importar_datos(ctx: commands.Context):
    if ctx.author.id != Config.ADMIN_ID:
        return await ctx.send(
            embed=discord.Embed(description="🔒 Denegado.", color=Colors.ERROR)
        )
    if not ctx.message.attachments or not ctx.message.attachments[0].filename.endswith('.json'):
        return await ctx.send(
            embed=discord.Embed(
                description="❌ Adjunta un archivo `.json` válido al comando.",
                color=Colors.ERROR
            )
        )
    content       = (await ctx.message.attachments[0].read()).decode('utf-8')
    success, msg  = await data_manager.import_ranking(content)
    await ctx.send(
        embed=discord.Embed(
            description=msg,
            color=Colors.SUCCESS if success else Colors.ERROR,
            timestamp=datetime.now()
        ).set_footer(text="A.E.C. Data Manager")
    )

# ==============================================================================
# 🚀 ARRANQUE
# ==============================================================================
if __name__ == "__main__":
    keep_alive()
    bot.run(Config.TOKEN)
