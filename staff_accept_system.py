import discord
from discord.ext import commands
from datetime import datetime
from utils.embeds import create_error_embed, create_success_embed

class StaffAcceptSystem:
    def __init__(self, bot):
        self.bot = bot
        self.staff_roles = [
            1365480205648396320,
            1365481317545808003,
            1221496580763418650,
            1221496580620816473,
            1221498803018797257
        ]
        self.setup_commands()
        
    def setup_commands(self):
        """Setup staff accept system commands"""
        
        @self.bot.command(name='aceptar')
        @commands.has_permissions(administrator=True)
        async def accept_staff(ctx, user: discord.Member):
            """Comando para aceptar a un usuario al equipo de staff"""
            try:
                # Get roles to assign
                roles_to_add = []
                for role_id in self.staff_roles:
                    role = ctx.guild.get_role(role_id)
                    if role:
                        roles_to_add.append(role)
                
                if not roles_to_add:
                    embed = create_error_embed(
                        "❌ Error de configuración",
                        "No se pudieron encontrar los roles de staff."
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Add roles to user
                await user.add_roles(*roles_to_add, reason=f"Aceptado al staff por {ctx.author}")
                
                # Send DM to user
                try:
                    dm_embed = discord.Embed(
                        title="🎉 ¡Felicidades! Has sido aceptado al Staff",
                        description=f"Has sido aceptado al equipo de staff de **Puro Chile RP** por {ctx.author.mention}",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    
                    dm_embed.add_field(
                        name="👮‍♂️ Administrador Responsable",
                        value=f"{ctx.author.mention}\n`{ctx.author.display_name}`",
                        inline=True
                    )
                    
                    dm_embed.add_field(
                        name="📋 Próximos Pasos",
                        value="Cualquier duda acude al chat de staff correspondiente.",
                        inline=False
                    )
                    
                    dm_embed.set_footer(text="Puro Chile RP - Bienvenido al Staff")
                    dm_embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
                    
                    await user.send(embed=dm_embed)
                    dm_sent = True
                except discord.Forbidden:
                    dm_sent = False
                
                # Send confirmation in channel
                embed = discord.Embed(
                    title="✅ Usuario Aceptado al Staff",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="👤 Nuevo Staff Member",
                    value=f"{user.mention}\n`{user.display_name}`",
                    inline=True
                )
                
                embed.add_field(
                    name="👮‍♂️ Aceptado por",
                    value=f"{ctx.author.mention}\n`{ctx.author.display_name}`",
                    inline=True
                )
                
                embed.add_field(
                    name="🎭 Roles Asignados",
                    value=f"**{len(roles_to_add)}** roles de staff",
                    inline=True
                )
                
                if dm_sent:
                    embed.add_field(
                        name="📩 Notificación",
                        value="✅ DM enviado exitosamente",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📩 Notificación",
                        value="❌ No se pudo enviar DM (DMs cerrados)",
                        inline=False
                    )
                
                embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
                embed.set_footer(
                    text="Puro Chile RP - Sistema de Staff",
                    icon_url=ctx.guild.icon.url if ctx.guild.icon else None
                )
                
                await ctx.send(embed=embed)
                
            except commands.MemberNotFound:
                embed = create_error_embed(
                    "❌ Usuario no encontrado",
                    "No se pudo encontrar al usuario mencionado."
                )
                await ctx.send(embed=embed)
            except Exception as e:
                print(f"Error en aceptar: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al procesar la aceptación."
                )
                await ctx.send(embed=embed)
        
        @accept_staff.error
        async def accept_staff_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ No tienes permisos de administrador para usar este comando.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("❌ Debes mencionar al usuario a aceptar. Uso: `pc!aceptar @usuario`")