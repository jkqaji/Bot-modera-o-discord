import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Token do bot
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    # IDs importantes
    GUILD_ID = int(os.getenv('GUILD_ID', 0))
    
    # Canais
    TICKET_LOG_CHANNEL = int(os.getenv('TICKET_LOG_CHANNEL', 0))
    MOD_LOG_CHANNEL = int(os.getenv('MOD_LOG_CHANNEL', 0))
    
    # Cargos
    ADMIN_ROLE = int(os.getenv('ADMIN_ROLE', 0))
    MOD_ROLE = int(os.getenv('MOD_ROLE', 0))
    SUPPORT_ROLE = int(os.getenv('SUPPORT_ROLE', 0))
    
    # Cores para embeds
    COLORS = {
        'success': 0x2ecc71,
        'error': 0xe74c3c,
        'warning': 0xf39c12,
        'info': 0x3498db,
        'ticket': 0x9b59b6
    }
    
    # Configurações de tickets
    TICKET_CATEGORY = int(os.getenv('TICKET_CATEGORY', 0))
    CLOSED_CATEGORY = int(os.getenv('CLOSED_CATEGORY', 0))
    
    # Limites
    MAX_TICKETS_PER_USER = 3
    AUTO_CLOSE_DAYS = 7
    
    # Mensagens
    WELCOME_MESSAGE = "📨 **Bem-vindo ao seu ticket!**\n\n"
    "A nossa equipe de suporte estará com você em breve.\n"
    "Enquanto isso, descreva detalhadamente o seu problema."
