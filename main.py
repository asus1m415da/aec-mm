import discord
from discord.ext import commands
import os
import re
from dotenv import load_dotenv
from groq import Groq
import asyncio

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="$", help_command=None, intents=intents)

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

@bot.event
async def on_ready():
    print(f"🌌 Galaxy Bot listo como {bot.user}")

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

# Manejo de error cuando alguien sin el rol intenta usar el comando
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
        description="Bot para gestionar permisos de canales con frases chistosas.\n\n**$add** — Añade usuario al canal (Solo MIDDLEMAN).\n**$joke** — Frase chistosa random.\n**$comandos** — Muestra este mensaje.\n",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Galaxy Bot | Powered by openai/gpt-oss-120b")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
