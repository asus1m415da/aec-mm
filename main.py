# Cat's Discord Bot - Versión Final v3.1
import discord
import os
from dotenv import load_dotenv
import random

print("\n🔍 Cargando...\n")

load_dotenv()

client = discord.Client(chunk_guilds_at_startup=False)

# 🔐 LOS 4 ROLES AUTORIZADOS (ACTUALIZADO)
AUTHORIZED_ROLES = [
    1427705211186839672,
    1330597790660694047,
    1329516197175103651,
    1330356239103688835
]

# IA
try:
    import google.generativeai as genai
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        genai.configure(api_key=api_key)
        GEMINI_OK = True
    else:
        GEMINI_OK = False
except:
    GEMINI_OK = False

consejos_history = {"trader": [], "middleman": []}

def get_advice(user_type):
    """Consejo rápido"""
    consejos = {
        "trader": [
            "Verifica reputación en múltiples servidores",
            "Nunca compartas .HAR files",
            "Graba video del trade completo",
            "Usa middlemen con +100 trades",
            "Pide referencias antes",
            "Confirma identidad oficial",
            "Revisa roles verificados",
            "Mantén conversaciones en Discord",
            "Screenshots de cada paso",
            "Evita tarifas excesivas",
            "Activa 2FA antes de tradear",
            "Confía en tu instinto"
        ],
        "middleman": [
            "Registro público transparente",
            "Nunca pidas contraseñas",
            "Responde en -5 minutos",
            "Publica testimonios",
            "Sistema de tickets",
            "Explica cada paso",
            "Guarda evidencias 30+ días",
            "Comunicación constante",
            "Políticas claras escritas",
            "Actualiza estadísticas",
            "Rechaza trades sospechosos",
            "Sé imparcial siempre"
        ]
    }
    
    usados = consejos_history[user_type][-2:] if consejos_history[user_type] else []
    disponibles = [c for c in consejos[user_type] if c not in usados]
    
    if not disponibles:
        disponibles = consejos[user_type]
    
    consejo = random.choice(disponibles)
    consejos_history[user_type].append(consejo)
    if len(consejos_history[user_type]) > 4:
        consejos_history[user_type].pop(0)
    
    return consejo

@client.event
async def on_ready():
    print(f'✅ {client.user}')
    print(f'🔐 {len(AUTHORIZED_ROLES)} roles')
    print(f'💲 Prefijo: $')
    print(f'🤖 IA: {"✅" if GEMINI_OK else "❌"}')
    print('📡 Listo\n')

@client.event
async def on_message(message):
    try:
        # Ignorar bots
        if message.author.bot:
            return
        
        # Solo $ commands
        if not message.content.startswith('$'):
            return
        
        # Solo en servidores
        if not message.guild:
            return
        
        # Obtener miembro
        member = message.guild.get_member(message.author.id)
        if not member:
            return
        
        # ✅ VERIFICAR ROLES - NUEVA LÓGICA
        member_roles = [r.id for r in member.roles]
        tiene_rol = any(r in AUTHORIZED_ROLES for r in member_roles)
        
        if not tiene_rol:
            print(f"❌ {message.author} NO tiene rol autorizado. Roles: {member_roles}")
            await message.channel.send("❌ Sin permisos")
            return
        
        print(f"✅ {message.author} tiene rol autorizado")
        
        cmd = message.content.lower().split()[0]
        
        # COMANDO: $add
        if cmd == '$add':
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("❌ Uso: `$add @usuario`")
                return
            
            target = None
            
            # Mención
            if message.mentions:
                target = message.mentions[0]
            # ID
            elif parts[1].isdigit():
                try:
                    target = await message.guild.fetch_member(int(parts[1]))
                except:
                    pass
            # Nombre
            else:
                query = parts[1].lower()
                for m in message.guild.members:
                    if query in (m.name.lower(), m.display_name.lower()):
                        target = m
                        break
            
            if not target:
                await message.channel.send("❌ Usuario no encontrado")
                return
            
            if target.bot:
                await message.channel.send("❌ No puedo añadir bots")
                return
            
            try:
                # Permisos
                ov = discord.PermissionOverwrite()
                ov.view_channel = True
                ov.send_messages = True
                ov.read_message_history = True
                await message.channel.set_permissions(target, overwrite=ov)
                
                # Consejos
                c1 = get_advice("trader")
                c2 = get_advice("middleman")
                
                # Mensaje
                msg = f"""✨ **Bienvenido** ✨

{target.mention} añadido al canal

📊 **Traders:** {c1}

🤝 **Middlemans:** {c2}

💎 Verifica reputación siempre
_Bot | Gemini AI_"""
                
                await message.channel.send(msg)
                print(f"✅ {target.name} añadido por {message.author}")
            
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")
                print(f"Error add: {e}")
        
        # COMANDO: $quit
        elif cmd == '$quit':
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("❌ Uso: `$quit @usuario`")
                return
            
            target = None
            
            if message.mentions:
                target = message.mentions[0]
            elif parts[1].isdigit():
                try:
                    target = await message.guild.fetch_member(int(parts[1]))
                except:
                    pass
            else:
                query = parts[1].lower()
                for m in message.guild.members:
                    if query in (m.name.lower(), m.display_name.lower()):
                        target = m
                        break
            
            if not target:
                await message.channel.send("❌ Usuario no encontrado")
                return
            
            try:
                ov = discord.PermissionOverwrite()
                ov.view_channel = False
                ov.send_messages = False
                await message.channel.set_permissions(target, overwrite=ov)
                
                await message.channel.send(f"👋 **{target.mention}** removido")
                print(f"✅ {target.name} removido por {message.author}")
            
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")
                print(f"Error quit: {e}")
        
        # COMANDO: $help
        elif cmd == '$help':
            msg = """📚 **Comandos**

`$add @usuario` - Añade al canal
`$quit @usuario` - Remueve del canal
`$help` - Muestra esto

🔐 Solo 4 roles autorizados
_Powered by Gemini AI_"""
            
            await message.channel.send(msg)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ DISCORD_TOKEN falta en .env")
        exit(1)
    
    print("🚀 Iniciando...\n")
    
    try:
        client.run(token)
    except Exception as e:
        print(f"❌ {e}")
