# Cat's Discord Bot - Versión Estable v2.1
import discord
import google.generativeai as genai
import os
from dotenv import load_dotenv
import random
import time
import hashlib
import sys

# ✅ VERIFICACIÓN SEGURA DE DEPENDENCIAS
print("🔍 Verificando dependencias...")
try:
    print(f"   Python: v{sys.version.split()[0]}")
except:
    print(f"   Python: v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

print(f"   discord.py-self: v{discord.__version__}")

try:
    import discord_self_embed
    EMBEDS_DISPONIBLES = True
    try:
        print(f"   discord.py-self-embed: v{discord_self_embed.__version__}")
    except:
        print("   discord.py-self-embed: Instalado")
except ImportError:
    EMBEDS_DISPONIBLES = False
    print("   ⚠️  discord.py-self-embed: No instalado")
    print("   💡 Ejecuta: pip install discord.py-self-embed")

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
    """Configura Gemini AI de forma segura"""
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"⚠️ Error configurando Gemini: {e}")
        return False

# Inicializar IA
gemma_client = setup_gemma()

def has_authorized_role(member):
    """Verifica rol autorizado con manejo de errores"""
    try:
        if member is None:
            return False
        member_role_ids = [role.id for role in member.roles]
        return any(role_id in member_role_ids for role_id in AUTHORIZED_ROLES)
    except:
        return False

def generate_advice(user_type):
    """Genera consejo único con IA o fallback"""
    if not gemma_client:
        return get_fallback_advice(user_type)

    try:
        timestamp = int(time.time() * 1000)
        random_num = random.randint(10000, 99999)
        unique_seed = hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()[:8]

        enfoques = {
            "trader": [
                "seguridad", "protección contra scams", "documentación",
                "señales de alerta", "comunicación", "verificación"
            ],
            "middleman": [
                "confianza", "transparencia", "profesionalismo",
                "comunicación", "gestión", "reputación"
            ]
        }

        enfoque = random.choice(enfoques[user_type])
        
        prompt = f"""Genera UN consejo corto para {user_type}s de trading (máximo 90 caracteres).
Tema: {enfoque}
Sin repetir: {', '.join(consejos_history[user_type][-2:]) if consejos_history[user_type] else 'ninguno'}
Semilla: {unique_seed}
Texto simple."""

        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=1.0,
                top_p=0.95,
                max_output_tokens=50,
            )
        )

        advice = response.text.strip()[:250]
        
        consejos_history[user_type].append(advice[:40])
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
            "Graba video del trade completo",
            "Usa middlemen con +100 trades verificados",
            "Pide referencias antes de iniciar",
            "Confirma identidad en servidor oficial",
            "Revisa roles verificados del MM",
            "Mantén conversaciones en Discord",
            "Screenshots de cada paso",
            "Evita tarifas excesivas",
            "Activa 2FA antes de tradear",
            "Confía en tu instinto"
        ],
        "middleman": [
            "Registro público con evidencias",
            "Nunca pidas contraseñas",
            "Responde rápido durante trades",
            "Publica testimonios regularmente",
            "Sistema de tickets profesional",
            "Explica cada paso claramente",
            "Guarda evidencias 30+ días",
            "Comunicación constante",
            "Políticas claras escritas",
            "Actualiza estadísticas semanales",
            "Rechaza trades sospechosos",
            "Sé imparcial siempre"
        ]
    }

    disponibles = fallback.get(user_type, fallback["trader"])
    
    # Evitar repeticiones recientes
    usados = consejos_history[user_type][-2:] if consejos_history[user_type] else []
    disponibles = [c for c in disponibles if c[:40] not in [u[:40] for u in usados]]
    
    if not disponibles:
        disponibles = fallback[user_type]

    consejo = random.choice(disponibles)
    
    consejos_history[user_type].append(consejo[:40])
    if len(consejos_history[user_type]) > 4:
        consejos_history[user_type].pop(0)

    return consejo

def create_welcome_message(member, advice_trader, advice_middleman):
    """Crea mensaje de bienvenida seguro"""
    try:
        # Validación y límites
        advice_trader = str(advice_trader)[:240] if advice_trader else "Verifica reputación"
        advice_middleman = str(advice_middleman)[:240] if advice_middleman else "Mantén transparencia"
        
        if EMBEDS_DISPONIBLES:
            try:
                colors = ["00FF00", "00FFFF", "FF00FF", "FFD700", "9B59B6", "3498DB"]
                
                desc = f"{member.mention} añadido\n\n📊 {advice_trader[:80]}\n\n🤝 {advice_middleman[:80]}"
                
                embed = discord_self_embed.Embed(
                    title="✨ Bienvenido ✨",
                    description=desc[:320],
                    colour=random.choice(colors)
                )
                
                return embed.generate_url(hide_url=True)
            except Exception as e:
                print(f"⚠️ Embed error: {e}")
        
        # Fallback texto
        return f"""✨ **¡Bienvenido!** ✨

{member.mention} añadido al canal

📊 **Traders:** {advice_trader}

🤝 **Middlemans:** {advice_middleman}

💎 Verifica reputación y documenta todo.
_Bot | Powered by Gemini AI_"""
    
    except Exception as e:
        print(f"Error creando mensaje: {e}")
        return f"✨ {member.mention} ha sido añadido al canal"

