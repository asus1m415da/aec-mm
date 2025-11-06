# Cat's Discord Bot - Compatible con discord.py-self 1.9.2
import discord
import google.generativeai as genai  # ✅ IMPORT CORREGIDO
import os
from dotenv import load_dotenv
import random
import time
import hashlib

load_dotenv()

client = discord.Client()

AUTHORIZED_ROLE_ID = 1427705211186839672

def setup_gemma():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY no encontrada")
    genai.configure(api_key=api_key)  # ✅ CONFIGURACIÓN CORREGIDA
    return True

try:
    gemma_client = setup_gemma()
except Exception as e:
    print(f"Error al configurar Gemini: {e}")
    gemma_client = False

consejos_history = {"trader": [], "middleman": []}

def has_authorized_role(member):
    if member is None:
        return False
    member_role_ids = [role.id for role in member.roles]
    return AUTHORIZED_ROLE_ID in member_role_ids

def generate_advice(user_type):
    if not gemma_client:
        return "⚠️ El servicio de IA no está disponible."

    timestamp = int(time.time() * 1000)
    random_num = random.randint(10000, 99999)
    unique_seed = hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()[:8]

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

    contexto = """Middleman: intermediario que evita estafas en trades digitales (Roblox/Discord).
Trader: usuario que intercambia objetos/cuentas digitales."""

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
        # ✅ API CORREGIDA para google-generativeai
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(
            prompts[user_type],
            generation_config=genai.types.GenerationConfig(
                temperature=1.0,
                top_p=0.95,
                top_k=40,
                max_output_tokens=150,
            )
        )

        advice = response.text.strip()

        if len(advice) > 800:
            advice = advice[:797] + "..."

        consejos_history[user_type].append(advice[:50])
        if len(consejos_history[user_type]) > 5:
            consejos_history[user_type].pop(0)

        return advice

    except Exception as e:
        print(f"⚠️ Error generando consejo: {e}")

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

        disponibles = [c for c in consejos_fallback[user_type] 
                      if not any(c[:50] == h for h in consejos_history[user_type][-3:])]

        if not disponibles:
            disponibles = consejos_fallback[user_type]

        consejo = random.choice(disponibles)

        consejos_history[user_type].append(consejo[:50])
        if len(consejos_history[user_type]) > 5:
            consejos_history[user_type].pop(0)

        return consejo

def create_welcome_embed(member, advice_trader, advice_middleman):
    colors = [0x00FF00, 0x00FFFF, 0xFF00FF, 0xFFD700, 0xFF6347, 0x9B59B6, 0xE74C3C, 0x3498DB, 0x1ABC9C, 0xF39C12]

    embed = discord.Embed(
        title="✨ ¡Bienvenido al Canal! ✨",
        description=f"**{member.mention}** ha sido añadido al canal",
        color=random.choice(colors)
    )

    try:
        embed.set_thumbnail(url=member.display_avatar.url)
    except:
        embed.set_thumbnail(url=member.avatar_url)

    embed.add_field(
        name="📊 Consejo para Traders",
        value=f"> {advice_trader}",
        inline=False
    )

    embed.add_field(
        name="🤝 Consejo para Middlemans",
        value=f"> {advice_middleman}",
        inline=False
    )

    embed.add_field(
        name="💎 Recordatorio",
        value="Middlemans evitan estafas en trades de alto valor. Verifica reputación y documenta todo.",
        inline=False
    )

    embed.set_footer(text="Bot de Gestión | Powered by Gemini AI")

    return embed

def create_removed_embed(member):
    embed = discord.Embed(
        title="👋 Usuario Removido",
        description=f"**{member.mention}** ha sido removido del canal",
        color=0xFF4444
    )

    try:
        embed.set_thumbnail(url=member.display_avatar.url)
    except:
        embed.set_thumbnail(url=member.avatar_url)
    
    embed.set_footer(text="Bot de Gestión de Canales")

    return embed

