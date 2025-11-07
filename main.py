# Cat's Discord Bot - Versión Simple v4.0
import discord
import os
from dotenv import load_dotenv

print("\n🚀 Iniciando bot...\n")

load_dotenv()

client = discord.Client(chunk_guilds_at_startup=False)

# 🔐 4 ROLES AUTORIZADOS
AUTHORIZED_ROLES = [
    1427705211186839672,
    1330597790660694047,
    1329516197175103651,
    1330356239103688835
]

@client.event
async def on_ready():
    print(f'✅ {client.user}')
    print(f'🔐 {len(AUTHORIZED_ROLES)} roles')
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
        
        # Verificar roles
        member_roles = [r.id for r in member.roles]
        tiene_rol = any(r in AUTHORIZED_ROLES for r in member_roles)
        
        if not tiene_rol:
            await message.channel.send("❌ Sin permisos")
            return
        
        cmd = message.content.lower().split()[0]
        
        # COMANDO: $add
        if cmd == '$add':
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("❌ Uso: `$add @usuario` o `$add ID`")
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
                
                # Mensaje simple
                await message.channel.send(f"✅ {target.mention} fue añadido al canal")
                print(f"✅ {target.name} añadido")
            
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")
                print(f"Error: {e}")
        
        # COMANDO: $quit
        elif cmd == '$quit':
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("❌ Uso: `$quit @usuario` o `$quit ID`")
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
                
                await message.channel.send(f"✅ {target.mention} fue removido del canal")
                print(f"✅ {target.name} removido")
            
            except Exception as e:
                await message.channel.send(f"❌ Error: {e}")
                print(f"Error: {e}")
        
        # COMANDO: $help
        elif cmd == '$help':
            msg = """📚 **Comandos**

`$add @usuario` - Añade al canal
`$quit @usuario` - Remueve del canal

🔐 Solo 4 roles autorizados"""
            
            await message.channel.send(msg)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ DISCORD_TOKEN falta en .env")
        exit(1)
    
    try:
        client.run(token)
    except Exception as e:
        print(f"❌ {e}")
