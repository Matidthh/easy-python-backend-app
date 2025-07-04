import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo


class AnonymousSystem:

    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()

    def setup_commands(self):

        @self.bot.command(name="anonimo")
        async def mensaje_anonimo(ctx, *, mensaje: str = None):
            canal_destino = ctx.channel
            canal_logs_id = 1234043843746205736  # Reemplaza con tu ID real
            canal_logs = self.bot.get_channel(canal_logs_id)

            if not canal_logs:
                await ctx.send(
                    "❌ No se pudo encontrar el canal de logs configurado.")
                return

            archivos = [
                await archivo.to_file() for archivo in ctx.message.attachments
            ]
            contenido = mensaje if mensaje else "(Sin mensaje)"

            # Hora chilena
            hora_chilena = datetime.now(ZoneInfo("America/Santiago"))

            embed_anonimo = discord.Embed(title="📩 Mensaje Anónimo",
                                          color=discord.Color.dark_gray(),
                                          timestamp=hora_chilena)

            embed_anonimo.add_field(name="📍 Ubicación",
                                    value="Desconocid@",
                                    inline=True)
            embed_anonimo.add_field(name="\u200b", value="\u200b",
                                    inline=True)  # Separador
            embed_anonimo.add_field(name="👤 Autor",
                                    value="Desconocid@",
                                    inline=True)

            embed_anonimo.add_field(name="💬 Mensaje",
                                    value=contenido,
                                    inline=True)
            embed_anonimo.add_field(name="\u200b", value="\u200b",
                                    inline=True)  # Separador
            embed_anonimo.add_field(
                name="📅 Fecha y Hora",
                value=hora_chilena.strftime("%d/%m/%Y - %H:%M"),
                inline=True)

            if ctx.guild and ctx.guild.icon:
                embed_anonimo.set_thumbnail(url=ctx.guild.icon.url)

            embed_anonimo.set_footer(text="Sistema de mensajes anónimos")

            await canal_destino.send(embed=embed_anonimo, files=archivos)

            embed_log = discord.Embed(
                title="📋 Log de Mensaje Anónimo",
                description=(
                    f"Enviado por: {ctx.author.mention} (`{ctx.author.id}`)\n\n"
                    f"**Contenido:**\n{contenido}"),
                color=discord.Color.red(),
                timestamp=hora_chilena)
            embed_log.set_footer(
                text=
                f"Canal original: #{ctx.channel.name} (ID: {ctx.channel.id})")

            await canal_logs.send(embed=embed_log, files=archivos)

            await ctx.message.delete()
