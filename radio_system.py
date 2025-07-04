import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import json
import os

# Configuración
RADIO_CATEGORY_ID = 1221496583447908513  # Categoría donde se crearán las radios
AUTHORIZED_ROLE_ID = 1221496580570353695  # Rol autorizado para crear radios


class RadioSystem:

    def __init__(self, bot):
        self.bot = bot
        self.active_radios = {
        }  # user_id: {'channel': channel, 'created_at': datetime}
        self.cleanup_task_running = False
        self.setup_commands()

    def setup_commands(self):
        """Configurar comandos del sistema de radio"""

        def is_authorized():

            def predicate(ctx):
                return any(role.id == AUTHORIZED_ROLE_ID
                           for role in ctx.author.roles)

            return commands.check(predicate)

        @self.bot.command(name='radio')
        @is_authorized()
        async def radio_command(ctx, *members):
            """Crear una radio (canal de voz temporal) para el grupo"""

            # Verificar si el usuario ya tiene una radio activa
            if ctx.author.id in self.active_radios:
                embed = discord.Embed(
                    title="❌ Radio ya activa",
                    description=
                    "Ya tienes una radio activa. Solo puedes tener una radio a la vez.",
                    color=discord.Color.red())
                await ctx.send(embed=embed, delete_after=10)
                return

            # Obtener la categoría de radios
            category = self.bot.get_channel(RADIO_CATEGORY_ID)
            if not category:
                embed = discord.Embed(
                    title="❌ Error de configuración",
                    description="No se encontró la categoría de radios.",
                    color=discord.Color.red())
                await ctx.send(embed=embed, delete_after=10)
                return

            # Procesar miembros mencionados
            radio_members = [ctx.author]  # El creador siempre está incluido
            roles_mentioned = []

            for item in members:
                # Si es una mención de rol
                if item.startswith('<@&'):
                    role_id = int(item.replace('<@&', '').replace('>', ''))
                    role = ctx.guild.get_role(role_id)
                    if role:
                        roles_mentioned.append(role)
                        radio_members.extend(role.members)

                # Si es una mención de usuario
                elif item.startswith('<@'):
                    user_id = int(
                        item.replace('<@!', '').replace('<@',
                                                        '').replace('>', ''))
                    member = ctx.guild.get_member(user_id)
                    if member and member not in radio_members:
                        radio_members.append(member)

            # Eliminar duplicados
            radio_members = list(set(radio_members))

            if len(radio_members
                   ) > 15:  # Límite de Discord para canales de voz
                embed = discord.Embed(
                    title="❌ Demasiados miembros",
                    description="Una radio no puede tener más de 15 miembros.",
                    color=discord.Color.red())
                await ctx.send(embed=embed, delete_after=10)
                return

            try:
                # Crear nombre del canal
                channel_name = f"📻-radio-{ctx.author.display_name.lower()}"

                # Configurar permisos
                overwrites = {
                    ctx.guild.default_role:
                    discord.PermissionOverwrite(view_channel=False,
                                                connect=False)
                }

                # Dar permisos a los miembros de la radio
                for member in radio_members:
                    overwrites[member] = discord.PermissionOverwrite(
                        view_channel=True,
                        connect=True,
                        speak=True,
                        use_voice_activation=True)

                # Crear el canal de voz
                voice_channel = await category.create_voice_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    user_limit=len(radio_members))

                # Registrar la radio activa
                self.active_radios[ctx.author.id] = {
                    'channel': voice_channel,
                    'created_at': datetime.now(),
                    'members': radio_members
                }

                # Crear embed de confirmación
                embed = discord.Embed(
                    title="📻 Radio Creada Exitosamente",
                    description=
                    f"Se ha creado tu radio personal: {voice_channel.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now())

                # Lista de miembros
                members_list = []
                for member in radio_members[:
                                            10]:  # Máximo 10 para evitar que sea muy largo
                    members_list.append(f"• {member.display_name}")

                if len(radio_members) > 10:
                    members_list.append(
                        f"• ... y {len(radio_members) - 10} más")

                embed.add_field(
                    name=f"👥 Miembros con acceso ({len(radio_members)})",
                    value="\n".join(members_list)
                    if members_list else "Solo tú",
                    inline=False)

                if roles_mentioned:
                    roles_text = ", ".join(
                        [role.name for role in roles_mentioned])
                    embed.add_field(name="🎭 Roles incluidos",
                                    value=roles_text,
                                    inline=False)

                embed.add_field(
                    name="⚠️ Información importante",
                    value=
                    "• La radio se eliminará automáticamente después de 10 minutos de inactividad\n"
                    "• Solo los miembros autorizados pueden ver y conectarse\n"
                    "• El canal se elimina cuando no hay nadie conectado por 10 minutos",
                    inline=False)

                embed.set_footer(
                    text="Puro Chile RP - Sistema de Radios",
                    icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

                # Eliminar mensaje original
                try:
                    await ctx.message.delete()
                except:
                    pass

                # Enviar confirmación
                confirmation_msg = await ctx.send(embed=embed)

                # Iniciar tarea de limpieza si no está corriendo
                if not self.cleanup_task_running:
                    self.cleanup_inactive_radios.start()
                    self.cleanup_task_running = True

                # Eliminar mensaje de confirmación después de 30 segundos
                await asyncio.sleep(30)
                try:
                    await confirmation_msg.delete()
                except:
                    pass

            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error creando radio",
                    description=f"No se pudo crear la radio: {str(e)}",
                    color=discord.Color.red())
                await ctx.send(embed=embed, delete_after=15)

        @self.bot.command(name='cerrar-radio')
        @is_authorized()
        async def close_radio_command(ctx):
            """Cerrar manualmente la radio del usuario"""

            if ctx.author.id not in self.active_radios:
                embed = discord.Embed(
                    title="❌ Sin radio activa",
                    description="No tienes ninguna radio activa.",
                    color=discord.Color.red())
                await ctx.send(embed=embed, delete_after=10)
                return

            try:
                radio_info = self.active_radios[ctx.author.id]
                channel = radio_info['channel']

                # Eliminar canal
                await channel.delete()

                # Eliminar del registro
                del self.active_radios[ctx.author.id]

                embed = discord.Embed(
                    title="📻 Radio cerrada",
                    description="Tu radio ha sido cerrada exitosamente.",
                    color=discord.Color.green())

                # Eliminar mensaje original
                try:
                    await ctx.message.delete()
                except:
                    pass

                await ctx.send(embed=embed, delete_after=10)

            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Error al cerrar la radio: {str(e)}",
                    color=discord.Color.red())
                await ctx.send(embed=embed, delete_after=10)

        @self.bot.command(name='radios-activas')
        @is_authorized()
        async def active_radios_command(ctx):
            """Ver radios activas"""

            if not self.active_radios:
                embed = discord.Embed(
                    title="📻 Sin radios activas",
                    description="No hay radios activas en este momento.",
                    color=discord.Color.blue())
                await ctx.send(embed=embed, delete_after=15)
                return

            embed = discord.Embed(
                title="📻 Radios Activas",
                description=f"Hay {len(self.active_radios)} radio(s) activa(s)",
                color=discord.Color.blue(),
                timestamp=datetime.now())

            for user_id, radio_info in self.active_radios.items():
                user = self.bot.get_user(user_id)
                channel = radio_info['channel']
                created_at = radio_info['created_at']
                members_count = len(radio_info['members'])

                time_active = datetime.now() - created_at
                hours, remainder = divmod(time_active.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)

                embed.add_field(
                    name=f"📻 {channel.name}",
                    value=
                    f"**Creador:** {user.display_name if user else 'Desconocido'}\n"
                    f"**Miembros:** {members_count}\n"
                    f"**Conectados:** {len(channel.members)}\n"
                    f"**Tiempo activo:** {int(hours)}h {int(minutes)}m",
                    inline=True)

            embed.set_footer(
                text="Puro Chile RP - Sistema de Radios",
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

            await ctx.send(embed=embed, delete_after=60)

    @tasks.loop(minutes=1)
    async def cleanup_inactive_radios(self):
        """Limpiar radios inactivas cada minuto"""
        try:
            to_remove = []

            for user_id, radio_info in self.active_radios.items():
                channel = radio_info['channel']

                # Verificar si el canal existe
                try:
                    await channel.fetch()
                except discord.NotFound:
                    # El canal ya no existe
                    to_remove.append(user_id)
                    continue

                # Verificar si hay miembros conectados
                if len(channel.members) == 0:
                    # Canal vacío por más de 10 minutos
                    inactive_time = datetime.now() - radio_info.get(
                        'last_activity', radio_info['created_at'])

                    if inactive_time.total_seconds() >= 600:  # 10 minutos
                        try:
                            await channel.delete()
                            to_remove.append(user_id)
                            print(
                                f"📻 Radio eliminada por inactividad: {channel.name}"
                            )
                        except Exception as e:
                            print(f"Error eliminando radio inactiva: {e}")
                else:
                    # Actualizar última actividad
                    radio_info['last_activity'] = datetime.now()

            # Remover radios eliminadas del registro
            for user_id in to_remove:
                if user_id in self.active_radios:
                    del self.active_radios[user_id]

            # Detener la tarea si no hay radios activas
            if not self.active_radios:
                self.cleanup_inactive_radios.cancel()
                self.cleanup_task_running = False
                print(
                    "📻 Tarea de limpieza de radios detenida - no hay radios activas"
                )

        except Exception as e:
            print(f"Error en limpieza de radios: {e}")

    @cleanup_inactive_radios.before_loop
    async def before_cleanup(self):
        """Esperar hasta que el bot esté listo"""
        await self.bot.wait_until_ready()

    def stop_cleanup(self):
        """Detener la tarea de limpieza"""
        if self.cleanup_inactive_radios.is_running():
            self.cleanup_inactive_radios.cancel()
            self.cleanup_task_running = False

class RadioView(discord.ui.View):
    def __init__(self, creator_id, radio_name, voice_channel):
        super().__init__(timeout=None)  # Persistent view
        self.creator_id = creator_id
        self.radio_name = radio_name
        self.voice_channel = voice_channel

    @discord.ui.button(label='🔒 Cerrar Radio', style=discord.ButtonStyle.danger, custom_id='close_radio')
    async def close_radio(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cerrar manualmente la radio del usuario"""

        # Verificar si el usuario que interactúa es el creador de la radio
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message("Solo el creador de la radio puede cerrarla.", ephemeral=True)
            return

        try:
            # Eliminar canal de voz
            await self.voice_channel.delete()

            # Responder a la interacción
            await interaction.response.send_message("Radio cerrada exitosamente.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Error al cerrar la radio: {str(e)}", ephemeral=True)