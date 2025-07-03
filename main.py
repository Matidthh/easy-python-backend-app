import discord
from discord.ext import commands
import os
import asyncio
import json
from datetime import datetime
from keep_alive import keep_alive

# Sistemas base
from bot_commands import BotCommands
from whitelist_system import WhitelistSystem
from reaction_logger import ReactionLogger
from warn_system import WarnSystem
from job_system import JobSystem
from rating_system import RatingSystem
from suggestion_system import SuggestionSystem
from warning_system import WarningSystem
from staff_accept_system import StaffAcceptSystem
from activity_check_system import ActivityCheckSystem
from auto_warning_system import AutoWarningSystem
from anonymous_system import AnonymousSystem
from register_instagram import InstagramSystem
from historial_user import HistorialUser
from system_ck import CKSystem
from whitelist_schedule_system import WhitelistScheduleSystem
from global_ban_system import GlobalBanSystem
from radio_system import RadioSystem
# Eliminar el sistema de autoayuda
# from ticket_autohelp_system import TicketAutoHelpSystem

# Configuración del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='pc!', intents=intents)

# Inicialización de sistemas
bot_commands = BotCommands(bot)
whitelist_system = WhitelistSystem(bot)
reaction_logger = ReactionLogger(bot)
warn_system = WarnSystem(bot)
job_system = JobSystem(bot)
rating_system = RatingSystem(bot)
suggestion_system = SuggestionSystem(bot)
warning_system = WarningSystem(bot)
staff_accept_system = StaffAcceptSystem(bot)
activity_check_system = ActivityCheckSystem(bot)
auto_warning_system = AutoWarningSystem(bot, warning_system)
instagram_system = InstagramSystem(bot)
anonymous_system = AnonymousSystem(bot)
historial_user = HistorialUser(bot)
ck_system = CKSystem(bot)
whitelist_schedule_system = WhitelistScheduleSystem(bot)
global_ban_system = GlobalBanSystem(bot)
radio_system = RadioSystem(bot)
# Eliminar la inicialización de TicketAutoHelpSystem
# ticket_autohelp_system = TicketAutoHelpSystem(bot)

# Eliminar comando de ayuda por defecto
bot.remove_command('help')


@bot.event
async def on_ready():
    print(f'{bot.user} ha iniciado sesión y está listo!')
    print(f'Bot ID: {bot.user.id}')
    await bot.change_presence(status=discord.Status.dnd,
                              activity=discord.Game(name="Puro Chile RP"))

    try:
        synced = await bot.tree.sync()
        print(f'Sincronizados {len(synced)} comandos slash')
    except Exception as e:
        print(f'Error sincronizando comandos: {e}')

    await register_persistent_views()
    whitelist_schedule_system.start_schedule_system()
    print(
        "🔧 Sistema de Auto-Ayuda: MODO MANTENIMIENTO - Solo comandos disponibles"
    )


@bot.event
async def on_message(message):
    if not message.author.bot:
        print(f"Mensaje recibido: '{message.content}' de {message.author}")
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Comando no encontrado",
            description=
            "El comando que intentaste usar no existe. Usa `pc!ayuda` para ver los comandos disponibles.",
            color=discord.Color.red())
        await ctx.send(embed=embed)

    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Argumento faltante",
            description=f"Te falta un argumento requerido: `{error.param}`",
            color=discord.Color.red())
        await ctx.send(embed=embed)

    elif isinstance(error, discord.DiscordServerError):
        embed = discord.Embed(
            title="⚠️ Problemas técnicos de Discord",
            description=
            "Discord está teniendo problemas técnicos, intenta de nuevo más tarde.",
            color=discord.Color.orange())
        await ctx.send(embed=embed)
        print(f"Error de servidor Discord: {error}")

    else:
        embed = discord.Embed(title="❌ Error no manejado",
                              description=f"Ocurrió un error: {str(error)}",
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        print(f"Error no manejado: {error}")


@bot.command(name='ping')
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!",
                          description=f"Latencia: {latency}ms",
                          color=discord.Color.green())
    await ctx.send(embed=embed)


