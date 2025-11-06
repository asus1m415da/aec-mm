# Cat's Discord Bot - Versión discord.py-self con Control de Roles
import discord
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import random
import time
import hashlib

# Cargar variables de entorno
load_dotenv()

# Configuración del cliente (selfbot)
client = discord.Client()

# ✨ ROLES AUTORIZADOS PARA USAR LOS COMANDOS ✨
AUTHORIZED_ROLES = [
    1427705211186839672,
    1329516197175103651,
    1330597790660694047,
    1330356239103688835
]

# Configurar Google AI con Gemma
def setup_gemma():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY no encontrada en las variables de entorno")
    client_ai = genai.Client(api_key=api_key)
    return client_ai

# Inicializar cliente de Gemma
try:
    gemma_client = setup_gemma()
except Exception as e:
    print(f"Error al configurar Gemma: {e}")
    gemma_client = None

# Historial de consejos generados (para evitar repeticiones)
consejos_history = {"trader": [], "middleman": []}

# ✅ FUNCIÓN PARA VERIFICAR SI EL USUARIO TIENE ROLES AUTORIZADOS
def has_authorized_role(member):
    """Verifica si el miembro tiene alguno de los roles autorizados"""
    if member is None:
        return False
    
    member_role_ids = [role.id for role in member.roles]
    
    for role_id in AUTHORIZED_ROLES:
        if role_id in member_role_ids:
            return True
    
    return False

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
                top_p=98,       # Máxima diversidad
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
        icon_url=client.user.display_avatar.url if client.user else None
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

@client.event
async def on_ready():
    print(f'✅ Selfbot conectado como {client.user}')
    print(f'ID: {client.user.id}')
    print('------')
    print(f'🔐 Roles autorizados: {len(AUTHORIZED_ROLES)} configurados')
    for role_id in AUTHORIZED_ROLES:
        print(f'   - {role_id}')
    if gemma_client:
        print('🤖 IA Gemma 3 4B activada con MÁXIMA variabilidad')
        print('🎲 Sistema anti-repetición activado')
    else:
        print('⚠️ IA no disponible')

@client.event
async def on_message(message):
    # Ignorar mensajes de otros usuarios
    if message.author != client.user:
        return

    # ✅ VERIFICAR ROLES ANTES DE PROCESAR COMANDOS
    if message.guild:  # Solo verificar en servidores
        author_member = message.guild.get_member(message.author.id)
        
        if not has_authorized_role(author_member):
            # Si el usuario no tiene rol autorizado, ignorar silenciosamente
            if message.content.startswith(('!add', '!quit', '!help_bot')):
                await message.channel.send("❌ No tienes permiso para usar este comando. Necesitas uno de los roles autorizados.")
                print(f"⚠️ Usuario {message.author} intentó usar comando sin rol autorizado")
            return

    # Sistema de comandos manual
    if message.content.startswith('!add'):
        await handle_add(message)
    elif message.content.startswith('!quit'):
        await handle_quit(message)
    elif message.content.startswith('!help_bot'):
        await handle_help(message)

