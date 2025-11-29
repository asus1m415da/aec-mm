import discord
from discord.ext import commands
import os
import re
from dotenv import load_dotenv
from groq import Groq
import asyncio
import aiohttp

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="$", help_command=None, intents=intents)

# ===== CONFIGURACIÓN DE VIGILANCIA =====
MONITORED_CHANNELS = {}  # {channel_id: webhook_url}
MARKDOWN_PATTERNS = {
    r'\*\*(.*?)\*\*': r'\1',  # **bold** → bold
    r'\*(.*?)\*': r'\1',      # *italic* → italic
    r'__(.*?)__': r'\1',      # __underline__ → underline
    r'_(.*?)_': r'\1',        # _italic_ → italic
    r'~~(.*?)~~': r'\1',      # ~~strikethrough~~ → strikethrough
    r'`(.*?)`': r'\1',        # `code` → code
    r'```[\w]*\n(.*?)\n```': r'\1',  # ```code block``` → code block
}

def strip_markdown(text):
    """Elimina todo markdown de un texto y lo deja plano"""
    cleaned = text
    for pattern, replacement in MARKDOWN_PATTERNS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.DOTALL)
    
    # Eliminar caracteres especiales Discord
    cleaned = re.sub(r'<@!?(\d+)>', r'@usuario', cleaned)
    cleaned = re.sub(r'<#(\d+)>', r'#canal', cleaned)
    cleaned = re.sub(r'<@&(\d+)>', r'@rol', cleaned)
    
    return cleaned.strip()

def get_random_joke():
    """Genera una frase chistosa usando Groq con openai/gpt-oss-120b"""
    try:
        client = Groq()
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "tu dices frases chistosas ramdoms de cualquier cosa, que hagan reir y que no esten quemadas, solo di la frase directa y nada mas"
                },
                {
                    "role": "user",
                    "content": ""
                }
            ],
            temperature=2,
            max_completion_tokens=1536,
            top_p=1,
            reasoning_effort="high",
            stream=True,
            stop=None,
            tools=[{"type": "browser_search"}]
        )
        
        joke = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                joke += chunk.choices[0].delta.content
        
        return joke.strip()
    except Exception as e:
        print(f"⚠️ Error Groq: {e}")
        return "¡Ups! Mi cerebro de IA necesita un café ☕"

def parse_user_input(arg):
    if re.match(r'^\d{15,20}$', arg):
        return int(arg), "id"
    if arg.startswith("<@"):
        match = re.search(r'<@!?(\d+)>', arg)
        if match:
            return int(match.group(1)), "mention"
    if re.match(r'^[a-zA-Z0-9_]{2,32}$', arg):
        return arg, "username"
    return None, None

async def create_webhook_for_channel(channel):
    """Crea un webhook en el canal y retorna su URL"""
    try:
        webhook = await channel.create_webhook(name="Galaxy Monitor")
        return str(webhook.url)
    except discord.Forbidden:
        print(f"❌ No tengo permisos para crear webhook en {channel.name}")
        return None
    except Exception as e:
        print(f"❌ Error creando webhook: {e}")
        return None

