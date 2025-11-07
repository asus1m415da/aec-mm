# Cat's Discord Bot - Versión Final v2.5
import discord
import os
from dotenv import load_dotenv
import random
import time
import hashlib
import sys

# ✅ VERIFICACIÓN DE DEPENDENCIAS (ORDEN CORRECTO)
print("\n🔍 Verificando dependencias...")
print(f"   Python: v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print(f"   discord.py-self: v{discord.__version__}")

try:
    import discord_self_embed
    EMBEDS_DISPONIBLES = True
    print("   ✅ discord.py-self-embed: Instalado")
except ImportError:
    EMBEDS_DISPONIBLES = False
    print("   ⚠️  discord.py-self-embed: No instalado")

try:
    import google.generativeai as genai
    GEMINI_DISPONIBLE = True
    print("   ✅ google-generativeai: Instalado")
except ImportError:
    genai = None
    GEMINI_DISPONIBLE = False
    print("   ⚠️  google-generativeai: No instalado")

print()

load_dotenv()

# Cliente optimizado
client = discord.Client(
    chunk_guilds_at_startup=False,
    max_messages=None
)

# 🔐 ROLES AUTORIZADOS
AUTHORIZED_ROLES = [
    1329516197175103651,
    1427705211186839672
]

# Estado del bot
consejos_history = {"trader": [], "middleman": []}
gemma_client = False

def setup_gemma():
    """Configura Gemini AI"""
    try:
        if not GEMINI_DISPONIBLE:
            return False
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"⚠️ Error Gemini: {e}")
        return False

gemma_client = setup_gemma()

def has_authorized_role(member):
    """Verifica rol autorizado"""
    try:
        if member is None:
            return False
        member_role_ids = [role.id for role in member.roles]
        has_role = any(role_id in member_role_ids for role_id in AUTHORIZED_ROLES)
        return has_role
    except Exception as e:
        print(f"Error verificando roles: {e}")
        return False

def generate_advice(user_type):
    """Genera consejo con IA o fallback"""
    if not gemma_client:
        return get_fallback_advice(user_type)

    try:
        timestamp = int(time.time() * 1000)
        random_num = random.randint(10000, 99999)
        unique_seed = hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()[:8]

        prompt = f"""Consejo corto para {user_type}s de trading (max 80 chars).
Semilla: {unique_seed}
Sin repetir: {', '.join(consejos_history[user_type][-2:]) if consejos_history[user_type] else 'ninguno'}"""

        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=1.0,
                max_output_tokens=40,
            )
        )

        advice = response.text.strip()[:220]
        
        consejos_history[user_type].append(advice[:35])
        if len(consejos_history[user_type]) > 4:
            consejos_history[user_type].pop(0)

        return advice

    except Exception as e:
        print(f"⚠️ IA error: {e}")
        return get_fallback_advice(user_type)

def get_fallback_advice(user_type):
    """Consejos predeterminados"""
    fallback = {
        "trader": [
            "Verifica reputación en múltiples servidores",
            "Nunca compartas archivos .HAR",
            "Graba video del trade",
            "Usa middlemen con +100 trades",
            "Pide referencias antes",
            "Confirma identidad oficial",
            "Revisa roles verificados",
            "Screenshots de cada paso",
            "Activa 2FA antes",
            "Confía en tu instinto"
        ],
        "middleman": [
            "Registro público transparente",
            "Nunca pidas contraseñas",
            "Responde rápido",
            "Testimonios regularmente",
            "Sistema de tickets",
            "Explica cada paso",
            "Guarda evidencias 30+ días",
            "Comunicación constante",
            "Políticas claras",
            "Sé imparcial"
        ]
    }

    disponibles = fallback.get(user_type, fallback["trader"])
    
    usados = consejos_history[user_type][-2:] if consejos_history[user_type] else []
    disponibles = [c for c in disponibles if c[:35] not in [u[:35] for u in usados]]
    
    if not disponibles:
        disponibles = fallback[user_type]

    consejo = random.choice(disponibles)
    
    consejos_history[user_type].append(consejo[:35])
    if len(consejos_history[user_type]) > 4:
        consejos_history[user_type].pop(0)

    return consejo

