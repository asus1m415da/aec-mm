# Cat's Discord Bot - Versión Mejorada v2.0
import discord
import google.generativeai as genai
import os
from dotenv import load_dotenv
import random
import time
import hashlib
import sys

# ✅ VERIFICACIÓN DE DEPENDENCIAS
print("🔍 Verificando dependencias...")
print(f"   Python: v{sys.version.split()[0]}")
print(f"   discord.py-self: v{discord.__version__}")

try:
    import discord_self_embed
    EMBEDS_DISPONIBLES = True
    print(f"   discord.py-self-embed: v{discord_self_embed.__version__}")
except ImportError:
    EMBEDS_DISPONIBLES = False
    print("   ⚠️  discord.py-self-embed: No instalado")
    print("   💡 Ejecuta: pip install -r requirements.txt")
except AttributeError:
    EMBEDS_DISPONIBLES = True
    print("   discord.py-self-embed: Instalado")

print()

load_dotenv()

# Cliente sin warnings
client = discord.Client(chunk_guilds_at_startup=False)

# 🔐 ROLES AUTORIZADOS
AUTHORIZED_ROLES = [
    1329516197175103651,
    1427705211186839672
]

def setup_gemma():
    """Configura cliente de Gemini AI"""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY no encontrada en .env")
    genai.configure(api_key=api_key)
    return True

try:
    gemma_client = setup_gemma()
except Exception as e:
    print(f"⚠️ Error configurando Gemini: {e}")
    gemma_client = False

consejos_history = {"trader": [], "middleman": []}

def has_authorized_role(member):
    """Verifica si el miembro tiene rol autorizado"""
    if member is None:
        return False
    member_role_ids = [role.id for role in member.roles]
    return any(role_id in member_role_ids for role_id in AUTHORIZED_ROLES)

def generate_advice(user_type):
    """Genera consejo único con IA o fallback"""
    if not gemma_client:
        return consejos_fallback(user_type)

    timestamp = int(time.time() * 1000)
    random_num = random.randint(10000, 99999)
    unique_seed = hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()[:8]

    enfoques = {
        "trader": [
            "seguridad en verificación de middlemans",
            "protección contra scams",
            "documentación de trades",
            "señales de alerta",
            "comunicación efectiva",
            "protección de información",
            "uso de sistemas escrow",
            "verificación de reputación"
        ],
        "middleman": [
            "construcción de confianza",
            "transparencia en procesos",
            "documentación profesional",
            "comunicación clara",
            "gestión de conflictos",
            "protección de datos",
            "mejora de reputación",
            "profesionalismo"
        ]
    }

    enfoque = random.choice(enfoques[user_type])
    estilo = random.choice(["directo", "motivador", "preventivo", "educativo", "práctico"])

    contexto = "Middleman: intermediario anti-estafas en trades digitales. Trader: usuario que intercambia items."

    prompt = f"""{contexto}

Genera UN consejo ÚNICO para {user_type}s (máximo 100 caracteres).
Enfoque: {enfoque} | Estilo: {estilo}
NO repitas: {', '.join(consejos_history[user_type][-3:]) if consejos_history[user_type] else 'ninguno'}
Semilla: {unique_seed}
Sin markdown, texto simple."""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=1.0,
                top_p=0.95,
                top_k=40,
                max_output_tokens=60,
            )
        )

        advice = response.text.strip()[:280]
        
        consejos_history[user_type].append(advice[:50])
        if len(consejos_history[user_type]) > 5:
            consejos_history[user_type].pop(0)

        return advice

    except Exception as e:
        print(f"⚠️ Error IA: {e}")
        return consejos_fallback(user_type)

