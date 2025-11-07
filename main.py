# Cat's Discord Bot - Versión Definitiva v4.1
import discord
import os
from dotenv import load_dotenv

print("\n🚀 Iniciando bot...\n")

load_dotenv()

client = discord.Client(chunk_guilds_at_startup=False, intents=discord.Intents.all())

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
    # Ignorar bots
    if message.author.bot:
        return
    
    # Solo $ commands
    if not message.content.startswith('$'):
        return
    
    # Solo en servidores
    if not message.guild:
        return
    
    try:
        # Obtener miembro
        member = message.guild.get_member(message.author.id)
        if not member:
            print(f"❌ No se encontró miembro para {message.author}")
            return
        
        # ✅ DEBUG: Mostrar roles del usuario
        user_roles = [r.id for r in member.roles]
        print(f"👤 {message.author} - Roles: {user_roles}")
        print(f"   Comando: {message.content}")
        
        # Verificar si tiene ALGUNO de los roles autorizados
        tiene_rol = any(role_id in user_roles for role_id in AUTHORIZED_ROLES)
        
        if not tiene_rol:
            print(f"❌ {message.author} no tiene permisos")
            await message.channel.send("❌ No tienes permisos para usar este bot")
            return
        
        print(f"✅ {message.author} AUTORIZADO")
        
        cmd = message.content.lower().split()[0]
        
        # COMANDO: $add
        if cmd == '$add':
            parts = message.content.split(maxsplit=1)
            
            if len(parts) < 2:
                await message.channel.send("❌ Uso: `$add @usuario`")
                return
            
            target = None
            query = parts[1].strip()
            
            # Mención
            if message.mentions:
                target = message.mentions[0]
                print(f"   Método: Mención")
            # ID
            elif query.isdigit():
                try:
                    target = await message.guild.fetch_member(int(query))
                    print(f"   Método: ID")
                except Exception as e:
                    print(f"   ID error: {e}")
            # Nombre o @nombre
            else:
                query_clean = query.replace('@', '').lower().strip()
                
                # Búsqueda exacta
                for m in message.guild.members:
                    if m.name.lower() == query_clean or m.display_name.lower() == query_clean:
                        target = m
                        print(f"   Método: Nombre exacto")
                        break
                
                # Búsqueda parcial
                if not target:
                    for m in message.guild.members:
                        if query_clean in m.name.lower() or query_clean in m.display_name.lower():
                            target = m
                            print(f"   Método: Nombre parcial")
                            break
            
            if not target:
                await message.channel.send(f"❌ Usuario `{query}` no encontrado")
                print(f"   ❌ Usuario no encontrado")
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
                
                # Respuesta
                await message.channel.send(f"✅ {target.mention} fue añadido al canal")
                print(f"✅ {target.name} añadido\n")
            
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")
                print(f"❌ Error: {e}\n")
        
        # COMANDO: $quit
        elif cmd == '$quit':
            parts = message.content.split(maxsplit=1)
            
            if len(parts) < 2:
                await message.channel.send("❌ Uso: `$quit @usuario`")
                return
            
            target = None
            query = parts[1].strip()
            
            if message.mentions:
                target = message.mentions[0]
            elif query.isdigit():
                try:
                    target = await message.guild.fetch_member(int(query))
                except:
                    pass
            else:
                query_clean = query.replace('@', '').lower().strip()
                for m in message.guild.members:
                    if m.name.lower() == query_clean or m.display_name.lower() == query_clean:
                        target = m
                        break
            
            if not target:
                await message.channel.send(f"❌ Usuario no encontrado")
                return
            
            try:
                ov = discord.PermissionOverwrite()
                ov.view_channel = False
                ov.send_messages = False
                
                await message.channel.set_permissions(target, overwrite=ov)
                
                await message.channel.send(f"✅ {target.mention} fue removido del canal")
                print(f"✅ {target.name} removido\n")
            
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")
                print(f"❌ Error: {e}\n")
        
        # COMANDO: $help
        elif cmd == '$help':
            await message.channel.send("""📚 **Comandos**
`$add @usuario` - Añade al canal
`$quit @usuario` - Remueve del canal""")
        
        else:
            await message.channel.send(f"❌ Comando desconocido: `{cmd}`")
    
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ DISCORD_TOKEN falta")
        exit(1)
    
    try:
        client.run(token)
    except Exception as e:
        print(f"❌ {e}")
