# Adding custom_id to suggestion buttons for persistent views.
import discord
from discord.ext import commands
from datetime import datetime
import json
import os
from utils.embeds import create_error_embed, create_success_embed, create_info_embed

class SuggestionSystem:
    def __init__(self, bot):
        self.bot = bot
        self.suggestion_channel_id = 1284885409830010982
        self.setup_commands()

    def setup_commands(self):
        """Setup suggestion system commands"""

        @self.bot.command(name='sugerencia')
        async def suggestion_command(ctx, *, motivo: str):
            """Comando para enviar sugerencias que serán votadas por la comunidad"""
            try:
                # Verificar que el motivo no esté vacío
                if len(motivo.strip()) < 10:
                    embed = create_error_embed(
                        "❌ Sugerencia muy corta",
                        "La sugerencia debe tener al menos 10 caracteres."
                    )
                    await ctx.send(embed=embed)
                    return

                # Obtener el canal de sugerencias
                suggestion_channel = self.bot.get_channel(self.suggestion_channel_id)
                if not suggestion_channel:
                    embed = create_error_embed(
                        "❌ Error de configuración",
                        "No se pudo encontrar el canal de sugerencias."
                    )
                    await ctx.send(embed=embed)
                    return

                # Crear embed de sugerencia
                embed = discord.Embed(
                    title="💡 Nueva Sugerencia",
                    description=f"**Sugerencia:**\n{motivo}",
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )

                embed.add_field(
                    name="👤 Autor",
                    value=ctx.author.mention,
                    inline=True
                )

                embed.add_field(
                    name="✅ Votos a Favor",
                    value="0",
                    inline=True
                )

                embed.add_field(
                    name="❌ Votos en Contra",
                    value="0",
                    inline=True
                )

                embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                embed.set_footer(text="Puro Chile RP - Sistema de Sugerencias")

                # Crear vista con botones de votación
                view = SuggestionVotingView(ctx.author.id)

                # Enviar la sugerencia al canal
                message = await suggestion_channel.send(embed=embed, view=view)

                # Guardar la sugerencia en los datos
                await self.save_suggestion(ctx.author.id, motivo, message.id)

                # Confirmar al usuario
                embed_confirmation = create_success_embed(
                    "✅ Sugerencia enviada",
                    f"Tu sugerencia ha sido enviada al canal de sugerencias.\n"
                    f"La comunidad podrá votarla en {suggestion_channel.mention}"
                )
                await ctx.send(embed=embed_confirmation)

            except Exception as e:
                print(f"Error en sugerencia: {e}")
                embed = create_error_embed(
                    "❌ Error del sistema",
                    "Ocurrió un error al procesar la sugerencia. Inténtalo de nuevo."
                )
                await ctx.send(embed=embed)

    async def save_suggestion(self, user_id, content, message_id):
        """Save suggestion to file"""
        try:
            suggestion_data = {
                "user_id": user_id,
                "content": content,
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "votes_for": [],
                "votes_against": []
            }

            # Load existing suggestions
            suggestions_file = 'data/suggestions.json'
            if os.path.exists(suggestions_file):
                with open(suggestions_file, 'r', encoding='utf-8') as f:
                    suggestions = json.load(f)
            else:
                suggestions = []

            suggestions.append(suggestion_data)

            # Save back to file
            with open(suggestions_file, 'w', encoding='utf-8') as f:
                json.dump(suggestions, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving suggestion: {e}")

class SuggestionVotingView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=None)  # Persistent view
        self.author_id = author_id

    @discord.ui.button(label="✅ Votar Sugerencia", style=discord.ButtonStyle.green, custom_id="vote_for")
    async def vote_for_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to vote in favor of the suggestion"""
        await self.handle_vote(interaction, "for")

    @discord.ui.button(label="❌ Rechazar Sugerencia", style=discord.ButtonStyle.red, custom_id="vote_against")
    async def vote_against_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to vote against the suggestion"""
        await self.handle_vote(interaction, "against")

    async def handle_vote(self, interaction: discord.Interaction, vote_type):
        """Handle voting logic"""
        try:
            # Prevent author from voting on their own suggestion
            if interaction.user.id == self.author_id:
                embed = create_error_embed(
                    "❌ No permitido",
                    "No puedes votar en tu propia sugerencia."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Load suggestions data
            suggestions_file = 'data/suggestions.json'
            if not os.path.exists(suggestions_file):
                await interaction.response.send_message("❌ Error: No se encontraron datos de sugerencias.", ephemeral=True)
                return

            with open(suggestions_file, 'r', encoding='utf-8') as f:
                suggestions = json.load(f)

            # Find the suggestion by message ID
            suggestion = None
            suggestion_index = None
            message_id = interaction.message.id if interaction.message else None
            if not message_id:
                await interaction.response.send_message("❌ Error: No se pudo obtener el ID del mensaje.", ephemeral=True)
                return

            for i, sug in enumerate(suggestions):
                if sug.get('message_id') == message_id:
                    suggestion = sug
                    suggestion_index = i
                    break

            if not suggestion:
                await interaction.response.send_message("❌ Error: No se encontró la sugerencia.", ephemeral=True)
                return

            user_id = interaction.user.id
            votes_for = suggestion.get('votes_for', [])
            votes_against = suggestion.get('votes_against', [])

            # Remove user from both lists first (change vote)
            if user_id in votes_for:
                votes_for.remove(user_id)
            if user_id in votes_against:
                votes_against.remove(user_id)

            # Add vote to appropriate list
            if vote_type == "for":
                votes_for.append(user_id)
                action = "apoyado"
            else:
                votes_against.append(user_id)
                action = "rechazado"

            # Update suggestion data
            suggestions[suggestion_index]['votes_for'] = votes_for
            suggestions[suggestion_index]['votes_against'] = votes_against

            # Save updated data
            with open(suggestions_file, 'w', encoding='utf-8') as f:
                json.dump(suggestions, f, indent=2, ensure_ascii=False)

            # Update the embed
            if not interaction.message or not interaction.message.embeds:
                await interaction.response.send_message("❌ Error: No se pudo obtener el embed del mensaje.", ephemeral=True)
                return
            embed = interaction.message.embeds[0]

            # Update vote counts in embed fields
            for i, field in enumerate(embed.fields):
                if field.name == "✅ Votos a Favor":
                    embed.set_field_at(i, name="✅ Votos a Favor", value=str(len(votes_for)), inline=True)
                elif field.name == "❌ Votos en Contra":
                    embed.set_field_at(i, name="❌ Votos en Contra", value=str(len(votes_against)), inline=True)

            # Update the message
            await interaction.response.edit_message(embed=embed, view=self)

            # Send confirmation
            await interaction.followup.send(f"✅ Has {action} esta sugerencia.", ephemeral=True)

        except Exception as e:
            print(f"Error handling vote: {e}")
            await interaction.response.send_message("❌ Error al procesar el voto.", ephemeral=True)