async def send_webhook_message(webhook_url, author_name, content, avatar_url):
    """Envía un mensaje a través de webhook con avatar del usuario"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "content": content,
                "username": author_name,
                "avatar_url": avatar_url
            }
            async with session.post(webhook_url, json=payload) as response:
                return response.status == 204
    except Exception as e:
        print(f"❌ Error enviando webhook: {e}")
        return False

@bot.event
async def on_ready():
    print(f"🌌 Galaxy Bot listo como {bot.user}")

@bot.event
async def on_message(message):
    """Detecta markdown en canales monitoreados y lo convierte"""
    # Verificar si el canal está monitoreado
    if message.channel.id not in MONITORED_CHANNELS:
        await bot.process_commands(message)
        return
    
    webhook_url = MONITORED_CHANNELS[message.channel.id]
    
    # Detectar si el mensaje tiene markdown
    has_markdown = any(pattern in message.content for pattern in [
        '**', '__', '~~', '`', '```'
    ])
    
    if has_markdown:
        # Limpiar markdown
        clean_content = strip_markdown(message.content)
        
        # Enviar a través de webhook
        success = await send_webhook_message(
            webhook_url,
            message.author.name,
            clean_content
        )
        
        if success:
            # Borrar el mensaje original
            try:
                await message.delete()
                print(f"✓ Mensaje de {message.author.name} procesado (markdown removido)")
            except discord.Forbidden:
                print(f"⚠️ No pude borrar el mensaje de {message.author.name}")
    
    await bot.process_commands(message)

@bot.command(name="monitorear")
@commands.has_permissions(administrator=True)
async def monitor_command(ctx, category_id: int = None):
    """Monitorea todos los canales de una categoría"""
    if category_id is None:
        embed = discord.Embed(
            title="❌ Uso Incorrecto",
            description="Debes especificar el ID de la categoría",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Ejemplo:",
            value="`$monitorear 1389689571146469510`",
            inline=False
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
        return
    
    try:
        category = bot.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            embed = discord.Embed(
                title="❌ Error",
                description="Ese ID no es una categoría válida",
                color=discord.Color.red()
            )
            embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
            await ctx.send(embed=embed)
            return
        
        channels_monitored = 0
        channels_failed = 0
        
        embed_progress = discord.Embed(
            title="⏳ Configurando monitoreo...",
            description=f"Procesando canales de: **{category.name}**",
            color=discord.Color.yellow()
        )
        progress_msg = await ctx.send(embed=embed_progress)
        
        for channel in category.text_channels:
            if isinstance(channel, discord.TextChannel):
                webhook_url = await create_webhook_for_channel(channel)
                if webhook_url:
                    MONITORED_CHANNELS[channel.id] = webhook_url
                    channels_monitored += 1
                else:
                    channels_failed += 1
        
        embed_success = discord.Embed(
            title="✓ Monitoreo Configurado",
            description=f"Vigilando la categoría: **{category.name}**",
            color=discord.Color.green()
        )
        embed_success.add_field(
            name="📊 Estadísticas",
            value=f"✓ Canales monitoreados: **{channels_monitored}**\n❌ Canales fallidos: **{channels_failed}**",
            inline=False
        )
        embed_success.add_field(
            name="⚙️ Función",
            value="Detectaré automáticamente markdown en estos canales y lo convertiré a texto plano mediante webhooks",
            inline=False
        )
        embed_success.set_footer(text="Galaxy Bot | Powered by Groq AI")
        
        await progress_msg.edit(embed=embed_success)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"```{str(e)}```",
            color=discord.Color.red()
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)

@bot.command(name="dejar_monitorear")
@commands.has_permissions(administrator=True)
async def unmonitor_command(ctx, category_id: int = None):
    """Deja de monitorear una categoría"""
    if category_id is None:
        embed = discord.Embed(
            title="❌ Uso Incorrecto",
            description="Debes especificar el ID de la categoría",
            color=discord.Color.red()
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
        return
    
    try:
        category = bot.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            embed = discord.Embed(
                title="❌ Error",
                description="Ese ID no es una categoría válida",
                color=discord.Color.red()
            )
            embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
            await ctx.send(embed=embed)
            return
        
        channels_removed = 0
        webhooks_deleted = 0
        
        try:
            all_webhooks = await ctx.guild.webhooks()
            for webhook in all_webhooks:
                if webhook.name == "Galaxy Monitor":
                    try:
                        await webhook.delete()
                        webhooks_deleted += 1
                        print(f"✓ Webhook '{webhook.name}' en {webhook.channel} eliminado")
                    except Exception as e:
                        print(f"⚠️ Error borrando webhook: {e}")
        except Exception as e:
            print(f"⚠️ Error obteniendo webhooks: {e}")
        
        for channel in category.text_channels:
            if channel.id in MONITORED_CHANNELS:
                del MONITORED_CHANNELS[channel.id]
                channels_removed += 1
        
        embed = discord.Embed(
            title="✓ Monitoreo Detenido",
            description=f"Dejé de vigilar **{channels_removed}** canales de: **{category.name}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🗑️ Webhooks Eliminados",
            value=f"**{webhooks_deleted}** webhooks 'Galaxy Monitor' fueron borrados del servidor",
            inline=False
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"```{str(e)}```",
            color=discord.Color.red()
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)

@bot.command(name="add")
@commands.has_any_role("MIDDLEMAN", 1427705211186839672)
async def add_user(ctx, *, arg=None):
    if not arg:
        embed = discord.Embed(
            title="❌ Uso Incorrecto",
            description="Debes especificar un usuario",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Formatos válidos:",
            value="`$add @usuario`\n`$add usuario`\n`$add 123456789`",
            inline=False
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
        return
    arg = arg.strip()
    user_data, user_type = parse_user_input(arg)
    if not user_data:
        embed = discord.Embed(
            title="❌ Formato Inválido",
            description="No pude reconocer el usuario",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Intenta con:",
            value="`@usuario` | `usuario` | `ID`",
            inline=False
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
        return
    try:
        if user_type == "id":
            user = await bot.fetch_user(user_data)
        elif user_type == "mention":
            user = await bot.fetch_user(user_data)
        elif user_type == "username":
            user = discord.utils.find(
                lambda m: m.name == user_data,
                ctx.guild.members
            )
            if not user:
                embed = discord.Embed(
                    title="❌ Usuario No Encontrado",
                    description=f"No existe el usuario `{user_data}` en este servidor",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
                await ctx.send(embed=embed)
                return
        
        # Permisos completos
        await ctx.channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            add_reactions=True,
            external_emojis=True,
            mention_everyone=False,
            manage_messages=False
        )
        
        embed_confirm = discord.Embed(
            title="✓ Usuario Añadido",
            description=f"{user.mention} ahora tiene acceso a {ctx.channel.mention}",
            color=discord.Color.green()
        )
        embed_confirm.add_field(
            name="Permisos Otorgados:",
            value="✓ Ver canal\n✓ Enviar mensajes\n✓ Ver historial\n✓ Enviar archivos\n✓ Enviar links\n✓ Reacciones",
            inline=False
        )
        embed_confirm.set_thumbnail(url=user.display_avatar.url)
        embed_confirm.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed_confirm)
        
        typing = await ctx.send(
            embed=discord.Embed(
                description="⏳ Generando frase chistosa...",
                color=discord.Color.yellow()
            )
        )
        joke = await asyncio.to_thread(get_random_joke)
        await typing.delete()
        
        embed_joke = discord.Embed(
            title="😂 Frase del Momento",
            description=f">>> {joke}",
            color=discord.Color.random()
        )
        embed_joke.set_footer(text="Galaxy Bot | openai/gpt-oss-120b | Browser Search ✓")
        await ctx.send(embed=embed_joke)
    except discord.NotFound:
        embed = discord.Embed(
            title="❌ Usuario No Encontrado",
            description="El usuario no existe en Discord",
            color=discord.Color.red()
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Permisos Insuficientes",
            description="No tengo permisos para modificar este canal",
            color=discord.Color.red()
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"``````",
            color=discord.Color.red()
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)

@add_user.error
async def add_user_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        embed = discord.Embed(
            title="🔒 Acceso Denegado",
            description="No tienes permisos para usar este comando",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Rol Requerido:",
            value="**MIDDLEMAN**",
            inline=False
        )
        embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
        await ctx.send(embed=embed)

@bot.command(name="comandos")
async def comandos_command(ctx):
    embed = discord.Embed(
        title="📚 Comandos Galaxy Bot",
        description="Bot para gestionar permisos de canales con frases chistosas.\n\n" +
                    "**$add** — Añade usuario al canal (Solo MIDDLEMAN).\n" +
                    "**$monitorear** — Vigila canales de una categoría.\n" +
                    "**$dejar_monitorear** — Deja de vigilar una categoría.\n" +
                    "**$status** — Muestra canales monitoreados.\n" +
                    "**$comandos** — Muestra este mensaje.\n",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Galaxy Bot | Powered by openai/gpt-oss-120b")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="status")
@commands.has_permissions(administrator=True)
async def status_command(ctx):
    """Muestra el estado de monitoreo actual"""
    if not MONITORED_CHANNELS:
        embed = discord.Embed(
            title="📊 Estado de Monitoreo",
            description="No hay canales siendo monitoreados actualmente",
            color=discord.Color.yellow()
        )
    else:
        channels_info = ""
        for channel_id in MONITORED_CHANNELS:
            channel = bot.get_channel(channel_id)
            if channel:
                channels_info += f"• {channel.mention}\n"
        
        embed = discord.Embed(
            title="📊 Estado de Monitoreo",
            description=f"Vigilando **{len(MONITORED_CHANNELS)}** canales:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Canales Activos",
            value=channels_info or "Sin canales",
            inline=False
        )
    
    embed.set_footer(text="Galaxy Bot | Powered by Groq AI")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