def consejos_fallback(user_type):
    """Consejos predeterminados si IA falla"""
    fallback = {
        "trader": [
            "Verifica reputación en múltiples servidores",
            "Nunca compartas archivos .HAR",
            "Graba video del trade completo",
            "Presión rápida = red flag",
            "Usa middlemen con +100 trades",
            "Pide referencias antes de iniciar",
            "Confirma identidad en servidor oficial",
            "Revisa roles verificados",
            "Conversaciones solo en Discord",
            "Screenshots de cada paso",
            "Evita tarifas +10% del trade",
            "Busca sistema de tickets",
            "Activa 2FA antes de tradear",
            "Sin límites de tiempo artificial",
            "Confía en tu instinto"
        ],
        "middleman": [
            "Registro público con timestamps",
            "Nunca pidas contraseñas",
            "Responde en -5 minutos",
            "Publica testimonios regularmente",
            "Sistema de tickets profesional",
            "Explica cada paso del proceso",
            "Guarda evidencias 30+ días",
            "Comunicación constante",
            "Garantías claras escritas",
            "Actualiza estadísticas semanales",
            "Rechaza trades sospechosos",
            "Sé imparcial siempre",
            "Verifica autenticidad de items",
            "Cumple tiempos establecidos",
            "Admite errores si ocurren"
        ]
    }

    disponibles = [c for c in fallback[user_type] 
                  if not any(c[:50] == h for h in consejos_history[user_type][-3:])]

    if not disponibles:
        disponibles = fallback[user_type]

    consejo = random.choice(disponibles)
    
    consejos_history[user_type].append(consejo[:50])
    if len(consejos_history[user_type]) > 5:
        consejos_history[user_type].pop(0)

    return consejo

def create_welcome_message(member, advice_trader, advice_middleman):
    """Crea mensaje de bienvenida con embed o texto"""
    
    # Validación
    advice_trader = advice_trader[:280] if advice_trader else "Verifica reputación del middleman"
    advice_middleman = advice_middleman[:280] if advice_middleman else "Mantén transparencia en trades"
    
    if EMBEDS_DISPONIBLES:
        try:
            colors = ["00FF00", "00FFFF", "FF00FF", "FFD700", "9B59B6", "E74C3C", "3498DB", "1ABC9C"]
            
            # Descripción compacta (máx 350 chars)
            desc = f"{member.mention} añadido\n\n📊 Traders: {advice_trader[:90]}\n\n🤝 MM: {advice_middleman[:90]}"
            
            embed = discord_self_embed.Embed(
                title="✨ Bienvenido ✨",
                description=desc[:340],
                colour=random.choice(colors)
            )
            
            return embed.generate_url(hide_url=True)
            
        except Exception as e:
            print(f"⚠️ Embed error: {e}")
    
    # Fallback texto
    return f"""✨ **¡Bienvenido al Canal!** ✨

{member.mention} ha sido añadido

📊 **Traders:** {advice_trader}

🤝 **Middlemans:** {advice_middleman}

💎 Middlemans evitan estafas. Verifica reputación.

_Bot de Gestión | Powered by Gemini AI_"""

def create_removed_message(member):
    """Crea mensaje de remoción"""
    
    if EMBEDS_DISPONIBLES:
        try:
            embed = discord_self_embed.Embed(
                title="👋 Usuario Removido",
                description=f"{member.mention} removido del canal",
                colour="FF4444"
            )
            return embed.generate_url(hide_url=True)
        except:
            pass
    
    return f"👋 **Usuario Removido**\n{member.mention} ha sido removido del canal"

@client.event
async def on_ready():
    print(f'✅ Selfbot conectado como {client.user}')
    print(f'   ID: {client.user.id}')
    print(f'   discord.py-self: v{discord.__version__}')
    print('------')
    print(f'🔐 Roles autorizados: {len(AUTHORIZED_ROLES)}')
    for role_id in AUTHORIZED_ROLES:
        print(f'   - {role_id}')
    print(f'🤖 IA Gemini: {"✅" if gemma_client else "❌"}')
    print(f'🎨 Embeds: {"✅" if EMBEDS_DISPONIBLES else "❌"}')
    print('📡 Bot listo\n')

@client.event
async def on_message(message):
    # Ignorar bots
    if message.author.bot:
        return
    
    # Solo comandos con prefijo .
    if not message.content.startswith('.'):
        return
    
    # Solo en servidores
    if not message.guild:
        return
    
    # Obtener miembro
    member = message.guild.get_member(message.author.id)
    if not member:
        return
    
    # Verificar permisos
    if not has_authorized_role(member):
        print(f"❌ {message.author} sin rol autorizado")
        await message.channel.send("❌ No tienes permiso.")
        return
    
    # Comandos
    content_lower = message.content.lower()
    
    if content_lower.startswith('.add'):
        await handle_add(message)
    elif content_lower.startswith('.quit'):
        await handle_quit(message)
    elif content_lower.startswith('.help'):
        await handle_help(message)