@bot.command(name='ayuda')
async def help_command(ctx):
    staff_role_id = 1221496580620816473
    is_staff = any(role.id == staff_role_id for role in ctx.author.roles)

    if is_staff:
        embed = discord.Embed(
            title="👑 Comandos de Staff - Puro Chile RP",
            description="Lista completa de comandos administrativos",
            color=discord.Color.gold(),
            timestamp=datetime.now())

        embed.add_field(name="📊 Sistema de Calificaciones",
                        value="⭐ `pc!calificar @staff [puntos] [motivo]`\n"
                        "📈 `pc!vercalificaciones [@staff]`\n"
                        "🏆 `pc!topcalificaciones`",
                        inline=False)

        embed.add_field(name="⚠️ Sistema de Sanciones",
                        value="🚨 `pc!sancionar @usuario [motivo]`\n"
                        "📋 `pc!verwarns @usuario`\n"
                        "🗑️ `pc!removewarn @usuario [ID]`\n"
                        "🔥 `pc!resetwarns @usuario`",
                        inline=False)

        embed.add_field(name="⚠️ Sistema de Advertencias",
                        value="🚨 `pc!advertir @usuario [motivo]`\n"
                        "📋 `pc!veradvertencias @usuario`\n"
                        "🗑️ `pc!sacaradvertencia @usuario [ID]`",
                        inline=False)

        embed.add_field(name="🔧 Gestión de Whitelist",
                        value="🔄 `pc!reset-whitelist @usuario`\n"
                        "📋 `pc!historial @usuario`\n"
                        "✅ `pc!aceptar @usuario`\n"
                        "📊 `pc!activity [votos]`",
                        inline=False)

        embed.add_field(name="🔨 Sistema de Ban Global",
                        value="🔨 `pc!bang @usuario [razón]` (Ban Global)\n"
                        "✅ `pc!unbang @usuario` (Unban Global)\n"
                        "📋 `pc!globalbans` (Lista de bans globales)",
                        inline=False)

        embed.add_field(
            name="🛠️ Herramientas Administrativas",
            value="💀 `pc!ck` (Sistema CK)\n"
            "🎯 `/verwhitelist @usuario` (Ver respuestas completas)",
            inline=False)

        embed.add_field(
            name="📢 Sistema de Anuncios",
            value="📢 `pc!anuncio` (Iniciar anuncios cada 4 horas)\n"
            "🛑 `pc!parar-anuncios` (Detener anuncios automáticos)\n"
            "📊 `pc!estado-anuncios` (Ver estado del sistema)\n"
            "📝 `pc!anuncio-manual` (Enviar anuncio manual)",
            inline=False)

        embed.add_field(name="📩 Sistemas de Comunicación",
                        value="📩 `pc!anonimo [mensaje]` (Mensaje anónimo)\n"
                        "💡 `pc!sugerencia [texto]` (Recibir sugerencias)",
                        inline=False)

        embed.add_field(
            name="📻 Sistema de Radios",
            value="📻 `pc!radio @rol/@usuarios` (Crear radio temporal)\n"
            "🔒 `pc!cerrar-radio` (Cerrar tu radio)\n"
            "📋 `pc!radios-activas` (Ver radios activas)",
            inline=False)

        embed.add_field(
            name="🛡️ Sistemas Activos",
            value=
            "• Sistema de advertencias automáticas\n• Registro de reacciones\n• Mensajes automáticos de whitelist\n• Sistema de ban global",
            inline=False)

        embed.set_thumbnail(
            url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.set_footer(
            text="Puro Chile RP - Panel de Administración",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    else:
        embed = discord.Embed(
            title="👥 Comandos para Ciudadanos - Puro Chile RP",
            description="Lista de comandos disponibles para todos los usuarios",
            color=discord.Color.blue(),
            timestamp=datetime.now())

        embed.add_field(
            name="🎮 Sistema de Whitelist",
            value="📝 `pc!whitelist` (Crear solicitud de whitelist)\n"
            "🔄 `pc!rechazar-whitelist` (Reiniciar whitelist tras timeout)",
            inline=False)

        embed.add_field(
            name="🚨 Servicios de Emergencia",
            value="🚨 `pc!entorno` (Solicitar Policía/Médicos/Mecánicos)",
            inline=False)

        embed.add_field(
            name="💼 Sistema de Postulaciones",
            value="💼 `pc!postular` (Postular para trabajos disponibles)",
            inline=False)

        embed.add_field(
            name="💡 Sistema de Sugerencias",
            value="💡 `pc!sugerencia [texto]` (Enviar sugerencia al staff)",
            inline=False)

        embed.add_field(name="🏓 Información del Bot",
                        value="🏓 `pc!ping` (Ver latencia del bot)\n"
                        "❓ `pc!ayuda` (Ver este menú de ayuda)",
                        inline=False)

        embed.add_field(
            name="📋 Información Importante",
            value=
            "• **Whitelist**: Obligatorio para acceder al servidor\n• **Servicios de Emergencia**: Disponibles 24/7\n• **Sugerencias**: El staff revisa todas las sugerencias",
            inline=False)

        embed.add_field(
            name="⏰ Horarios de Whitelist",
            value=
            "**Días de Semana**: 4:00 PM - 11:00 PM\n**Fin de Semana**: 1:00 PM - 11:00 PM",
            inline=False)

        embed.set_thumbnail(
            url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
        embed.set_footer(
            text="Puro Chile RP - Comandos de Usuario",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    await ctx.send(embed=embed)


async def register_persistent_views():
    """Registrar todas las vistas persistentes para que funcionen después de reiniciar el bot"""
    try:
        # Importar las vistas que necesitan ser persistentes
        from suggestion_system import SuggestionVotingView
        from activity_check_system import ActivityCheckView
        from utils.views import EntornoView
        from radio_system import RadioView
        from whitelist_system import RobloxVerificationView, WhitelistReviewView
        from system_ck import CKView

        # Registrar vistas persistentes genéricas (sin datos específicos)
        bot.add_view(SuggestionVotingView(author_id=0))  # ID temporal
        bot.add_view(ActivityCheckView(required_votes=0,
                                       admin_id=0))  # Valores temporales
        bot.add_view(EntornoView(bot))
        bot.add_view(RadioView(creator_id=0, radio_name="",
                               voice_channel=None))  # Valores temporales

        # Registrar vistas del sistema de whitelist
        bot.add_view(
            RobloxVerificationView(
                user_id=0, whitelist_system=whitelist_system))  # ID temporal
        bot.add_view(
            WhitelistReviewView(user_id=0,
                                channel_id=0,
                                whitelist_system=whitelist_system,
                                roblox_info={}))  # Valores temporales

        # Registrar vistas del sistema de CK
        bot.add_view(CKView(user_id=0, bot=bot))  # ID temporal

        print("✅ Vistas persistentes registradas correctamente")
    except Exception as e:
        print(f"❌ Error registrando vistas persistentes: {e}")


async def init_data_directories():
    os.makedirs('data', exist_ok=True)

    if not os.path.exists('data/whitelist_applications.json'):
        with open('data/whitelist_applications.json', 'w') as f:
            json.dump([], f)

    if not os.path.exists('data/reaction_logs.json'):
        with open('data/reaction_logs.json', 'w') as f:
            json.dump([], f)

    if not os.path.exists('data/suggestions.json'):
        with open('data/suggestions.json', 'w') as f:
            json.dump([], f)


async def main():
    await init_data_directories()
    await rating_system.init_database()
    keep_alive()

    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print(
            "❌ Error: DISCORD_BOT_TOKEN no encontrado en las variables de entorno"
        )
        return

    try:
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ Error: Token de bot inválido")
    except Exception as e:
        print(f"❌ Error iniciando el bot: {e}")


if __name__ == '__main__':
    asyncio.run(main())
