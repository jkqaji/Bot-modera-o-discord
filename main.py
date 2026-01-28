import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '.'

# Bot com intents mínimos
intents = discord.Intents.default()
intents.message_content = True  # Apenas para ler mensagens

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# Eventos
@bot.event
async def on_ready():
    print(f'✅ Bot online: {bot.user.name}')
    print(f'🎯 Prefixo: {PREFIX}')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{PREFIX}ajuda"
    ))

# COMANDOS BÁSICOS (SEMPRE FUNCIONAM)
@bot.command(name="ping")
async def ping_cmd(ctx):
    """Testa o bot"""
    await ctx.send('🏓 Pong!')

@bot.command(name="ajuda")
async def ajuda_cmd(ctx):
    """Mostra ajuda"""
    embed = discord.Embed(
        title="📚 Ajuda",
        description=f"Prefixo: `{PREFIX}`",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📋 Comandos Básicos",
        value=(
            f"`{PREFIX}ping` - Testa o bot\n"
            f"`{PREFIX}userinfo` - Suas informações\n"
            f"`{PREFIX}avatar` - Seu avatar\n"
            f"`{PREFIX}serverinfo` - Info do servidor\n"
            f"`{PREFIX}say [texto]` - Repete texto\n"
            f"`{PREFIX}ajuda` - Esta mensagem"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="userinfo")
async def userinfo_cmd(ctx, member: discord.Member = None):
    """Informações do usuário"""
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f"👤 {member.name}",
        color=member.color if member.color.value != 0 else 0x5865F2
    )
    
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Conta criada", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    
    if member.joined_at:
        embed.add_field(name="Entrou aqui", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    
    embed.add_field(name="Bot", value="✅" if member.bot else "❌", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="avatar")
async def avatar_cmd(ctx, member: discord.Member = None):
    """Mostra avatar"""
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f"🖼️ Avatar de {member.name}",
        color=0x5865F2
    )
    
    if member.avatar:
        embed.set_image(url=member.avatar.url)
        embed.description = f"[Link]({member.avatar.url})"
    else:
        embed.set_image(url=member.default_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name="serverinfo")
async def serverinfo_cmd(ctx):
    """Informações do servidor"""
    guild = ctx.guild
    
    embed = discord.Embed(
        title=f"🏰 {guild.name}",
        color=0x9b59b6
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="👑 Dono", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    
    text = len(guild.text_channels)
    voice = len(guild.voice_channels)
    embed.add_field(name="📁 Canais", value=f"Texto: {text}\nVoz: {voice}", inline=True)
    
    embed.add_field(name="😀 Emojis", value=len(guild.emojis), inline=True)
    embed.add_field(name="🎭 Cargos", value=len(guild.roles), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="say")
async def say_cmd(ctx, *, texto):
    """Faz o bot falar"""
    await ctx.send(texto)

# Sistema de moderação SIMPLES
@bot.command(name="limpar")
@commands.has_permissions(manage_messages=True)
async def limpar_cmd(ctx, quantidade: int = 10):
    """Limpa mensagens (apenas moderadores)"""
    if quantidade < 1 or quantidade > 100:
        await ctx.send("❌ Use entre 1 e 100")
        return
    
    deletadas = await ctx.channel.purge(limit=quantidade + 1)
    msg = await ctx.send(f"🗑️ {len(deletadas)-1} mensagens limpas!")
    await msg.delete(delay=3)

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, motivo="Não especificado"):
    """Expulsa um usuário"""
    try:
        await member.kick(reason=motivo)
        await ctx.send(f"👢 {member.mention} foi expulso. Motivo: {motivo}")
    except:
        await ctx.send("❌ Não tenho permissão")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, motivo="Não especificado"):
    """Bane um usuário"""
    try:
        await member.ban(reason=motivo)
        await ctx.send(f"🔨 {member.mention} foi banido. Motivo: {motivo}")
    except:
        await ctx.send("❌ Não tenho permissão")

# Comandos divertidos
@bot.command(name="dado")
async def dado_cmd(ctx, lados: int = 6):
    """Rola um dado"""
    if lados < 2:
        lados = 6
    
    resultado = __import__('random').randint(1, lados)
    await ctx.send(f"🎲 {ctx.author.mention} rolou um D{lados}: **{resultado}**")

@bot.command(name="moeda")
async def moeda_cmd(ctx):
    """Cara ou coroa"""
    resultado = __import__('random').choice(["cara", "coroa"])
    await ctx.send(f"🪙 {ctx.author.mention} deu: **{resultado}**")

@bot.command(name="sorte")
async def sorte_cmd(ctx, *, pergunta):
    """Responde sim/não"""
    respostas = ["Sim", "Não", "Talvez", "Claro que sim!", "Nunca", "Com certeza"]
    resposta = __import__('random').choice(respostas)
    await ctx.send(f"🎱 {ctx.author.mention} perguntou: '{pergunta}'\nResposta: **{resposta}**")

# Tratamento de erros
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão")
    else:
        await ctx.send(f"⚠️ Erro: {str(error)[:100]}")

# INICIAR
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Token não encontrado! Crie um arquivo .env")
        print("Conteúdo do .env:")
        print("DISCORD_TOKEN=MTQ2NTgwMTc2MzQwMjU1MTMwNg.GV5NQr.cQZezuj8GEAFTWQQBtOVstxKSelgA8n01ZrcuQ")
    else:
        print("🚀 Iniciando bot...")
        bot.run(TOKEN)