async def handle_add(message):
    """Añade usuario al canal"""
    parts = message.content.split()
    
    if len(parts) < 2:
        await message.channel.send("❌ Uso: `.add @usuario` | `.add usuario` | `.add ID`")
        return

    member = None
    query = parts[1]
    
    # Método 1: Mención
    if message.mentions:
        member = message.mentions[0]
    
    # Método 2: ID
    elif query.replace('<@', '').replace('>', '').replace('!', '').isdigit():
        try:
            user_id = int(query.replace('<@', '').replace('>', '').replace('!', ''))
            member = await message.guild.fetch_member(user_id)
        except:
            pass
    
    # Método 3: Nombre
    else:
        query_lower = query.lower()
        
        for m in message.guild.members:
            if m.name.lower() == query_lower or m.display_name.lower() == query_lower:
                member = m
                break
        
        if not member:
            for m in message.guild.members:
                if query_lower in m.name.lower() or query_lower in m.display_name.lower():
                    member = m
                    break

    if not member:
        await message.channel.send(f"❌ Usuario `{query}` no encontrado")
        return

    if member.bot:
        await message.channel.send("❌ No puedo añadir bots")
        return

    try:
        # Establecer permisos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = True
        overwrites.send_messages = True
        overwrites.read_message_history = True
        overwrites.add_reactions = True

        await message.channel.set_permissions(member, overwrite=overwrites)

        # Generar consejos
        advice_trader = generate_advice("trader")
        advice_middleman = generate_advice("middleman")

        # Enviar mensaje
        msg_content = create_welcome_message(member, advice_trader, advice_middleman)
        await message.channel.send(msg_content)
        
        print(f"✅ {member.name} añadido por {message.author.name}")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)}")
        print(f"Error: {e}")

async def handle_quit(message):
    """Remueve usuario del canal"""
    parts = message.content.split()
    
    if len(parts) < 2:
        await message.channel.send("❌ Uso: `.quit @usuario` | `.quit usuario` | `.quit ID`")
        return

    member = None
    query = parts[1]
    
    # Buscar usuario (mismo método que add)
    if message.mentions:
        member = message.mentions[0]
    elif query.replace('<@', '').replace('>', '').replace('!', '').isdigit():
        try:
            user_id = int(query.replace('<@', '').replace('>', '').replace('!', ''))
            member = await message.guild.fetch_member(user_id)
        except:
            pass
    else:
        query_lower = query.lower()
        for m in message.guild.members:
            if m.name.lower() == query_lower or m.display_name.lower() == query_lower:
                member = m
                break
        
        if not member:
            for m in message.guild.members:
                if query_lower in m.name.lower() or query_lower in m.display_name.lower():
                    member = m
                    break

    if not member:
        await message.channel.send(f"❌ Usuario `{query}` no encontrado")
        return

    try:
        # Quitar permisos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = False
        overwrites.send_messages = False

        await message.channel.set_permissions(member, overwrite=overwrites)

        # Enviar confirmación
        msg_content = create_removed_message(member)
        await message.channel.send(msg_content)

        print(f"✅ {member.name} removido por {message.author.name}")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)}")
        print(f"Error: {e}")

async def handle_help(message):
    """Muestra comandos disponibles"""
    
    if EMBEDS_DISPONIBLES:
        try:
            embed = discord_self_embed.Embed(
                title="📚 Comandos del Bot",
                description="Sistema con IA\n.add usuario | .quit usuario | .help\nSolo roles autorizados",
                colour="3498DB"
            )
            
            await message.channel.send(embed.generate_url(hide_url=True))
            return
        except:
            pass
    
    # Fallback texto
    texto = f"""📚 **Comandos del Bot**

Sistema con IA - Solo roles autorizados

**.add usuario** - Añade al canal
`.add @usuario` | `.add usuario` | `.add ID`

**.quit usuario** - Remueve del canal
(mismos métodos que .add)

**.help** - Muestra esta ayuda

🔐 {len(AUTHORIZED_ROLES)} roles autorizados
_Powered by Gemini AI | Cat's Edition_"""
    
    await message.channel.send(texto)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: DISCORD_TOKEN no encontrado en .env")
        print("💡 Crea un archivo .env con:")
        print("   DISCORD_TOKEN=tu_token_aqui")
        print("   GOOGLE_API_KEY=tu_api_key_aqui")
        exit(1)
    
    print("🚀 Iniciando selfbot...")
    print(f"🔐 {len(AUTHORIZED_ROLES)} roles autorizados\n")
    
    try:
        client.run(token)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
