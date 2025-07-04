import discord
from discord.ext import commands
from datetime import datetime
import json
import os
from utils.embeds import create_error_embed, create_success_embed, create_info_embed

class WarningSystem:
    def __init__(self, bot):
        self.bot = bot
        self.staff_role_id = 1221496580620816473
        self.setup_commands()
        
    def setup_commands(self):
        """Setup warning system commands"""
        
        def is_staff():
            """Check if user has staff role"""
            def predicate(ctx):
                return any(role.id == self.staff_role_id for role in ctx.author.roles)
            return predicate
        
        @self.bot.command(name='advertir')
        async def warn_user(ctx, user: discord.Member, *, motivo: str):
            """Comando para agregar advertencias a un usuario"""
            try:
                # Check if user has staff role
                if not any(role.id == self.staff_role_id for role in ctx.author.roles):
                    embed = discord.Embed(
                        title="❌ Sin Permisos",
                        description="No tienes permisos para usar este comando.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Verificar que el motivo no esté vacío
                if len(motivo.strip()) < 3:
                    embed = discord.Embed(
                        title="❌ Motivo muy corto",
                        description="El motivo debe tener al menos 3 caracteres.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Cargar advertencias existentes
                warnings = await self.load_warnings()
                
                # Obtener advertencias del usuario
                user_warnings = warnings.get(str(user.id), [])
                
                # Crear nueva advertencia
                warning_data = {
                    "id": len(user_warnings) + 1,
                    "motivo": motivo,
                    "staff": ctx.author.id,
                    "fecha": datetime.utcnow().isoformat()
                }
                
                user_warnings.append(warning_data)
                warnings[str(user.id)] = user_warnings
                
                # Guardar advertencias
                await self.save_warnings(warnings)
                
                # Crear embed decorativo
                embed = discord.Embed(
                    title="⚠️ Sistema de Advertencias",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="👤 Usuario Advertido",
                    value=f"{user.mention}\n`{user.display_name}`",
                    inline=True
                )
                
                embed.add_field(
                    name="🆔 ID de Advertencia",
                    value=f"**#{warning_data['id']}**",
                    inline=True
                )
                
                embed.add_field(
                    name="👮‍♂️ Staff Responsable",
                    value=f"{ctx.author.mention}\n`{ctx.author.display_name}`",
                    inline=True
                )
                
                embed.add_field(
                    name="📝 Motivo de la Advertencia",
                    value=f"```{motivo}```",
                    inline=False
                )
                
                embed.add_field(
                    name="📊 Total de Advertencias",
                    value=f"**{len(user_warnings)}** advertencia(s)",
                    inline=True
                )
                
                embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
                embed.set_footer(
                    text="Puro Chile RP - Sistema de Advertencias",
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
                print(f"Error en advertir: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al procesar la advertencia."
                )
                await ctx.send(embed=embed)
        
        @self.bot.command(name='sacaradvertencia')
        async def remove_warning(ctx, user: discord.Member, warning_id: int):
            """Comando para eliminar una advertencia específica"""
            try:
                # Check if user has staff role
                if not any(role.id == self.staff_role_id for role in ctx.author.roles):
                    embed = discord.Embed(
                        title="❌ Sin Permisos",
                        description="No tienes permisos para usar este comando.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                
                warnings = await self.load_warnings()
                user_warnings = warnings.get(str(user.id), [])
                
                if not user_warnings:
                    embed = discord.Embed(
                        title="❌ Sin Advertencias",
                        description=f"{user.mention} no tiene advertencias registradas.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Find and remove the warning
                warning_to_remove = None
                for warning in user_warnings:
                    if warning["id"] == warning_id:
                        warning_to_remove = warning
                        break
                
                if not warning_to_remove:
                    embed = discord.Embed(
                        title="❌ Advertencia No Encontrada",
                        description=f"No se encontró una advertencia con ID **#{warning_id}** para {user.mention}.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Remove the warning
                user_warnings.remove(warning_to_remove)
                warnings[str(user.id)] = user_warnings
                await self.save_warnings(warnings)
                
                # Create success embed
                embed = discord.Embed(
                    title="✅ Advertencia Eliminada",
                    description=f"Se eliminó la advertencia **#{warning_id}** de {user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                
                embed.add_field(
                    name="📝 Motivo Eliminado",
                    value=warning_to_remove["motivo"],
                    inline=False
                )
                
                embed.add_field(
                    name="👤 Staff",
                    value=f"<@{ctx.author.id}>",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 Advertencias Restantes",
                    value=f"**{len(user_warnings)}** advertencia(s)",
                    inline=True
                )
                
                embed.set_footer(text="Puro Chile RP - Sistema de Advertencias", 
                               icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Hubo un error al eliminar la advertencia.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                print(f"Error removing warning: {e}")

        @self.bot.command(name='veradvertencias')
        async def view_warnings(ctx, user: discord.Member):
            """Comando para ver todas las advertencias de un usuario"""
            try:
                # Check if user has staff role
                if not any(role.id == self.staff_role_id for role in ctx.author.roles):
                    embed = discord.Embed(
                        title="❌ Sin Permisos",
                        description="No tienes permisos para usar este comando.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return
                
                warnings = await self.load_warnings()
                user_warnings = warnings.get(str(user.id), [])
                
                if not user_warnings:
                    embed = create_info_embed(
                        "📋 Sin Advertencias",
                        f"{user.mention} no tiene advertencias registradas."
                    )
                    await ctx.send(embed=embed)
                    return
                
                # Crear embed principal
                embed = discord.Embed(
                    title="📋 Historial de Advertencias",
                    description=f"**Usuario:** {user.mention} (`{user.display_name}`)\n**Total:** {len(user_warnings)} advertencia(s)",
                    color=discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                
                # Agregar cada advertencia
                for warning in user_warnings[-5:]:  # Mostrar últimas 5
                    # Determinar si es automática o manual
                    is_automatic = warning.get('auto_generated', False)
                    
                    if is_automatic:
                        staff_mention = f"<@{self.bot.user.id}> (Sistema Automático)"
                        staff_name = "Sistema Automático"
                    else:
                        staff_user = self.bot.get_user(warning['staff'])
                        staff_name = staff_user.display_name if staff_user else "Usuario desconocido"
                        staff_mention = f"<@{warning['staff']}>"
                    
                    fecha = datetime.fromisoformat(warning['fecha']).strftime("%d/%m/%Y %H:%M")
                    
                    embed.add_field(
                        name=f"⚠️ Advertencia #{warning['id']}",
                        value=f"**Staff:** {staff_mention}\n**Fecha:** {fecha}\n**Motivo:** {warning['motivo']}",
                        inline=False
                    )
                
                if len(user_warnings) > 5:
                    embed.set_footer(text=f"Mostrando las últimas 5 de {len(user_warnings)} advertencias totales")
                else:
                    embed.set_footer(text="Puro Chile RP - Sistema de Advertencias")
                
                embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                print(f"Error en veradvertencias: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al obtener las advertencias."
                )
                await ctx.send(embed=embed)
        
        @warn_user.error
        @view_warnings.error
        async def warning_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("❌ No tienes permisos para usar este comando.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("❌ Faltan argumentos requeridos.")
    
    async def load_warnings(self):
        """Load warnings from JSON file"""
        try:
            if os.path.exists('data/warnings.json'):
                with open('data/warnings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading warnings: {e}")
            return {}
    
    async def save_warnings(self, warnings):
        """Save warnings to JSON file"""
        try:
            os.makedirs('data', exist_ok=True)
            with open('data/warnings.json', 'w', encoding='utf-8') as f:
                json.dump(warnings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving warnings: {e}")