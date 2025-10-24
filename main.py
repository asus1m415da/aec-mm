import discord
from discord.ext import commands
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import random
import time
import hashlib

# Cargar variables de entorno
load_dotenv()

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Configurar Google AI con Gemma
def setup_gemma():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY no encontrada en las variables de entorno")
    client = genai.Client(api_key=api_key)
    return client

# Inicializar cliente de Gemma
try:
    gemma_client = setup_gemma()
except Exception as e:
    print(f"Error al configurar Gemma: {e}")
    gemma_client = None

# Historial de consejos generados (para evitar repeticiones)
consejos_history = {"trader": [], "middleman": []}

# Función para generar consejos ÚNICOS Y DIFERENTES cada vez
def generate_advice(user_type):
    """Genera consejos ÚNICOS usando Gemma 3 4B con máxima variabilidad"""
    if not gemma_client:
        return "⚠️ El servicio de IA no está disponible en este momento."

    # Crear semilla única usando timestamp + random + hash
    timestamp = int(time.time() * 1000)  # Milisegundos
    random_num = random.randint(10000, 99999)
    unique_seed = hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()[:8]

    # Variaciones de enfoque para MAYOR DIVERSIDAD
    enfoques_trader = [
        "seguridad en la verificación de middlemans",
        "protección contra scams comunes",
        "mejores prácticas de documentación",
        "señales de alerta en trades sospechosos",
        "consejos de comunicación efectiva",
        "protección de información personal",
        "uso correcto de sistemas de escrow",
        "verificación de reputación del intermediario"
    ]

    enfoques_middleman = [
        "construcción de confianza con traders",
        "transparencia en el proceso de intercambio",
        "documentación profesional de trades",
        "comunicación clara con ambas partes",
        "gestión de conflictos entre traders",
        "protección de datos de clientes",
        "mejora continua de reputación",
        "profesionalismo en situaciones difíciles"
    ]

    enfoque = random.choice(enfoques_trader if user_type == "trader" else enfoques_middleman)

    # CONTEXTO MÍNIMO pero efectivo
    contexto = """Middleman: intermediario que evita estafas en trades digitales (Roblox/Discord).
Trader: usuario que intercambia objetos/cuentas digitales."""

    # Variaciones de estilo para cada consejo
    estilos = [
        "directo y profesional",
        "motivador y práctico",
        "preventivo y cauteloso",
        "educativo y claro",
        "basado en experiencia real"
    ]

    estilo = random.choice(estilos)

    prompts = {
        "trader": f"""{contexto}

Genera UN consejo ÚNICO Y ORIGINAL para traders (máximo 2 líneas).
Enfoque específico: {enfoque}
Estilo: {estilo}
IMPORTANTE: NO repitas estos consejos previos: {', '.join(consejos_history['trader'][-3:]) if consejos_history['trader'] else 'ninguno'}

Sé CREATIVO y DIFERENTE. Cada consejo debe ser ÚNICO.
Semilla única: {unique_seed}
Texto simple, sin markdown.""",

        "middleman": f"""{contexto}

Genera UN consejo ÚNICO Y ORIGINAL para middlemans (máximo 2 líneas).
Enfoque específico: {enfoque}
Estilo: {estilo}
IMPORTANTE: NO repitas estos consejos previos: {', '.join(consejos_history['middleman'][-3:]) if consejos_history['middleman'] else 'ninguno'}

Sé CREATIVO y DIFERENTE. Cada consejo debe ser ÚNICO.
Semilla única: {unique_seed}
Texto simple, sin markdown."""
    }

    try:
        # MÁXIMA temperatura para MÁXIMA variabilidad
        response = gemma_client.models.generate_content(
            model='gemma-3-4b-it',
            contents=prompts[user_type],
            config=types.GenerateContentConfig(
                temperature=2.0,  # MÁXIMA creatividad (rango 0-2)
                top_p=0.98,       # Máxima diversidad
                top_k=64,         # Más opciones de tokens
                max_output_tokens=150,
            )
        )

        advice = response.text.strip()

        # Limpiar y validar
        if len(advice) > 800:
            advice = advice[:797] + "..."

        # Agregar al historial (mantener últimos 5)
        consejos_history[user_type].append(advice[:50])  # Solo primeras 50 chars
        if len(consejos_history[user_type]) > 5:
            consejos_history[user_type].pop(0)

        print(f"✅ Consejo generado con enfoque: {enfoque}, estilo: {estilo}")

        return advice

    except Exception as e:
        print(f"⚠️ Error generando consejo con IA: {e}")
        import traceback
        traceback.print_exc()

        # Fallback con 15 consejos DIFERENTES para cada tipo
        consejos_fallback = {
            "trader": [
                "💡 Verifica la reputación del middleman en múltiples servidores antes de confiar.",
                "🔒 Nunca compartas tu .HAR file, incluso si parece legítimo el pedido.",
                "📊 Graba video del proceso completo del trade para tener evidencia.",
                "⚠️ Si el middleman te presiona para actuar rápido, es una red flag.",
                "🎯 Usa middlemen con historial público verificable de +100 trades exitosos.",
                "🛡️ Pregunta por referencias de otros traders antes de iniciar.",
                "⚡ Confirma la identidad del middleman en su servidor oficial.",
                "🔍 Revisa que el middleman tenga roles verificados en servidores grandes.",
                "💬 Mantén todas las conversaciones dentro de Discord para tener registro.",
                "📸 Toma screenshots de cada paso: acuerdo, envío y recepción.",
                "🚫 Evita middlemen que cobran tarifas excesivas (+10% del trade).",
                "✅ Busca middlemen con sistema de tickets organizado.",
                "🔐 Activa autenticación 2FA en todas tus cuentas antes de tradear.",
                "⏰ Los trades legítimos nunca tienen límite de tiempo artificial.",
                "🌟 Confía en tu instinto: si algo se siente mal, cancela el trade."
            ],
            "middleman": [
                "✨ Mantén un registro público de todos tus trades con timestamps y evidencias.",
                "🛡️ Nunca solicites información como contraseñas, solo los ítems del trade.",
                "⚡ Responde en menos de 5 minutos durante un trade activo.",
                "💎 Publica testimonios de traders satisfechos regularmente.",
                "📝 Usa un sistema de tickets para mantener organización profesional.",
                "🎯 Explica cada paso del proceso antes de iniciarlo.",
                "🔒 Guarda evidencia de cada trade por mínimo 30 días.",
                "💬 Mantén comunicación constante con ambas partes durante el proceso.",
                "🌟 Ofrece garantías claras y políticas de disputa escritas.",
                "📊 Actualiza tus estadísticas de trades públicamente cada semana.",
                "⚠️ Rechaza trades que parezcan sospechosos, aunque pierdas comisión.",
                "🤝 Sé imparcial: tu trabajo es facilitar, no tomar lados.",
                "🔍 Verifica la autenticidad de los ítems antes de proceder.",
                "⏱️ Establece tiempos máximos de respuesta y cúmplelos siempre.",
                "💯 La honestidad es tu mejor publicidad: admite errores si ocurren."
            ]
        }

        # Evitar repetir fallback recientes
        disponibles = [c for c in consejos_fallback[user_type] 
                      if not any(c[:50] == h for h in consejos_history[user_type][-3:])]

        if not disponibles:
            disponibles = consejos_fallback[user_type]

        consejo = random.choice(disponibles)

        # Agregar al historial
        consejos_history[user_type].append(consejo[:50])
        if len(consejos_history[user_type]) > 5:
            consejos_history[user_type].pop(0)

        return consejo

