import discord
from discord.ext import commands
import json
import os
from datetime import datetime

class WarnSystem:
    def __init__(self, bot):
        self.bot = bot
        self.setup_commands()
    
    def setup_commands(self):
        """Setup warn system commands"""
        
        def is_staff():
            """Check if user has staff role"""
            def predicate(ctx):
                staff_role_id = 1221496580620816473
                return any(role.id == staff_role_id for role in ctx.author.roles)
            return commands.check(predicate)
        
        @self.bot.command(name='sancionar')
        @is_staff()
        async def warn_user(ctx, user: discord.Member, *, motivo: str):
            """Comando para agregar warns a un usuario"""
            if not motivo:
                await ctx.send("❌ Debes proporcionar un motivo para la sanción.")
                return
            
            # Load existing warns
            warns = await self.load_warns()
            
            # Create warn entry
            warn_entry = {
                "id": len(warns) + 1,
                "user_id": user.id,
                "username": str(user),
                "staff_id": ctx.author.id,
                "staff_username": str(ctx.author),
                "motivo": motivo,
                "timestamp": datetime.now().isoformat(),
                "guild_id": ctx.guild.id
            }
            
            # Add warn
            warns.append(warn_entry)
            
            # Save warns
            await self.save_warns(warns)
            
            # Count user's warns
            user_warns = [w for w in warns if w['user_id'] == user.id and w['guild_id'] == ctx.guild.id]
            warn_count = len(user_warns)
            
            # Create embed
            embed = discord.Embed(
                title="⚠️ Usuario Sancionado",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Usuario",
                value=f"{user.mention} ({user.display_name})",
                inline=True
            )
            
            embed.add_field(
                name="👮 Staff",
                value=f"{ctx.author.mention} ({ctx.author.display_name})",
                inline=True
            )
            
            embed.add_field(
                name="🔢 Warns Totales",
                value=f"{warn_count}/5",
                inline=True
            )
            
            embed.add_field(
                name="📝 Motivo",
                value=motivo,
                inline=False
            )
            
            embed.add_field(
                name="🆔 ID de Warn",
                value=f"`{warn_entry['id']}`",
                inline=True
            )
            
            # Warning if close to limit
            if warn_count >= 5:
                embed.add_field(
                    name="🚨 LÍMITE ALCANZADO",
                    value="Este usuario ha alcanzado el máximo de 5 warns.",
                    inline=False
                )
                embed.color = discord.Color.red()
            elif warn_count >= 4:
                embed.add_field(
                    name="⚠️ ADVERTENCIA",
                    value="Este usuario está cerca del límite de warns.",
                    inline=False
                )
            
            embed.set_footer(text=f"Servidor: {ctx.guild.name}")
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='verwarns')
        async def view_warns(ctx, user: discord.Member):
            """Comando para ver todos los warns de un usuario"""
            warns = await self.load_warns()
            user_warns = [w for w in warns if w['user_id'] == user.id and w['guild_id'] == ctx.guild.id]
            
            if not user_warns:
                embed = discord.Embed(
                    title="📋 Historial de Warns",
                    description=f"{user.mention} no tiene warns activos.",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=user.display_avatar.url)
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📋 Historial de Warns",
                description=f"Warns de {user.mention} ({len(user_warns)}/5)",
                color=discord.Color.orange() if len(user_warns) < 5 else discord.Color.red(),
                timestamp=datetime.now()
            )
            
            for i, warn in enumerate(user_warns[-10:], 1):  # Show last 10 warns
                embed.add_field(
                    name=f"⚠️ Warn #{warn['id']}",
                    value=f"**Staff:** {warn['staff_username']}\n"
                          f"**Motivo:** {warn['motivo']}\n"
                          f"**Fecha:** {datetime.fromisoformat(warn['timestamp']).strftime('%d/%m/%Y %H:%M')}",
                    inline=False
                )
            
            if len(user_warns) > 10:
                embed.add_field(
                    name="ℹ️ Información",
                    value=f"Mostrando los últimos 10 warns de {len(user_warns)} totales.",
                    inline=False
                )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Servidor: {ctx.guild.name}")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='removewarn')
        @is_staff()
        async def remove_warn(ctx, user: discord.Member, warn_id: int):
            """Comando para eliminar un warn específico"""
            warns = await self.load_warns()
            
            # Find the warn
            warn_to_remove = None
            for i, warn in enumerate(warns):
                if warn['id'] == warn_id and warn['user_id'] == user.id and warn['guild_id'] == ctx.guild.id:
                    warn_to_remove = warns.pop(i)
                    break
            
            if not warn_to_remove:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"No se encontró el warn #{warn_id} para {user.mention}.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            # Save updated warns
            await self.save_warns(warns)
            
            # Count remaining warns
            remaining_warns = len([w for w in warns if w['user_id'] == user.id and w['guild_id'] == ctx.guild.id])
            
            embed = discord.Embed(
                title="✅ Warn Eliminado",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Usuario",
                value=f"{user.mention} ({user.display_name})",
                inline=True
            )
            
            embed.add_field(
                name="👮 Staff",
                value=f"{ctx.author.mention} ({ctx.author.display_name})",
                inline=True
            )
            
            embed.add_field(
                name="🔢 Warns Restantes",
                value=f"{remaining_warns}/5",
                inline=True
            )
            
            embed.add_field(
                name="🆔 Warn Eliminado",
                value=f"#{warn_id}: {warn_to_remove['motivo']}",
                inline=False
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Servidor: {ctx.guild.name}")
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name='resetwarns')
        @is_staff()
        async def reset_warns(ctx, user: discord.Member):
            """Comando para eliminar todos los warns de un usuario"""
            warns = await self.load_warns()
            
            # Count user's warns before removal
            user_warns_count = len([w for w in warns if w['user_id'] == user.id and w['guild_id'] == ctx.guild.id])
            
            if user_warns_count == 0:
                embed = discord.Embed(
                    title="ℹ️ Información",
                    description=f"{user.mention} no tiene warns para eliminar.",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
                return
            
            # Remove all warns for this user in this guild
            warns = [w for w in warns if not (w['user_id'] == user.id and w['guild_id'] == ctx.guild.id)]
            
            # Save updated warns
            await self.save_warns(warns)
            
            embed = discord.Embed(
                title="🧹 Warns Reseteados",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Usuario",
                value=f"{user.mention} ({user.display_name})",
                inline=True
            )
            
            embed.add_field(
                name="👮 Staff",
                value=f"{ctx.author.mention} ({ctx.author.display_name})",
                inline=True
            )
            
            embed.add_field(
                name="🔢 Warns Eliminados",
                value=f"{user_warns_count} warns eliminados",
                inline=True
            )
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Servidor: {ctx.guild.name}")
            
            await ctx.send(embed=embed)
        
        @warn_user.error
        @remove_warn.error
        @reset_warns.error
        async def warn_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                embed = discord.Embed(
                    title="❌ Sin Permisos",
                    description="No tienes permisos para usar este comando.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            elif isinstance(error, commands.MemberNotFound):
                embed = discord.Embed(
                    title="❌ Usuario No Encontrado",
                    description="No se pudo encontrar el usuario mencionado.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            elif isinstance(error, commands.BadArgument):
                embed = discord.Embed(
                    title="❌ Argumento Inválido",
                    description="Verifica que hayas mencionado correctamente al usuario y/o el número de warn.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
    
    async def load_warns(self):
        """Load warns from JSON file"""
        try:
            with open('data/warns.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    async def save_warns(self, warns):
        """Save warns to JSON file"""
        os.makedirs('data', exist_ok=True)
        with open('data/warns.json', 'w') as f:
            json.dump(warns, f, indent=2)