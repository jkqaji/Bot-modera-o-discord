import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
from datetime import datetime
import random
import string
from config import Config

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, emoji="📩", custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.db
        user_tickets = await db.get_user_tickets(interaction.user.id)
        
        # Verificar limite de tickets
        open_tickets = [t for t in user_tickets if t['status'] == 'open']
        if len(open_tickets) >= Config.MAX_TICKETS_PER_USER:
            await interaction.followup.send(
                f"❌ Você já tem {len(open_tickets)} tickets abertos. "
                f"O máximo permitido é {Config.MAX_TICKETS_PER_USER}.",
                ephemeral=True
            )
            return
        
        # Gerar ID único para o ticket
        ticket_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Obter categoria
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=Config.TICKET_CATEGORY)
        
        if not category:
            await interaction.followup.send("❌ Categoria de tickets não configurada.", ephemeral=True)
            return
        
        # Criar canal do ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(Config.SUPPORT_ROLE): discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True
            ),
            guild.get_role(Config.ADMIN_ROLE): discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True, manage_channels=True
            )
        }
        
        channel = await category.create_text_channel(
            name=f"ticket-{ticket_id}",
            overwrites=overwrites,
            topic=f"Ticket de {interaction.user.name} | ID: {ticket_id}"
        )
        
        # Salvar no banco de dados
        await db.create_ticket(ticket_id, interaction.user.id, channel.id, "support")
        
        # Embed de boas-vindas
        embed = discord.Embed(
            title=f"Ticket #{ticket_id}",
            description=Config.WELCOME_MESSAGE,
            color=Config.COLORS['ticket']
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="Criado por", value=interaction.user.mention)
        embed.add_field(name="Data", value=discord.utils.format_dt(datetime.now(), 'F'))
        embed.set_footer(text="Use os botões abaixo para interagir com o ticket.")
        
        # View com ações do ticket
        ticket_view = TicketActionsView(ticket_id)
        
        await channel.send(
            content=f"{interaction.user.mention} | <@&{Config.SUPPORT_ROLE}>",
            embed=embed,
            view=ticket_view
        )
        
        # Log
        log_channel = guild.get_channel(Config.TICKET_LOG_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="🎫 Ticket Criado",
                color=Config.COLORS['success']
            )
            log_embed.add_field(name="ID", value=ticket_id)
            log_embed.add_field(name="Usuário", value=f"{interaction.user.mention}\n({interaction.user.id})")
            log_embed.add_field(name="Canal", value=channel.mention)
            await log_channel.send(embed=log_embed)
        
        await interaction.followup.send(
            f"✅ Ticket criado com sucesso! Acesse em {channel.mention}",
            ephemeral=True
        )

class TicketActionsView(View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
    
    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒", custom_id=f"close_ticket_")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        # Verificar permissões
        if not any(role.id in [Config.SUPPORT_ROLE, Config.ADMIN_ROLE, Config.MOD_ROLE] 
                  for role in interaction.user.roles):
            await interaction.followup.send("❌ Você não tem permissão para fechar tickets.", ephemeral=True)
            return
        
        # Modal para motivo do fechamento
        modal = CloseTicketModal(self.ticket_id)
        await interaction.followup.send_modal(modal)
    
    @discord.ui.button(label="Transcrever", style=discord.ButtonStyle.secondary, emoji="📄", custom_id=f"transcript_")
    async def transcript_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        if not any(role.id in [Config.SUPPORT_ROLE, Config.ADMIN_ROLE, Config.MOD_ROLE] 
                  for role in interaction.user.roles):
            await interaction.followup.send("❌ Permissão negada.", ephemeral=True)
            return
        
        # Criar transcrição
        messages = []
        async for message in interaction.channel.history(limit=500, oldest_first=True):
            messages.append(f"{message.author.name} ({message.author.id}) [{message.created_at}]: {message.content}")
        
        transcript = "\n".join(messages)
        
        # Salvar em arquivo
        filename = f"transcript_{self.ticket_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        await interaction.followup.send(
            f"📄 Transcrição criada!",
            file=discord.File(filename),
            ephemeral=True
        )
    
    @discord.ui.button(label="Reabrir", style=discord.ButtonStyle.success, emoji="🔓", custom_id=f"reopen_ticket_")
    async def reopen_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        
        if not any(role.id in [Config.ADMIN_ROLE, Config.MOD_ROLE] for role in interaction.user.roles):
            await interaction.followup.send("❌ Apenas moderadores podem reabrir tickets.", ephemeral=True)
            return
        
        db = interaction.client.db
        ticket = await db.get_ticket(self.ticket_id)
        
        if not ticket:
            await interaction.followup.send("❌ Ticket não encontrado.", ephemeral=True)
            return
        
        # Mover para categoria aberta
        category = discord.utils.get(interaction.guild.categories, id=Config.TICKET_CATEGORY)
        if category:
            await interaction.channel.edit(category=category)
        
        # Atualizar status
        with db.get_connection() as conn:
            conn.execute('UPDATE tickets SET status = "open", closed_at = NULL WHERE ticket_id = ?', 
                        (self.ticket_id,))
        
        embed = discord.Embed(
            title="🔓 Ticket Reaberto",
            description=f"Ticket reaberto por {interaction.user.mention}",
            color=Config.COLORS['success']
        )
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Ticket reaberto com sucesso!")