# Función para crear embeds bonitos
def create_welcome_embed(member, advice_trader, advice_middleman):
    """Crea un embed profesional y atractivo"""
    colors = [0x00FF00, 0x00FFFF, 0xFF00FF, 0xFFD700, 0xFF6347, 0x9B59B6, 0xE74C3C, 0x3498DB, 0x1ABC9C, 0xF39C12]

    embed = discord.Embed(
        title="✨ ¡Bienvenido al Canal! ✨",
        description=f"**{member.mention}** ha sido añadido al canal",
        color=random.choice(colors),
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    # Consejos ÚNICOS con IA
    embed.add_field(
        name="📊 Consejo para Traders",
        value=f"> {advice_trader}",
        inline=False
    )

    embed.add_field(
        name="🤝 Consejo para Middlemans (𝙈𝙄𝘿𝘿𝙇𝙀𝙈𝘼𝙉𝙎)",
        value=f"> {advice_middleman}",
        inline=False
    )

    embed.add_field(
        name="💎 Recordatorio",
        value="Middlemans evitan estafas en trades de alto valor. Verifica reputación y documenta todo.",
        inline=False
    )

    embed.set_footer(
        text="Bot de Gestión de Canales | Powered by Gemma AI",
        icon_url=bot.user.display_avatar.url if bot.user else None
    )

    return embed

def create_removed_embed(member):
    """Crea embed para cuando se remueve un usuario"""
    embed = discord.Embed(
        title="👋 Usuario Removido",
        description=f"**{member.mention}** ha sido removido del canal",
        color=0xFF4444,
        timestamp=discord.utils.utcnow()
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Bot de Gestión de Canales")

    return embed

@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print(f'ID: {bot.user.id}')
    print('------')
    if gemma_client:
        print('🤖 IA Gemma 3 4B activada con MÁXIMA variabilidad')
        print('🎲 Sistema anti-repetición activado')
    else:
        print('⚠️ IA no disponible')

@bot.command(name='add')
async def add_user(ctx, member: discord.Member = None, user_id: str = None):
    """
    Añade un usuario al canal con permisos de lectura y escritura
    Uso: !add @usuario o !add ID_USUARIO
    """
    # Obtener el miembro
    if member is None and user_id:
        try:
            member = await ctx.guild.fetch_member(int(user_id))
        except:
            await ctx.send("❌ No se pudo encontrar el usuario con ese ID")
            return

    if member is None:
        await ctx.send("❌ Por favor menciona un usuario o proporciona su ID\nUso: `!add @usuario` o `!add ID_USUARIO`")
        return

    # Verificar que no sea un bot
    if member.bot:
        await ctx.send("❌ No puedo añadir bots al canal")
        return

    try:
        # Crear permisos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = True
        overwrites.send_messages = True
        overwrites.read_message_history = True
        overwrites.add_reactions = True

        # Aplicar permisos al canal actual
        await ctx.channel.set_permissions(member, overwrite=overwrites)

        # Generar consejos ÚNICOS con IA
        print("🤖 Generando consejos ÚNICOS con IA...")
        advice_trader = generate_advice("trader")
        advice_middleman = generate_advice("middleman")

        print(f"📊 Trader: {advice_trader[:80]}...")
        print(f"🤝 Middleman: {advice_middleman[:80]}...")

        # Crear y enviar embed
        embed = create_welcome_embed(member, advice_trader, advice_middleman)

        # Enviar el embed
        mensaje = await ctx.send(embed=embed)
        print(f"✅ Embed enviado - ID: {mensaje.id}")
        print(f"✅ {member.name} añadido al canal {ctx.channel.name}")

    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos suficientes para modificar los permisos del canal")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Error HTTP al enviar el embed: {str(e)}")
        print(f"Error HTTP completo: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        await ctx.send(f"❌ Error al añadir usuario: {str(e)}")
        print(f"Error completo: {e}")
        import traceback
        traceback.print_exc()

@bot.command(name='quit')
async def remove_user(ctx, member: discord.Member = None, user_id: str = None):
    """
    Remueve a un usuario del canal
    Uso: !quit @usuario o !quit ID_USUARIO
    """
    # Obtener el miembro
    if member is None and user_id:
        try:
            member = await ctx.guild.fetch_member(int(user_id))
        except:
            await ctx.send("❌ No se pudo encontrar el usuario con ese ID")
            return

    if member is None:
        await ctx.send("❌ Por favor menciona un usuario o proporciona su ID\nUso: `!quit @usuario` o `!quit ID_USUARIO`")
        return

    try:
        # Remover permisos específicos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = False
        overwrites.send_messages = False

        # Aplicar permisos
        await ctx.channel.set_permissions(member, overwrite=overwrites)

        # Crear y enviar embed
        embed = create_removed_embed(member)
        await ctx.send(embed=embed)

        print(f"✅ {member.name} removido del canal {ctx.channel.name}")

    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos suficientes para modificar los permisos del canal")
    except Exception as e:
        await ctx.send(f"❌ Error al remover usuario: {str(e)}")
        print(f"Error: {e}")

@bot.command(name='help_bot')
async def help_command(ctx):
    """Muestra los comandos disponibles"""
    embed = discord.Embed(
        title="📚 Comandos del Bot",
        description="Sistema de gestión con consejos únicos de IA",
        color=0x3498DB
    )

    embed.add_field(
        name="!add @usuario",
        value="Añade usuario al canal. Genera consejos ÚNICOS cada vez con IA.",
        inline=False
    )

    embed.add_field(
        name="!quit @usuario",
        value="Remueve usuario del canal.",
        inline=False
    )

    embed.add_field(
        name="💡 Info",
        value="**Middleman**: Intermediario que evita estafas.\n**Trader**: Intercambia objetos/cuentas digitales.",
        inline=False
    )

    embed.set_footer(text="Powered by Gemma 3 4B AI | Consejos únicos garantizados")

    await ctx.send(embed=embed)

# Manejo de errores
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ No pude encontrar ese usuario. Asegúrate de mencionarlo correctamente o usar su ID.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Faltan argumentos. Usa `!help_bot` para ver cómo usar los comandos.")
    else:
        print(f"Error: {error}")
        import traceback
        traceback.print_exc()

# Iniciar el bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ ERROR: DISCORD_TOKEN no encontrado en las variables de entorno")
    else:
        print("🚀 Iniciando bot con IA Gemma 3 4B...")
        print("🎲 Sistema de variabilidad MÁXIMA activado")
        bot.run(token)
