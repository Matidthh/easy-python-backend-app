import discord
from discord.ext import commands
from datetime import datetime
import pytz


class InstagramSystem:

    def __init__(self, bot):
        self.bot = bot
        self.instagram_profiles = {}
        self.setup_commands()

    def setup_commands(self):

        @self.bot.command(name="register")
        async def register(ctx, nickname: str):
            user_id = ctx.author.id
            if nickname in self.instagram_profiles:
                await ctx.send("Este nickname ya está en uso. Usa otro.")
                return
            if user_id in self.instagram_profiles.values():
                await ctx.send(
                    "Ya estás registrado. Usa `pc!delete` para eliminar tu perfil actual."
                )
                return
            self.instagram_profiles[nickname] = user_id
            await ctx.send(
                f"✅ Registrado correctamente con el nickname: `{nickname}`")

        @self.bot.command(name="post")
        async def post(ctx, *, message: str = None):
            user_id = ctx.author.id
            nickname = None
            for nick, uid in self.instagram_profiles.items():
                if uid == user_id:
                    nickname = nick
                    break

            if not nickname:
                await ctx.send(
                    "Debes registrarte primero con `pc!register <nickname>`.")
                return

            # Hora chilena
            tz = pytz.timezone("America/Santiago")
            now = datetime.now(tz)
            fecha_str = now.strftime("%d/%m/%Y - %H:%M")

            embed = discord.Embed(title="📸 Sistema de Instagram",
                                  color=discord.Color.magenta(),
                                  timestamp=now)

            # Campos lado a lado usando '\u200b' para espacio en blanco
            embed.add_field(name="**Nombre:**",
                            value=f"**{nickname}**",
                            inline=True)
            embed.add_field(name="**Fecha de envío:**",
                            value=f"**{fecha_str}**",
                            inline=True)

            # Publicación
            if message:
                embed.add_field(name="**Publicación subida:**",
                                value=message,
                                inline=False)
            else:
                embed.add_field(name="**Publicación subida:**",
                                value="(Sin mensaje)",
                                inline=False)

            # Añadir imagen si el usuario adjunta alguna
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
                if attachment.content_type.startswith('image/'):
                    embed.set_image(url=attachment.url)

            # Thumbnail con el logo del servidor
            if ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)

            embed.set_footer(text="Puro Chile RP - Sistema Instagram")

            # Enviar embed
            sent_message = await ctx.send(embed=embed)

            # Borrar mensaje original para limpieza
            await ctx.message.delete()

            # Agregar reacción de corazón
            await sent_message.add_reaction("❤️")

            # Crear hilo para respuestas públicas
            thread = await sent_message.create_thread(
                name=f"Respuestas a {nickname}", auto_archive_duration=60)
            # Puedes guardar o manejar el thread si quieres luego

        @self.bot.command(name="delete")
        async def delete(ctx):
            user_id = ctx.author.id
            nickname_to_delete = None
            for nick, uid in self.instagram_profiles.items():
                if uid == user_id:
                    nickname_to_delete = nick
                    break
            if not nickname_to_delete:
                await ctx.send("❌ No estás registrado actualmente.")
                return
            del self.instagram_profiles[nickname_to_delete]
            await ctx.send("✅ Tu perfil ha sido eliminado con éxito.")
