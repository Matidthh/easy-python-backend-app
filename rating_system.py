import asyncio
import asyncpg
import discord
from discord.ext import commands
from datetime import datetime
import os
from utils.embeds import create_error_embed, create_success_embed, create_info_embed


class RatingSystem:

    def __init__(self, bot):
        self.bot = bot
        self.staff_role_id = 1221496580620816473
        self.setup_commands()

    def setup_commands(self):
        """Setup rating system commands"""

        @self.bot.command(name='calificar')
        async def rate_staff(ctx, member: discord.Member, rating_str: str, *,
                             motivo: str):
            """Comando para calificar a un miembro del staff"""
            try:
                # Convertir la calificación de string a int
                try:
                    rating = int(rating_str)
                except ValueError:
                    embed = create_error_embed(
                        "❌ Calificación inválida",
                        "La calificación debe ser un número entero entre -5 y 5."
                    )
                    await ctx.send(embed=embed)
                    return

                # Verificar que el usuario a calificar tenga el rol de staff
                staff_role = discord.utils.get(member.roles,
                                               id=self.staff_role_id)
                if not staff_role:
                    embed = create_error_embed(
                        "❌ Error",
                        f"{member.mention} no es miembro del staff y no puede ser calificado."
                    )
                    await ctx.send(embed=embed)
                    return

                # Verificar que la calificación esté en el rango válido
                if rating < -5 or rating > 5:
                    embed = create_error_embed(
                        "❌ Calificación inválida",
                        "La calificación debe estar entre -5 y 5 puntos.")
                    await ctx.send(embed=embed)
                    return

                # Verificar que el motivo no esté vacío
                if len(motivo.strip()) < 5:
                    embed = create_error_embed(
                        "❌ Motivo requerido",
                        "Debes proporcionar un motivo de al menos 5 caracteres."
                    )
                    await ctx.send(embed=embed)
                    return

                # Verificar que no se esté autocalificando
                if ctx.author.id == member.id:
                    embed = create_error_embed(
                        "❌ Error", "No puedes calificarte a ti mismo.")
                    await ctx.send(embed=embed)
                    return

                # Guardar la calificación en la base de datos
                await self.save_rating(ctx.author.id, member.id, rating,
                                       motivo)

                # Respuesta de confirmación con formato decorativo
                rating_color = discord.Color.green(
                ) if rating > 0 else discord.Color.orange(
                ) if rating == 0 else discord.Color.red()
                rating_emoji = "⭐" if rating > 0 else "⚠️" if rating == 0 else "❌"

                embed = discord.Embed(title="📊 Sistema de Calificaciones",
                                      color=rating_color,
                                      timestamp=datetime.utcnow())

                embed.add_field(
                    name="👤 Staff Calificado",
                    value=f"{member.mention}\n`{member.display_name}`",
                    inline=True)

                embed.add_field(name="⭐ Puntuación Otorgada",
                                value=f"**{rating:+d} puntos** {rating_emoji}",
                                inline=True)

                embed.add_field(
                    name="📝 Calificado por",
                    value=f"{ctx.author.mention}\n`{ctx.author.display_name}`",
                    inline=True)

                embed.add_field(name="💬 Motivo de la Calificación",
                                value=f"```{motivo}```",
                                inline=False)

                embed.set_thumbnail(url=member.avatar.url if member.
                                    avatar else member.default_avatar.url)
                embed.set_footer(
                    text="Puro Chile RP - Sistema de Calificaciones",
                    icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

                await ctx.send(embed=embed)

            except commands.MemberNotFound:
                embed = create_error_embed(
                    "❌ Usuario no encontrado",
                    "No se pudo encontrar al usuario mencionado.")
                await ctx.send(embed=embed)
            except Exception as e:
                print(f"Error en calificar: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al procesar la calificación. Inténtalo de nuevo."
                )
                await ctx.send(embed=embed)

        @self.bot.command(name='vercalificaciones')
        async def view_ratings(ctx, member: discord.Member = None):
            """Comando para ver las calificaciones de un miembro del staff"""
            target_member = member if member is not None else ctx.author

            try:
                # Verificar que el usuario tenga el rol de staff
                staff_role = discord.utils.get(target_member.roles,
                                               id=self.staff_role_id)
                if not staff_role:
                    embed = create_error_embed(
                        "❌ Error",
                        f"{target_member.mention} no es miembro del staff.")
                    await ctx.send(embed=embed)
                    return

                # Obtener estadísticas de calificaciones
                stats = await self.get_rating_stats(target_member.id)
                recent_ratings = await self.get_recent_ratings(
                    target_member.id, limit=3)

                # Crear embed con la información
                total_score = stats['total_score'] or 0
                total_ratings = stats['total_ratings'] or 0
                avg_rating = round(total_score / total_ratings,
                                   2) if total_ratings > 0 else 0

                # Determinar color basado en la puntuación
                if total_score > 10:
                    color = discord.Color.green()
                elif total_score > 0:
                    color = discord.Color.blue()
                elif total_score == 0:
                    color = discord.Color.light_grey()
                else:
                    color = discord.Color.red()

                embed = discord.Embed(
                    title=f"📊 Calificaciones de {target_member.display_name}",
                    color=color,
                    timestamp=datetime.utcnow())

                embed.set_thumbnail(
                    url=target_member.avatar.url if target_member.
                    avatar else target_member.default_avatar.url)

                embed.add_field(name="📈 Puntuación Total",
                                value=f"**{total_score:+d}** puntos",
                                inline=True)

                embed.add_field(name="🔢 Total de Valoraciones",
                                value=f"**{total_ratings}** calificaciones",
                                inline=True)

                embed.add_field(
                    name="📊 Promedio",
                    value=f"**{avg_rating:+.2f}** por calificación",
                    inline=True)

                # Agregar últimas 3 calificaciones si existen
                if recent_ratings:
                    ratings_text = ""
                    for rating_data in recent_ratings:
                        rater = self.bot.get_user(rating_data['rater_id'])
                        rater_name = rater.display_name if rater else "Usuario desconocido"
                        rating_value = rating_data['rating']
                        motivo = rating_data['reason'][:50] + "..." if len(
                            rating_data['reason']
                        ) > 50 else rating_data['reason']

                        emoji = "⭐" if rating_value > 0 else "⚠️" if rating_value == 0 else "❌"
                        ratings_text += f"{emoji} **{rating_value:+d}** por {rater_name}\n*{motivo}*\n\n"

                    embed.add_field(name="🕒 Últimas 3 Calificaciones",
                                    value=ratings_text
                                    or "No hay calificaciones recientes",
                                    inline=False)

                await ctx.send(embed=embed)

            except Exception as e:
                print(f"Error en vercalificaciones: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al obtener las calificaciones.")
                await ctx.send(embed=embed)

        @self.bot.command(name='topcalificaciones')
        async def top_ratings(ctx):
            """Comando para ver el ranking de staff mejor calificado"""
            try:
                # Obtener top 10 staff mejor calificados
                top_staff = await self.get_top_staff(limit=10)

                if not top_staff:
                    embed = create_info_embed(
                        "📊 Ranking de Staff",
                        "Aún no hay calificaciones registradas.")
                    await ctx.send(embed=embed)
                    return

                embed = discord.Embed(
                    title="🏆 Top Staff - Ranking de Calificaciones",
                    description=
                    "Los miembros del staff mejor valorados por la comunidad",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow())

                ranking_text = ""
                medals = [
                    "🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣",
                    "🔟"
                ]

                for i, staff_data in enumerate(top_staff):
                    user = self.bot.get_user(staff_data['staff_id'])
                    if user:
                        medal = medals[i] if i < len(medals) else f"{i+1}."
                        total_score = staff_data['total_score']
                        total_ratings = staff_data['total_ratings']
                        avg_rating = round(total_score / total_ratings,
                                           2) if total_ratings > 0 else 0

                        ranking_text += f"{medal} **{user.display_name}**\n"
                        ranking_text += f"   📈 {total_score:+d} puntos | 🔢 {total_ratings} valoraciones | 📊 {avg_rating:+.2f} promedio\n\n"

                embed.add_field(name="🏅 Ranking Actual",
                                value=ranking_text,
                                inline=False)

                embed.set_footer(
                    text=
                    "💡 Usa pc!calificar para valorar a un miembro del staff")

                await ctx.send(embed=embed)

            except Exception as e:
                print(f"Error en topcalificaciones: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al obtener el ranking.")
                await ctx.send(embed=embed)

    async def get_db_connection(self):
        """Get database connection"""
        return await asyncpg.connect(os.environ.get('DATABASE_URL'))

    async def init_database(self):
        """Initialize database tables"""
        conn = await self.get_db_connection()
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS staff_ratings (
                    id SERIAL PRIMARY KEY,
                    staff_id BIGINT NOT NULL,
                    rater_id BIGINT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= -5 AND rating <= 5),
                    reason TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Crear índices para mejorar el rendimiento
            await conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_staff_ratings_staff_id ON staff_ratings(staff_id)'
            )
            await conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_staff_ratings_created_at ON staff_ratings(created_at)'
            )

        finally:
            await conn.close()

    async def save_rating(self, rater_id, staff_id, rating, reason):
        """Save a rating to the database"""
        conn = await self.get_db_connection()
        try:
            await conn.execute(
                '''
                INSERT INTO staff_ratings (staff_id, rater_id, rating, reason)
                VALUES ($1, $2, $3, $4)
            ''', staff_id, rater_id, rating, reason)
        finally:
            await conn.close()

    async def get_rating_stats(self, staff_id):
        """Get rating statistics for a staff member"""
        conn = await self.get_db_connection()
        try:
            result = await conn.fetchrow(
                '''
                SELECT 
                    COALESCE(SUM(rating), 0) as total_score,
                    COUNT(*) as total_ratings
                FROM staff_ratings 
                WHERE staff_id = $1
            ''', staff_id)
            return dict(result) if result else {
                'total_score': 0,
                'total_ratings': 0
            }
        finally:
            await conn.close()

    async def get_recent_ratings(self, staff_id, limit=3):
        """Get recent ratings for a staff member"""
        conn = await self.get_db_connection()
        try:
            results = await conn.fetch(
                '''
                SELECT rater_id, rating, reason, created_at
                FROM staff_ratings 
                WHERE staff_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ''', staff_id, limit)
            return [dict(row) for row in results]
        finally:
            await conn.close()

    async def get_top_staff(self, limit=10):
        """Get top rated staff members"""
        conn = await self.get_db_connection()
        try:
            results = await conn.fetch(
                '''
                SELECT 
                    staff_id,
                    SUM(rating) as total_score,
                    COUNT(*) as total_ratings,
                    AVG(rating::DECIMAL) as avg_rating
                FROM staff_ratings 
                GROUP BY staff_id 
                HAVING COUNT(*) > 0
                ORDER BY total_score DESC, total_ratings DESC
                LIMIT $1
            ''', limit)
            return [dict(row) for row in results]
        finally:
            await conn.close()