async def handle_add(message):
    """
    Añade un usuario al canal con permisos de lectura y escritura
    Uso: !add @usuario o !add ID_USUARIO
    """
    parts = message.content.split()
    
    if len(parts) < 2:
        await message.channel.send("❌ Por favor menciona un usuario o proporciona su ID\nUso: `!add @usuario` o `!add ID_USUARIO`")
        return

    # Obtener el miembro
    member = None
    
    # Verificar si hay mención
    if message.mentions:
        member = message.mentions[0]
    else:
        # Intentar por ID
        try:
            user_id = int(parts[1])
            member = await message.guild.fetch_member(user_id)
        except:
            await message.channel.send("❌ No se pudo encontrar el usuario con ese ID")
            return

    if member is None:
        await message.channel.send("❌ No se pudo encontrar el usuario")
        return

    # Verificar que no sea un bot
    if member.bot:
        await message.channel.send("❌ No puedo añadir bots al canal")
        return

    try:
        # Crear permisos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = True
        overwrites.send_messages = True
        overwrites.read_message_history = True
        overwrites.add_reactions = True

        # Aplicar permisos al canal actual
        await message.channel.set_permissions(member, overwrite=overwrites)

        # Generar consejos ÚNICOS con IA
        print("🤖 Generando consejos ÚNICOS con IA...")
        advice_trader = generate_advice("trader")
        advice_middleman = generate_advice("middleman")

        print(f"📊 Trader: {advice_trader[:80]}...")
        print(f"🤝 Middleman: {advice_middleman[:80]}...")

        # Crear y enviar embed
        embed = create_welcome_embed(member, advice_trader, advice_middleman)

        # Enviar el embed
        mensaje = await message.channel.send(embed=embed)
        print(f"✅ Embed enviado - ID: {mensaje.id}")
        print(f"✅ {member.name} añadido al canal {message.channel.name} por {message.author.name}")

    except discord.Forbidden:
        await message.channel.send("❌ No tengo permisos suficientes para modificar los permisos del canal")
    except discord.HTTPException as e:
        await message.channel.send(f"❌ Error HTTP al enviar el embed: {str(e)}")
        print(f"Error HTTP completo: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        await message.channel.send(f"❌ Error al añadir usuario: {str(e)}")
        print(f"Error completo: {e}")
        import traceback
        traceback.print_exc()

async def handle_quit(message):
    """
    Remueve a un usuario del canal
    Uso: !quit @usuario o !quit ID_USUARIO
    """
    parts = message.content.split()
    
    if len(parts) < 2:
        await message.channel.send("❌ Por favor menciona un usuario o proporciona su ID\nUso: `!quit @usuario` o `!quit ID_USUARIO`")
        return

    # Obtener el miembro
    member = None
    
    # Verificar si hay mención
    if message.mentions:
        member = message.mentions[0]
    else:
        # Intentar por ID
        try:
            user_id = int(parts[1])
            member = await message.guild.fetch_member(user_id)
        except:
            await message.channel.send("❌ No se pudo encontrar el usuario con ese ID")
            return

    if member is None:
        await message.channel.send("❌ No se pudo encontrar el usuario")
        return

    try:
        # Remover permisos específicos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = False
        overwrites.send_messages = False

        # Aplicar permisos
        await message.channel.set_permissions(member, overwrite=overwrites)

        # Crear y enviar embed
        embed = create_removed_embed(member)
        await message.channel.send(embed=embed)

        print(f"✅ {member.name} removido del canal {message.channel.name} por {message.author.name}")

    except discord.Forbidden:
        await message.channel.send("❌ No tengo permisos suficientes para modificar los permisos del canal")
    except Exception as e:
        await message.channel.send(f"❌ Error al remover usuario: {str(e)}")
        print(f"Error: {e}")

async def handle_help(message):
    """Muestra los comandos disponibles"""
    embed = discord.Embed(
        title="📚 Comandos del Bot",
        description="Sistema de gestión con consejos únicos de IA\n🔐 **Solo disponible para roles autorizados**",
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

    embed.add_field(
        name="🔐 Seguridad",
        value=f"Solo usuarios con roles autorizados pueden usar estos comandos.\n**Roles configurados:** {len(AUTHORIZED_ROLES)}",
        inline=False
    )

    embed.set_footer(text="Powered by Gemma 3 4B AI | Consejos únicos garantizados | Cat's Edition")

    await message.channel.send(embed=embed)

# Iniciar el selfbot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ ERROR: DISCORD_TOKEN no encontrado en las variables de entorno")
    else:
        print("🚀 Iniciando selfbot con IA Gemma 3 4B...")
        print("🎲 Sistema de variabilidad MÁXIMA activado")
        print("🔐 Sistema de control de roles activado")
        print("⚠️ ADVERTENCIA: Los selfbots violan los ToS de Discord")
        client.run(token, bot=False)