def create_welcome_message(member, advice_trader, advice_middleman):
    """Crea mensaje de bienvenida"""
    try:
        advice_trader = str(advice_trader)[:200] if advice_trader else "Verifica reputación"
        advice_middleman = str(advice_middleman)[:200] if advice_middleman else "Mantén transparencia"
        
        if EMBEDS_DISPONIBLES:
            try:
                colors = ["00FF00", "00FFFF", "FF00FF", "FFD700", "9B59B6", "3498DB"]
                
                desc = f"{member.mention} añadido\n\n📊 {advice_trader[:70]}\n🤝 {advice_middleman[:70]}"
                
                embed = discord_self_embed.Embed(
                    title="✨ Bienvenido ✨",
                    description=desc[:300],
                    colour=random.choice(colors)
                )
                
                return embed.generate_url(hide_url=True)
            except Exception as e:
                print(f"⚠️ Embed error: {e}")
        
        return f"""✨ **¡Bienvenido!** ✨

{member.mention} añadido al canal

📊 **Traders:** {advice_trader}
🤝 **Middlemans:** {advice_middleman}

💎 Verifica reputación y documenta todo.
_Bot | Powered by Gemini AI_"""
    
    except Exception as e:
        print(f"Error mensaje: {e}")
        return f"✨ {member.mention} añadido al canal"

def create_removed_message(member):
    """Crea mensaje de remoción"""
    try:
        if EMBEDS_DISPONIBLES:
            try:
                embed = discord_self_embed.Embed(
                    title="👋 Usuario Removido",
                    description=f"{member.mention} removido",
                    colour="FF4444"
                )
                return embed.generate_url(hide_url=True)
            except:
                pass
        
        return f"👋 **Removido:** {member.mention}"
    except:
        return "👋 Usuario removido"

@client.event
async def on_ready():
    """Bot listo"""
    print(f'✅ Selfbot conectado como {client.user}')
    print(f'   ID: {client.user.id}')
    print('------')
    print(f'🔐 Roles autorizados: {len(AUTHORIZED_ROLES)}')
    print(f'🤖 IA Gemini: {"✅" if gemma_client else "❌"}')
    print(f'🎨 Embeds: {"✅" if EMBEDS_DISPONIBLES else "❌"}')
    print(f'💲 Prefijo: $')
    print('📡 Bot listo - Esperando comandos...\n')

@client.event
async def on_message(message):
    """Procesa comandos"""
    try:
        # Debug: Ver TODOS los mensajes
        if message.content.startswith('$'):
            print(f"[DEBUG] Mensaje detectado: '{message.content}' de {message.author}")
        
        # Ignorar bots
        if message.author.bot:
            return
        
        # Solo comandos con $
        if not message.content.startswith('$'):
            return
        
        # Solo en servidores
        if not message.guild:
            await message.channel.send("❌ Solo funciona en servidores")
            return
        
        # Obtener miembro
        member = message.guild.get_member(message.author.id)
        if not member:
            print(f"[DEBUG] No se pudo obtener miembro para {message.author}")
            return
        
        # Verificar permisos
        if not has_authorized_role(member):
            print(f"[DEBUG] {message.author} sin rol autorizado")
            await message.channel.send("❌ Sin permisos.")
            return
        
        print(f"[✅] Comando autorizado: {message.content} por {message.author}")
        
        # Comandos
        content = message.content.lower().strip()
        
        if content.startswith('$add'):
            await handle_add(message)
        elif content.startswith('$quit'):
            await handle_quit(message)
        elif content.startswith('$help'):
            await handle_help(message)
        else:
            await message.channel.send(f"❌ Comando desconocido. Usa `$help`")
    
    except Exception as e:
        print(f"[ERROR] on_message: {e}")
        import traceback
        traceback.print_exc()

