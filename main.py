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

if not TOKEN or not GROQ_API_KEY:
    print("❌ ERROR: Falta DISCORD_TOKEN o GROQ_API_KEY en .env")
    exit(1)

bot = commands.Bot(command_prefix="$", self_bot=True)

def get_random_joke():
    """Genera una frase chistosa usando Groq con openai/gpt-oss-120b"""
    try:
        client = Groq()
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "tu eres Galaxy Bot, tu dices frases chistosas ramdoms, solo dices directo la frase porfavor"
                },
                {
                    "role": "user",
                    "content": ""
                }
            ],
            temperature=2,
            max_completion_tokens=65536,
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
    """Parsea el input para extraer ID, mention o username"""
    
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
    print(f"╔════════════════════════════════════╗")
    print(f"║  🌌 Galaxy Bot Conectado 🌌      ║")
    print(f"║  Usuario: {bot.user}              ║")
    print(f"║  Modelo: openai/gpt-oss-120b     ║")
    print(f"╚════════════════════════════════════╝")

@bot.command(name="add")
async def add_user(ctx, *, arg=None):
    """Añade un usuario al canal con una frase chistosa 🎉"""
    
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
        await ctx.send(embed=embed)
        return
    
    arg = arg.strip()
    user_data, user_type = parse_user_input(arg)
    
    if not user_data:
        await ctx.send("❌ Formato inválido. Intenta: `@usuario`, `usuario` o `ID`")
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
                await ctx.send(f"❌ Usuario `{user_data}` no encontrado")
                return
        
        # Añadir usuario al canal
        await ctx.channel.set_permissions(
            user,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
        
        # 1️⃣ Enviar confirmación
        embed_confirm = discord.Embed(
            title="✓ Usuario Añadido",
            description=f"{user.mention} ahora tiene acceso a {ctx.channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed_confirm)
        
        # 2️⃣ Generar y enviar frase
        typing = await ctx.send("⏳ Generando frase chistosa...")
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
        await ctx.send("❌ Usuario no encontrado en Discord")
    except discord.Forbidden:
        await ctx.send("❌ No tengo permisos para modificar este canal")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name="joke")
async def joke_command(ctx):
    """Obtiene una frase chistosa random 🎭"""
    typing = await ctx.send("⏳ Pensando con GPT-OSS...")
    joke = await asyncio.to_thread(get_random_joke)
    await typing.delete()
    
    embed = discord.Embed(
        title="😂 Frase Chistosa",
        description=f">>> {joke}",
        color=discord.Color.random()
    )
    embed.set_footer(text="Galaxy Bot | openai/gpt-oss-120b")
    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx):
    """Muestra los comandos disponibles"""
    embed = discord.Embed(
        title="📚 Comandos Galaxy Bot",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="$add",
        value="Añade usuario + muestra frase\nEjemplos: `$add @user` | `$add user` | `$add 123456789`",
        inline=False
    )
    embed.add_field(
        name="$joke",
        value="Genera una frase chistosa random",
        inline=False
    )
    embed.set_footer(text="Galaxy Bot | Powered by openai/gpt-oss-120b")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