class CloseTicketModal(discord.ui.Modal, title="Fechar Ticket"):
    def __init__(self, ticket_id):
        super().__init__()
        self.ticket_id = ticket_id
        
        self.reason = discord.ui.TextInput(
            label="Motivo do fechamento",
            placeholder="Digite o motivo do fechamento...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        db = interaction.client.db
        
        # Fechar no banco de dados
        await db.close_ticket(self.ticket_id, interaction.user.id, self.reason.value)
        
        # Mover para categoria de fechados
        guild = interaction.guild
        closed_category = discord.utils.get(guild.categories, id=Config.CLOSED_CATEGORY)
        
        if closed_category:
            await interaction.channel.edit(
                category=closed_category,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.get_role(Config.ADMIN_ROLE): discord.PermissionOverwrite(read_messages=True)
                }
            )
        
        # Embed de fechamento
        embed = discord.Embed(
            title=f"🔒 Ticket Fechado",
            description=f"Ticket fechado por {interaction.user.mention}",
            color=Config.COLORS['error']
        )
        if self.reason.value:
            embed.add_field(name="Motivo", value=self.reason.value)
        embed.set_footer(text=f"Ticket ID: {self.ticket_id}")
        
        await interaction.channel.send(embed=embed)
        
        # Log
        log_channel = guild.get_channel(Config.TICKET_LOG_CHANNEL)
        if log_channel:
            log_embed = discord.Embed(
                title="🔒 Ticket Fechado",
                color=Config.COLORS['warning']
            )
            log_embed.add_field(name="ID", value=self.ticket_id)
            log_embed.add_field(name="Moderador", value=interaction.user.mention)
            log_embed.add_field(name="Motivo", value=self.reason.value or "Não especificado")
            await log_channel.send(embed=log_embed)
        
        await interaction.followup.send("✅ Ticket fechado com sucesso!", ephemeral=True)

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        # Registrar views persistentes
        self.bot.add_view(TicketView())
    
    @commands.command(name="setup-tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Configura o sistema de tickets no canal atual"""
        embed = discord.Embed(
            title="🎫 Sistema de Suporte",
            description="Clique no botão abaixo para abrir um novo ticket de suporte.\n"
                       "Nossa equipe responderá o mais rápido possível!",
            color=Config.COLORS['ticket']
        )
        embed.add_field(
            name="📋 Diretrizes",
            value="• Descreva seu problema claramente\n"
                  "• Seja respeitoso com a equipe\n"
                  "• Não abra tickets desnecessários",
            inline=False
        )
        
        await ctx.send(embed=embed, view=TicketView())
        await ctx.message.delete()
    
    @commands.command(name="add-user")
    @commands.has_role(Config.SUPPORT_ROLE)
    async def add_user_to_ticket(self, ctx, member: discord.Member):
        """Adiciona um usuário ao ticket atual"""
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        embed = discord.Embed(
            description=f"✅ {member.mention} foi adicionado ao ticket.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="remove-user")
    @commands.has_role(Config.SUPPORT_ROLE)
    async def remove_user_from_ticket(self, ctx, member: discord.Member):
        """Remove um usuário do ticket atual"""
        await ctx.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(
            description=f"✅ {member.mention} foi removido do ticket.",
            color=Config.COLORS['success']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="ticket-info")
    async def ticket_info(self, ctx):
        """Mostra informações sobre o ticket atual"""
        db = self.bot.db
        
        # Extrair ID do ticket do nome do canal
        if ctx.channel.name.startswith("ticket-"):
            ticket_id = ctx.channel.name.split("-")[1]
            ticket = await db.get_ticket(ticket_id)
            
            if ticket:
                user = await self.bot.fetch_user(ticket['user_id'])
                closed_by = await self.bot.fetch_user(ticket['closed_by']) if ticket['closed_by'] else None
                
                embed = discord.Embed(
                    title=f"Informações do Ticket #{ticket_id}",
                    color=Config.COLORS['info']
                )
                embed.add_field(name="Criado por", value=f"{user.mention}\n({user.id})")
                embed.add_field(name="Status", value=ticket['status'].upper())
                embed.add_field(name="Categoria", value=ticket['category'])
                embed.add_field(name="Criado em", value=discord.utils.format_dt(
                    datetime.fromisoformat(ticket['created_at']), 'F'
                ))
                
                if ticket['closed_at']:
                    embed.add_field(name="Fechado em", value=discord.utils.format_dt(
                        datetime.fromisoformat(ticket['closed_at']), 'F'
                    ))
                    if closed_by:
                        embed.add_field(name="Fechado por", value=closed_by.mention)
                    if ticket['reason']:
                        embed.add_field(name="Motivo", value=ticket['reason'], inline=False)
                
                await ctx.send(embed=embed)
                return
        
        await ctx.send("❌ Este não é um canal de ticket válido.")

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