@client.event
async def on_ready():
    print(f'✅ Selfbot conectado como {client.user}')
    print(f'ID: {client.user.id}')
    print(f'discord.py-self versión: {discord.__version__}')
    print('------')
    print(f'🔐 ROL AUTORIZADO: {AUTHORIZED_ROLE_ID}')
    if gemma_client:
        print('🤖 IA Gemini activada')
    else:
        print('⚠️ IA no disponible')
    print('📡 Bot listo - Solo usuarios con rol autorizado pueden usar comandos')

@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    if not message.content.startswith('!'):
        return
    
    if not message.guild:
        return
    
    member = message.guild.get_member(message.author.id)
    
    if not member:
        return
    
    if not has_authorized_role(member):
        print(f"❌ {message.author} sin rol autorizado")
        await message.channel.send("❌ No tienes permiso para usar este comando.")
        return
    
    print(f"✅ Usuario autorizado: {message.author} - {message.content}")
    
    if message.content.startswith('!add'):
        await handle_add(message)
    elif message.content.startswith('!quit'):
        await handle_quit(message)
    elif message.content.startswith('!help_bot'):
        await handle_help(message)

async def handle_add(message):
    parts = message.content.split()
    
    if len(parts) < 2:
        await message.channel.send("❌ Uso: `!add @usuario` o `!add ID_USUARIO`")
        return

    member = None
    
    if message.mentions:
        member = message.mentions[0]
    else:
        try:
            user_id = int(parts[1].replace('<@', '').replace('>', '').replace('!', ''))
            member = await message.guild.fetch_member(user_id)
        except:
            await message.channel.send("❌ No se pudo encontrar el usuario")
            return

    if member is None:
        await message.channel.send("❌ Usuario no encontrado")
        return

    if member.bot:
        await message.channel.send("❌ No puedo añadir bots")
        return

    try:
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = True
        overwrites.send_messages = True
        overwrites.read_message_history = True
        overwrites.add_reactions = True

        await message.channel.set_permissions(member, overwrite=overwrites)

        print("🤖 Generando consejos con IA...")
        advice_trader = generate_advice("trader")
        advice_middleman = generate_advice("middleman")

        embed = create_welcome_embed(member, advice_trader, advice_middleman)

        await message.channel.send(embed=embed)
        
        print(f"✅ {member.name} añadido por {message.author.name}")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)}")
        print(f"Error completo: {e}")
        import traceback
        traceback.print_exc()

async def handle_quit(message):
    parts = message.content.split()
    
    if len(parts) < 2:
        await message.channel.send("❌ Uso: `!quit @usuario` o `!quit ID_USUARIO`")
        return

    member = None
    
    if message.mentions:
        member = message.mentions[0]
    else:
        try:
            user_id = int(parts[1].replace('<@', '').replace('>', '').replace('!', ''))
            member = await message.guild.fetch_member(user_id)
        except:
            await message.channel.send("❌ No se pudo encontrar el usuario")
            return

    if member is None:
        await message.channel.send("❌ Usuario no encontrado")
        return

    try:
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = False
        overwrites.send_messages = False

        await message.channel.set_permissions(member, overwrite=overwrites)

        embed = create_removed_embed(member)
        await message.channel.send(embed=embed)

        print(f"✅ {member.name} removido por {message.author.name}")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)}")
        print(f"Error: {e}")

async def handle_help(message):
    embed = discord.Embed(
        title="📚 Comandos del Bot",
        description="Sistema de gestión con IA\n🔐 **Solo para usuarios con rol autorizado**",
        color=0x3498DB
    )

    embed.add_field(
        name="!add @usuario",
        value="Añade usuario al canal con consejos únicos de IA",
        inline=False
    )

    embed.add_field(
        name="!quit @usuario",
        value="Remueve usuario del canal",
        inline=False
    )

    embed.add_field(
        name="🔐 Seguridad",
        value=f"Solo el rol <@&{AUTHORIZED_ROLE_ID}> puede usar comandos",
        inline=False
    )

    embed.set_footer(text="Powered by Gemini AI | Cat's Edition")

    await message.channel.send(embed=embed)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ ERROR: DISCORD_TOKEN no encontrado")
    else:
        print("🚀 Iniciando selfbot...")
        print(f"🔐 ROL AUTORIZADO: {AUTHORIZED_ROLE_ID}")
        client.run(token)
