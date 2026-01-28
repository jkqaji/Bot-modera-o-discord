import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
from config import Config

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_tickets.start()
    
    def cog_unload(self):
        self.cleanup_tickets.cancel()
    
    @tasks.loop(hours=24)
    async def cleanup_tickets(self):
        """Limpa tickets antigos automaticamente"""
        with self.bot.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM tickets 
                WHERE status = 'closed' 
                AND closed_at < datetime('now', '-? days')
            ''', (Config.AUTO_CLOSE_DAYS,))
            old_tickets = cursor.fetchall()
        
        for ticket in old_tickets:
            try:
                channel = self.bot.get_channel(ticket['channel_id'])
                if channel:
                    await channel.delete(reason="Ticket antigo - limpeza automática")
            except:
                pass
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Mostra a latência do bot"""
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description=f"🏓 Pong! {latency}ms",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="status")
    @commands.has_role(Config.MOD_ROLE)
    async def status(self, ctx):
        """Mostra estatísticas do bot"""
        with self.bot.db.get_connection() as conn:
            # Tickets
            cursor = conn.execute('SELECT COUNT(*) FROM tickets')
            total_tickets = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM tickets WHERE status = "open"')
            open_tickets = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM tickets WHERE status = "closed"')
            closed_tickets = cursor.fetchone()[0]
            
            # Moderação
            cursor = conn.execute('SELECT COUNT(*) FROM moderation')
            total_cases = cursor.fetchone()[0]
        
        embed = discord.Embed(
            title="📊 Estatísticas do Bot",
            color=Config.COLORS['info'],
            timestamp=datetime.now()
        )
        embed.add_field(name="🎫 Tickets", 
                       value=f"Total: {total_tickets}\n"
                             f"Abertos: {open_tickets}\n"
                             f"Fechados: {closed_tickets}",
                       inline=True)
        
        embed.add_field(name="🛡️ Moderação",
                       value=f"Total de casos: {total_cases}",
                       inline=True)
        
        embed.add_field(name="🌐 Servidores",
                       value=f"{len(self.bot.guilds)} servidores",
                       inline=True)
        
        embed.set_footer(text=f"Bot: {self.bot.user.name}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="userinfo")
    @commands.has_role(Config.MOD_ROLE)
    async def userinfo(self, ctx, member: discord.Member = None):
        """Mostra informações de um usuário"""
        member = member or ctx.author
        
        with self.bot.db.get_connection() as conn:
            # Tickets do usuário
            cursor = conn.execute('''
                SELECT COUNT(*) FROM tickets WHERE user_id = ?
            ''', (member.id,))
            ticket_count = cursor.fetchone()[0]
            
            # Advertências
            cursor = conn.execute('''
                SELECT COUNT(*) FROM moderation 
                WHERE user_id = ? AND action = 'warn' AND active = true
            ''', (member.id,))
            warning_count = cursor.fetchone()[0]
        
        embed = discord.Embed(
            title=f"👤 Informações de {member.name}",
            color=member.color,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url)
        
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Conta criada", 
                       value=discord.utils.format_dt(member.created_at, 'R'), 
                       inline=True)
        embed.add_field(name="Entrou no servidor", 
                       value=discord.utils.format_dt(member.joined_at, 'R'), 
                       inline=True)
        
        roles = [role.mention for role in member.roles[1:]][:10]  # Ignorar @everyone
        embed.add_field(name=f"Cargos ({len(roles)})", 
                       value=" ".join(roles) if roles else "Nenhum cargo",
                       inline=False)
        
        embed.add_field(name="🎫 Tickets", value=ticket_count, inline=True)
        embed.add_field(name="⚠️ Advertências", value=warning_count, inline=True)
        embed.add_field(name="📊 Status", 
                       value=f"Online: {'✅' if member.status == discord.Status.online else '❌'}\n"
                             f"Mobile: {'✅' if member.is_on_mobile() else '❌'}",
                       inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utilities(bot))