def create_removed_message(member):
    """Crea mensaje de remoción seguro"""
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
        
        return f"👋 **Usuario Removido:** {member.mention}"
    except:
        return "👋 Usuario removido del canal"

@client.event
async def on_ready():
    """Evento cuando el bot está listo"""
    try:
        print(f'✅ Selfbot conectado como {client.user}')
        print(f'   ID: {client.user.id}')
        print(f'   discord.py-self: v{discord.__version__}')
        print('------')
        print(f'🔐 Roles autorizados: {len(AUTHORIZED_ROLES)}')
        print(f'🤖 IA Gemini: {"✅" if gemma_client else "❌"}')
        print(f'🎨 Embeds: {"✅" if EMBEDS_DISPONIBLES else "❌"}')
        print('📡 Bot listo\n')
    except Exception as e:
        print(f"Error en on_ready: {e}")

@client.event
async def on_message(message):
    """Procesa mensajes y comandos"""
    try:
        # Ignorar bots
        if message.author.bot:
            return
        
        # Solo comandos .
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
            await message.channel.send("❌ Sin permisos.")
            return
        
        # Comandos
        content = message.content.lower().strip()
        
        if content.startswith('.add'):
            await handle_add(message)
        elif content.startswith('.quit'):
            await handle_quit(message)
        elif content.startswith('.help'):
            await handle_help(message)
    
    except Exception as e:
        print(f"Error en on_message: {e}")

async def handle_add(message):
    """Añade usuario al canal"""
    try:
        parts = message.content.split()
        
        if len(parts) < 2:
            await message.channel.send("❌ Uso: `.add @usuario` | `.add nombre` | `.add ID`")
            return

        member = None
        query = parts[1]
        
        # Mención directa
        if message.mentions and len(message.mentions) > 0:
            member = message.mentions[0]
        
        # ID numérico
        elif query.replace('<@', '').replace('>', '').replace('!', '').isdigit():
            try:
                user_id = int(query.replace('<@', '').replace('>', '').replace('!', ''))
                member = await message.guild.fetch_member(user_id)
            except:
                pass
        
        # Buscar por nombre
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
        
        print(f"✅ {member.name} añadido")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)[:100]}")
        print(f"Error en add: {e}")

async def handle_quit(message):
    """Remueve usuario del canal"""
    try:
        parts = message.content.split()
        
        if len(parts) < 2:
            await message.channel.send("❌ Uso: `.quit @usuario` | `.quit nombre` | `.quit ID`")
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

        # Enviar confirmación
        msg_content = create_removed_message(member)
        await message.channel.send(msg_content)

        print(f"✅ {member.name} removido")

    except Exception as e:
        await message.channel.send(f"❌ Error: {str(e)[:100]}")
        print(f"Error en quit: {e}")

async def handle_help(message):
    """Muestra ayuda"""
    try:
        if EMBEDS_DISPONIBLES:
            try:
                embed = discord_self_embed.Embed(
                    title="📚 Comandos",
                    description=".add usuario | .quit usuario | .help\nSolo roles autorizados",
                    colour="3498DB"
                )
                
                await message.channel.send(embed.generate_url(hide_url=True))
                return
            except:
                pass
        
        texto = """📚 **Comandos del Bot**

**.add** - Añade usuario
`.add @user` | `.add nombre` | `.add ID`

**.quit** - Remueve usuario
(mismos métodos)

**.help** - Muestra ayuda

🔐 Solo roles autorizados
_Powered by Gemini AI_"""
        
        await message.channel.send(texto)
    
    except Exception as e:
        print(f"Error en help: {e}")
        await message.channel.send("📚 Comandos: .add | .quit | .help")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: DISCORD_TOKEN no encontrado en .env")
        exit(1)
    
    print("🚀 Iniciando selfbot...")
    print(f"🔐 {len(AUTHORIZED_ROLES)} roles autorizados\n")
    
    try:
        client.run(token)
    except KeyboardInterrupt:
        print("\n⚠️ Bot detenido por usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
