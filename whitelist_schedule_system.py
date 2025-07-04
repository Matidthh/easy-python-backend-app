import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, time, timedelta
import pytz


class WhitelistScheduleSystem:

    def __init__(self, bot):
        self.bot = bot
        self.announcement_active = False
        self.setup_system()

    def setup_system(self):
        """Configurar el sistema de mensajes automáticos"""

        # Configuración fácil de modificar
        self.config = {
            'channel_id':
            1221496581828776050,  # Canal donde se enviarán los mensajes
            'timezone':
            'America/Santiago',  # Zona horaria de Chile

            # Contenido del mensaje (fácil de modificar)
            'title':
            '📋 ¡Sistema de Whitelist Disponible!',
            'description':
            '¡Hola! Te recordamos que nuestro sistema de whitelist está **activo** y listo para nuevos usuarios.',
            'color':
            0x00ff88,  # Color verde brillante

            # Horarios (fácil de modificar)
            'weekday_hours': {
                'start': '4:00 PM',
                'end': '11:00 PM',
                'days': 'Lunes a Viernes'
            },
            'weekend_hours': {
                'start': '1:00 PM',
                'end': '11:00 PM',
                'days': 'Sábados y Domingos'
            },

            # Comando y mensajes adicionales
            'command':
            'pc!whitelist',
            'footer_text':
            'Puro Chile RP - Sistema Automatizado',
            'warning_message':
            '⚠️ **Fuera de estos horarios es probable que el bot no responda o esté apagado**\n\n🙏 **Por favor respeta los horarios y evita dejar el sistema a medias en la whitelist.**'
        }

    @tasks.loop(hours=4)  # Se ejecuta cada 4 horas
    async def automatic_announcements(self):
        """Enviar anuncios automáticos cada 4 horas"""
        try:
            if not self.announcement_active:
                return

            # Obtener el canal
            channel = self.bot.get_channel(self.config['channel_id'])
            if not channel:
                print(
                    f"❌ Canal {self.config['channel_id']} no encontrado para mensaje de whitelist"
                )
                return

            # Crear el embed decorativo
            embed = await self.create_announcement_embed()

            # Enviar el mensaje
            await channel.send(embed=embed)
            print(
                f"✅ Anuncio automático de whitelist enviado a {channel.name} (cada 4 horas)")

        except Exception as e:
            print(f"❌ Error enviando anuncio automático de whitelist: {e}")

    async def create_announcement_embed(self):
        """Crear el embed del anuncio"""
        embed = discord.Embed(title=self.config['title'],
                              description=self.config['description'],
                              color=self.config['color'],
                              timestamp=datetime.now())

        # Agregar información del comando
        embed.add_field(
            name="🎮 ¿Cómo hacer la whitelist?",
            value=
            f"Usa el comando: **`{self.config['command']}`**\nEste comando creará un canal privado para tu proceso de whitelist con verificación de Roblox.",
            inline=False)

        # Agregar horarios de semana
        embed.add_field(
            name="📅 Horarios de Atención - Días de Semana",
            value=
            f"**{self.config['weekday_hours']['days']}**\n🕐 {self.config['weekday_hours']['start']} - {self.config['weekday_hours']['end']}",
            inline=True)

        # Agregar horarios de fin de semana
        embed.add_field(
            name="📅 Horarios de Atención - Fin de Semana",
            value=
            f"**{self.config['weekend_hours']['days']}**\n🕐 {self.config['weekend_hours']['start']} - {self.config['weekend_hours']['end']}",
            inline=True)

        # Espacio vacío para formato
        embed.add_field(name="\u200b", value="\u200b", inline=True)

        # Mensaje de advertencia
        embed.add_field(name="⚠️ Importante",
                        value=self.config['warning_message'],
                        inline=False)

        # Información adicional
        embed.add_field(
            name="✨ Características del Nuevo Sistema",
            value=
            "• 🔗 **Verificación con Roblox** - Vincula tu cuenta automáticamente\n• 📊 **Información completa** - Obtiene datos de tu perfil de Roblox\n• 🚀 **Proceso mejorado** - Más rápido y eficiente\n• 👥 **Atención personalizada** - Canal privado para cada usuario",
            inline=False)

        # Configurar thumbnail y footer
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/emojis/842109479665860628.png"
        )  # Emoji de Roblox
        embed.set_footer(text=self.config['footer_text'],
                         icon_url=self.bot.user.avatar.url
                         if self.bot.user.avatar else None)

        return embed

    async def send_initial_announcement(self, channel):
        """Enviar anuncio inicial y iniciar ciclo de 4 horas"""
        try:
            embed = await self.create_announcement_embed()
            
            # Agregar información sobre el ciclo automático
            embed.add_field(
                name="🔄 Sistema Automático Activado",
                value="📢 **Los anuncios se enviarán automáticamente cada 4 horas**\n⏰ Próximo anuncio en 4 horas",
                inline=False)
            
            await channel.send(embed=embed)
            print(f"✅ Anuncio inicial enviado a {channel.name}")
            
            # Activar los anuncios automáticos
            self.announcement_active = True
            if not self.automatic_announcements.is_running():
                self.automatic_announcements.start()
                print("✅ Sistema de anuncios cada 4 horas iniciado")
            
        except Exception as e:
            print(f"❌ Error enviando anuncio inicial: {e}")

    def stop_announcements(self):
        """Detener los anuncios automáticos"""
        self.announcement_active = False
        if self.automatic_announcements.is_running():
            self.automatic_announcements.cancel()
            print("🛑 Anuncios automáticos de whitelist detenidos")

    @automatic_announcements.before_loop
    async def before_automatic_announcements(self):
        """Esperar hasta que el bot esté listo"""
        await self.bot.wait_until_ready()

    def start_schedule_system(self):
        """Este método ya no inicia automáticamente el sistema"""
        print("✅ Sistema de anuncios configurado - Use pc!anuncio para activar")

    # Métodos para modificar la configuración fácilmente
    def update_schedule_config(self, **kwargs):
        """Actualizar configuración del sistema de forma fácil"""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                print(f"✅ Configuración actualizada: {key} = {value}")
            else:
                print(f"⚠️ Clave de configuración no reconocida: {key}")

    def update_weekday_hours(self, start_time, end_time):
        """Actualizar horarios de días de semana"""
        self.config['weekday_hours']['start'] = start_time
        self.config['weekday_hours']['end'] = end_time
        print(f"✅ Horarios de semana actualizados: {start_time} - {end_time}")

    def update_weekend_hours(self, start_time, end_time):
        """Actualizar horarios de fin de semana"""
        self.config['weekend_hours']['start'] = start_time
        self.config['weekend_hours']['end'] = end_time
        print(
            f"✅ Horarios de fin de semana actualizados: {start_time} - {end_time}"
        )

    def update_channel(self, channel_id):
        """Cambiar canal donde se envían los mensajes"""
        self.config['channel_id'] = channel_id
        print(f"✅ Canal actualizado: {channel_id}")

    def manual_send_message(self):
        """Enviar mensaje manualmente (para pruebas)"""
        asyncio.create_task(self.daily_whitelist_reminder())
        print("🔄 Enviando mensaje manual...")

    # Comandos para el staff para controlar el sistema
    def setup_staff_commands(self):
        """Configurar comandos para el staff"""

        def is_staff():
            def predicate(ctx):
                staff_role_id = 1221496580620816473
                return any(role.id == staff_role_id
                           for role in ctx.author.roles)
            return commands.check(predicate)

        @self.bot.command(name='anuncio')
        @is_staff()
        async def start_announcements(ctx):
            """Iniciar sistema de anuncios automáticos cada 4 horas"""
            try:
                # Eliminar el mensaje del comando para mantener el canal limpio
                await ctx.message.delete()
                
                if self.announcement_active:
                    embed = discord.Embed(
                        title="⚠️ Sistema ya activo",
                        description="Los anuncios automáticos ya están funcionando.\nUsa `pc!parar-anuncios` para detenerlos.",
                        color=discord.Color.orange())
                    message = await ctx.send(embed=embed)
                    # Eliminar el mensaje después de 5 segundos
                    await asyncio.sleep(5)
                    await message.delete()
                    return
                
                # Enviar anuncio inicial e iniciar sistema automático
                await self.send_initial_announcement(ctx.channel)
                
                # Confirmar activación (mensaje temporal)
                embed = discord.Embed(
                    title="✅ Sistema Activado",
                    description="Anuncios automáticos iniciados.\nSe enviará un anuncio cada 4 horas.",
                    color=discord.Color.green())
                confirmation = await ctx.send(embed=embed)
                
                # Eliminar confirmación después de 10 segundos
                await asyncio.sleep(10)
                await confirmation.delete()
                
            except Exception as e:
                await ctx.send(f"❌ Error iniciando anuncios: {e}")

        @self.bot.command(name='parar-anuncios')
        @is_staff()
        async def stop_announcements_command(ctx):
            """Detener los anuncios automáticos"""
            try:
                await ctx.message.delete()
                
                if not self.announcement_active:
                    embed = discord.Embed(
                        title="⚠️ Sistema inactivo",
                        description="Los anuncios automáticos no están funcionando.",
                        color=discord.Color.orange())
                    message = await ctx.send(embed=embed)
                    await asyncio.sleep(5)
                    await message.delete()
                    return
                
                self.stop_announcements()
                
                embed = discord.Embed(
                    title="🛑 Sistema Detenido",
                    description="Los anuncios automáticos han sido detenidos.",
                    color=discord.Color.red())
                confirmation = await ctx.send(embed=embed)
                
                await asyncio.sleep(5)
                await confirmation.delete()
                
            except Exception as e:
                await ctx.send(f"❌ Error deteniendo anuncios: {e}")

        @self.bot.command(name='estado-anuncios')
        @is_staff()
        async def announcement_status(ctx):
            """Ver estado del sistema de anuncios"""
            try:
                embed = discord.Embed(
                    title="📊 Estado del Sistema de Anuncios",
                    color=discord.Color.blue(),
                    timestamp=datetime.now())
                
                status = "🟢 Activo" if self.announcement_active else "🔴 Inactivo"
                embed.add_field(name="Estado", value=status, inline=True)
                
                if self.announcement_active and self.automatic_announcements.is_running():
                    next_run = self.automatic_announcements.next_iteration
                    if next_run:
                        embed.add_field(name="Próximo anuncio", 
                                      value=f"<t:{int(next_run.timestamp())}:R>", 
                                      inline=True)
                
                embed.add_field(name="📍 Canal",
                              value=f"<#{self.config['channel_id']}>",
                              inline=True)
                embed.add_field(name="⏰ Frecuencia",
                              value="Cada 4 horas",
                              inline=True)
                
                embed.add_field(
                    name="📅 Horarios de Semana",
                    value=f"{self.config['weekday_hours']['start']} - {self.config['weekday_hours']['end']}",
                    inline=True)
                embed.add_field(
                    name="📅 Horarios de Fin de Semana",
                    value=f"{self.config['weekend_hours']['start']} - {self.config['weekend_hours']['end']}",
                    inline=True)
                
                embed.set_footer(text="Use pc!anuncio para activar o pc!parar-anuncios para detener")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error obteniendo estado: {e}")

        @self.bot.command(name='anuncio-manual')
        @is_staff()
        async def manual_announcement(ctx):
            """Enviar un anuncio manual sin afectar el sistema automático"""
            try:
                await ctx.message.delete()
                
                embed = await self.create_announcement_embed()
                embed.add_field(
                    name="📋 Anuncio Manual",
                    value="Este es un anuncio enviado manualmente por el staff.",
                    inline=False)
                
                await ctx.send(embed=embed)
                print(f"✅ Anuncio manual enviado por {ctx.author}")
                
            except Exception as e:
                await ctx.send(f"❌ Error enviando anuncio manual: {e}")