async def handle_add(message):
    """Añade usuario"""
    try:
        parts = message.content.split()
        
        if len(parts) < 2:
            await message.channel.send("❌ Uso: `$add @usuario` | `$add nombre` | `$add ID`")
            return

        member = None
        query = parts[1]
        
        # Mención
        if message.mentions and len(message.mentions) > 0:
            member = message.mentions[0]
            print(f"[DEBUG] Usuario encontrado por mención: {member.name}")
        
        # ID
        elif query.replace('<@', '').replace('>', '').replace('!', '').isdigit():
            try:
                user_id = int(query.replace('<@', '').replace('>', '').replace('!', ''))
                member = await message.guild.fetch_member(user_id)
                print(f"[DEBUG] Usuario encontrado por ID: {member.name}")
            except Exception as e:
                print(f"[DEBUG] ID no encontrado: {e}")
        
        # Nombre
        else:
            query_lower = query.lower()
            
            for m in message.guild.members:
                if m.name.lower() == query_lower or m.display_name.lower() == query_lower:
                    member = m
                    print(f"[DEBUG] Usuario encontrado por nombre exacto: {member.name}")
                    break
            
            if not member:
                for m in message.guild.members:
                    if query_lower in m.name.lower() or query_lower in m.display_name.lower():
                        member = m
                        print(f"[DEBUG] Usuario encontrado por nombre parcial: {member.name}")
                        break

        if not member:
            await message.channel.send(f"❌ Usuario `{query}` no encontrado")
            return

        if member.bot:
            await message.channel.send("❌ No puedo añadir bots")
            return

        # Permisos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = True
        overwrites.send_messages = True
        overwrites.read_message_history = True
        overwrites.add_reactions = True

        await message.channel.set_permissions(member, overwrite=overwrites)

        # Consejos
        advice_trader = generate_advice("trader")
        advice_middleman = generate_advice("middleman")

        # Enviar
        msg_content = create_welcome_message(member, advice_trader, advice_middleman)
        await message.channel.send(msg_content)
        
        print(f"[✅] {member.name} añadido por {message.author.name}")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)[:100]}")
        print(f"[ERROR] handle_add: {e}")
        import traceback
        traceback.print_exc()

async def handle_quit(message):
    """Remueve usuario"""
    try:
        parts = message.content.split()
        
        if len(parts) < 2:
            await message.channel.send("❌ Uso: `$quit @usuario` | `$quit nombre` | `$quit ID`")
            return

        member = None
        query = parts[1]
        
        if message.mentions and len(message.mentions) > 0:
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

        # Quitar permisos
        overwrites = discord.PermissionOverwrite()
        overwrites.view_channel = False
        overwrites.send_messages = False

        await message.channel.set_permissions(member, overwrite=overwrites)

        msg_content = create_removed_message(member)
        await message.channel.send(msg_content)

        print(f"[✅] {member.name} removido por {message.author.name}")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)[:100]}")
        print(f"[ERROR] handle_quit: {e}")

async def handle_help(message):
    """Muestra ayuda"""
    try:
        if EMBEDS_DISPONIBLES:
            try:
                embed = discord_self_embed.Embed(
                    title="📚 Comandos",
                    description="$add usuario | $quit usuario | $help\nSolo roles autorizados",
                    colour="3498DB"
                )
                
                await message.channel.send(embed.generate_url(hide_url=True))
                return
            except:
                pass
        
        texto = f"""📚 **Comandos del Bot**

**$add** - Añade usuario
`$add @user` | `$add nombre` | `$add ID`

**$quit** - Remueve usuario
(mismos métodos)

**$help** - Muestra ayuda

🔐 Solo roles autorizados ({len(AUTHORIZED_ROLES)})
_Powered by Gemini AI_"""
        
        await message.channel.send(texto)
    
    except Exception as e:
        print(f"[ERROR] handle_help: {e}")
        await message.channel.send("📚 Comandos: $add | $quit | $help")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: DISCORD_TOKEN no encontrado en .env")
        exit(1)
    
    print("🚀 Iniciando selfbot...")
    print(f"🔐 {len(AUTHORIZED_ROLES)} roles autorizados")
    print(f"💲 Prefijo de comandos: $\n")
    
    try:
        client.run(token)
    except KeyboardInterrupt:
        print("\n⚠️ Bot detenido")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
