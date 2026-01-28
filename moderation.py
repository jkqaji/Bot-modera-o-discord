import discord
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import random
import string
from config import Config

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def log_mod_action(self, action, user, moderator, reason, duration=None):
        """Log de ações de moderação"""
        log_channel = self.bot.get_channel(Config.MOD_LOG_CHANNEL)
        
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"🛡️ {action.upper()}",
            color=Config.COLORS['warning'],
            timestamp=datetime.now()
        )
        embed.add_field(name="Usuário", value=f"{user.mention}\n({user.id})", inline=True)
        embed.add_field(name="Moderador", value=moderator.mention, inline=True)
        if reason:
            embed.add_field(name="Motivo", value=reason, inline=False)
        if duration:
            embed.add_field(name="Duração", value=duration, inline=True)
        
        await log_channel.send(embed=embed)
    
    @commands.command(name="warn")
    @commands.has_role(Config.MOD_ROLE)
    async def warn(self, ctx, member: discord.Member, *, reason="Não especificado"):
        """Adverte um usuário"""
        case_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Salvar no banco
        await self.bot.db.add_mod_action(
            case_id, member.id, ctx.author.id, "warn", reason
        )
        
        # Embed para o usuário
        user_embed = discord.Embed(
            title="⚠️ Você foi advertido",
            description=f"Servidor: {ctx.guild.name}",
            color=Config.COLORS['warning']
        )
        user_embed.add_field(name="Motivo", value=reason)
        user_embed.add_field(name="Moderador", value=ctx.author.name)
        user_embed.set_footer(text=f"Case ID: {case_id}")
        
        try:
            await member.send(embed=user_embed)
        except:
            pass
        
        # Embed no canal
        embed = discord.Embed(
            description=f"✅ {member.mention} foi advertido.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
        
        # Log
        await self.log_mod_action("WARN", member, ctx.author, reason)
    
    @commands.command(name="mute")
    @commands.has_role(Config.MOD_ROLE)
    async def mute(self, ctx, member: discord.Member, duration: str = "1h", *, reason="Não especificado"):
        """Silencia um usuário por um tempo determinado"""
        # Converter duração para segundos
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1].lower()
        amount = int(duration[:-1])
        
        if unit not in time_units:
            await ctx.send("❌ Unidade de tempo inválida. Use s, m, h ou d.")
            return
        
        seconds = amount * time_units[unit]
        
        # Aplicar mute
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            # Criar role de mute se não existir
            mute_role = await ctx.guild.create_role(name="Muted", color=discord.Color.dark_gray())
            
            # Configurar permissões em todos os canais
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, add_reactions=False)
        
        await member.add_roles(mute_role)
        
        # Salvar no banco
        case_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        await self.bot.db.add_mod_action(
            case_id, member.id, ctx.author.id, "mute", reason, duration
        )
        
        # Embed para o usuário
        user_embed = discord.Embed(
            title="🔇 Você foi silenciado",
            description=f"Servidor: {ctx.guild.name}",
            color=Config.COLORS['warning']
        )
        user_embed.add_field(name="Motivo", value=reason)
        user_embed.add_field(name="Duração", value=duration)
        user_embed.add_field(name="Moderador", value=ctx.author.name)
        user_embed.set_footer(text=f"Case ID: {case_id}")
        
        try:
            await member.send(embed=user_embed)
        except:
            pass
        
        # Embed no canal
        embed = discord.Embed(
            description=f"🔇 {member.mention} foi silenciado por {duration}.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
        
        # Log
        await self.log_mod_action("MUTE", member, ctx.author, reason, duration)
        
        # Auto-remover mute
        await asyncio.sleep(seconds)
        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            
            # Embed de unmute automático
            auto_embed = discord.Embed(
                description=f"🔊 {member.mention} foi automaticamente desilenciado.",
                color=Config.COLORS['info']
            )
            await ctx.send(embed=auto_embed)
    
    @commands.command(name="unmute")
    @commands.has_role(Config.MOD_ROLE)
    async def unmute(self, ctx, member: discord.Member):
        """Remove o silenciamento de um usuário"""
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        
        if not mute_role or mute_role not in member.roles:
            await ctx.send("❌ Este usuário não está silenciado.")
            return
        
        await member.remove_roles(mute_role)
        
        embed = discord.Embed(
            description=f"🔊 {member.mention} foi desilenciado.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
        
        await self.log_mod_action("UNMUTE", member, ctx.author, "Remoção manual")
    
    @commands.command(name="kick")
    @commands.has_role(Config.MOD_ROLE)
    async def kick(self, ctx, member: discord.Member, *, reason="Não especificado"):
        """Expulsa um usuário do servidor"""
        case_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Embed para o usuário
        user_embed = discord.Embed(
            title="👢 Você foi expulso",
            description=f"Servidor: {ctx.guild.name}",
            color=Config.COLORS['error']
        )
        user_embed.add_field(name="Motivo", value=reason)
        user_embed.add_field(name="Moderador", value=ctx.author.name)
        user_embed.set_footer(text=f"Case ID: {case_id}")
        
        try:
            await member.send(embed=user_embed)
        except:
            pass
        
        await member.kick(reason=f"{ctx.author}: {reason}")
        
        # Salvar no banco
        await self.bot.db.add_mod_action(
            case_id, member.id, ctx.author.id, "kick", reason
        )
        
        embed = discord.Embed(
            description=f"👢 {member.mention} foi expulso.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
        
        await self.log_mod_action("KICK", member, ctx.author, reason)
    
    @commands.command(name="ban")
    @commands.has_role(Config.MOD_ROLE)
    async def ban(self, ctx, member: discord.Member, *, reason="Não especificado"):
        """Bane um usuário do servidor"""
        case_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # Embed para o usuário
        user_embed = discord.Embed(
            title="🔨 Você foi banido",
            description=f"Servidor: {ctx.guild.name}",
            color=Config.COLORS['error']
        )
        user_embed.add_field(name="Motivo", value=reason)
        user_embed.add_field(name="Moderador", value=ctx.author.name)
        user_embed.set_footer(text=f"Case ID: {case_id}")
        
        try:
            await member.send(embed=user_embed)
        except:
            pass
        
        await member.ban(reason=f"{ctx.author}: {reason}")
        
        # Salvar no banco
        await self.bot.db.add_mod_action(
            case_id, member.id, ctx.author.id, "ban", reason
        )
        
        embed = discord.Embed(
            description=f"🔨 {member.mention} foi banido.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
        
        await self.log_mod_action("BAN", member, ctx.author, reason)
    
    @commands.command(name="clear")
    @commands.has_role(Config.MOD_ROLE)
    async def clear(self, ctx, amount: int = 10):
        """Limpa mensagens do canal"""
        if amount > 100:
            await ctx.send("❌ Você só pode limpar até 100 mensagens de uma vez.")
            return
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        
        embed = discord.Embed(
            description=f"🗑️ {len(deleted) - 1} mensagens foram deletadas.",
            color=Config.COLORS['success']
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(3)
        await msg.delete()
    
    @commands.command(name="warnings")
    @commands.has_role(Config.MOD_ROLE)
    async def warnings(self, ctx, member: discord.Member):
        """Mostra as advertências de um usuário"""
        warnings = await self.bot.db.get_user_warnings(member.id)
        
        if not warnings:
            embed = discord.Embed(
                description=f"📋 {member.mention} não tem advertências.",
                color=Config.COLORS['info']
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"Advertências de {member.name}",
            color=Config.COLORS['warning']
        )
        
        for i, warn in enumerate(warnings, 1):
            moderator = await self.bot.fetch_user(warn['moderator_id'])
            embed.add_field(
                name=f"⚠️ Case {warn['case_id']}",
                value=f"**Motivo:** {warn['reason']}\n"
                      f"**Moderador:** {moderator.mention if moderator else 'Desconhecido'}\n"
                      f"**Data:** {discord.utils.format_dt(datetime.fromisoformat(warn['created_at']), 'R')}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="case")
    @commands.has_role(Config.MOD_ROLE)
    async def case_info(self, ctx, case_id: str):
        """Mostra informações de um caso específico"""
        with self.bot.db.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM moderation WHERE case_id = ?', (case_id,))
            case = cursor.fetchone()
        
        if not case:
            await ctx.send("❌ Caso não encontrado.")
            return
        
        user = await self.bot.fetch_user(case['user_id'])
        moderator = await self.bot.fetch_user(case['moderator_id'])
        
        embed = discord.Embed(
            title=f"🛡️ Caso {case_id}",
            color=Config.COLORS['info']
        )
        embed.add_field(name="Usuário", value=f"{user.mention}\n({user.id})")
        embed.add_field(name="Moderador", value=moderator.mention)
        embed.add_field(name="Ação", value=case['action'].upper())
        embed.add_field(name="Motivo", value=case['reason'] or "Não especificado")
        embed.add_field(name="Duração", value=case['duration'] or "N/A")
        embed.add_field(name="Data", value=discord.utils.format_dt(
            datetime.fromisoformat(case['created_at']), 'F'
        ))
        embed.add_field(name="Ativo", value="✅ Sim" if case['active'] else "❌ Não")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
