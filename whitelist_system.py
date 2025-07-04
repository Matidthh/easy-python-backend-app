import discord
from discord.ext import commands
import json
import os
import asyncio
import aiohttp
from datetime import datetime

# Configuration
WHITELIST_CATEGORY_ID = 1386906933272907816
STAFF_ROLE_ID = 1221496580620816473
RESULTS_CHANNEL_ID = 1221496581828776049

class WhitelistSystem:
    def __init__(self, bot):
        self.bot = bot
        self.user_channels = {}
        self.pending_verifications = {}  # Para almacenar verificaciones pendientes
        self.setup_commands()

    def setup_commands(self):
        """Setup whitelist commands"""
        
        def is_staff():
            def predicate(ctx):
                return any(role.id == STAFF_ROLE_ID for role in ctx.author.roles)
            return commands.check(predicate)

        @self.bot.command(name='whitelist')
        async def whitelist_command(ctx):
            """Comando para crear canal de whitelist con vinculación de Roblox"""
            # Check if user already has completed or is in process of whitelist
            if await self.has_whitelist_history(ctx.author.id):
                await ctx.send(
                    "❌ Ya has completado tu proceso de whitelist anteriormente. Solo se permite una whitelist por usuario."
                )
                return

            # Check if user already has a channel
            if ctx.author.id in self.user_channels:
                await ctx.send("❌ Ya tienes un canal de whitelist activo.")
                return

            # Get the whitelist category
            category = self.bot.get_channel(WHITELIST_CATEGORY_ID)
            if not category:
                await ctx.send("❌ Error: No se encontró la categoría de whitelist.")
                return

            # Get staff role
            staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
            if not staff_role:
                await ctx.send("❌ Error: No se encontró el rol de staff.")
                return

            try:
                # Create private channel
                channel_name = f"whitelist-{ctx.author.name.lower()}"
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                channel = await ctx.guild.create_text_channel(
                    channel_name, category=category, overwrites=overwrites)

                # Store channel mapping
                self.user_channels[ctx.author.id] = channel.id

                # Send confirmation to user
                await ctx.send(f"✅ Canal de whitelist creado: {channel.mention}")

                # Start Roblox verification process
                await self.start_roblox_verification(ctx.author, channel)

            except Exception as e:
                await ctx.send(f"❌ Error al crear el canal: {str(e)}")

        @self.bot.command(name='reset-whitelist')
        @is_staff()
        async def reset_whitelist_command(ctx, user: discord.Member):
            """Comando para resetear completamente la whitelist de un usuario"""
            try:
                # Load user data before deletion for DM
                user_data = None
                if os.path.exists('data/whitelist_applications.json'):
                    with open('data/whitelist_applications.json',
                              'r',
                              encoding='utf-8') as f:
                        applications = json.load(f)
                    
                    # Verificar que applications es un diccionario, no una lista
                    if isinstance(applications, dict):
                        user_data = applications.get(str(user.id))
                    else:
                        # Si es una lista, buscar el usuario en la lista
                        user_data = None
                        for app in applications:
                            if isinstance(app, dict) and app.get('user_id') == str(user.id):
                                user_data = app
                                break

                # Remove from active channels
                channel_deleted = False
                if user.id in self.user_channels:
                    channel_id = self.user_channels[user.id]
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.delete()
                        channel_deleted = True
                    del self.user_channels[user.id]

                # Remove from applications file
                if os.path.exists('data/whitelist_applications.json'):
                    with open('data/whitelist_applications.json',
                              'r',
                              encoding='utf-8') as f:
                        applications = json.load(f)

                    # Remove user's applications
                    if isinstance(applications, dict):
                        # Si es un diccionario (formato correcto)
                        if str(user.id) in applications:
                            del applications[str(user.id)]
                    else:
                        # Si es una lista (formato incorrecto, convertir a diccionario)
                        new_applications = {}
                        for app in applications:
                            if isinstance(app, dict) and app.get('user_id'):
                                if app.get('user_id') != str(user.id):
                                    new_applications[app['user_id']] = app
                        applications = new_applications

                    with open('data/whitelist_applications.json',
                              'w',
                              encoding='utf-8') as f:
                        json.dump(applications,
                                  f,
                                  indent=2,
                                  ensure_ascii=False)

                # Send DM to user with their whitelist information
                await self.send_reset_dm(user, user_data, ctx.author)

                # Log the reset action
                await self.log_whitelist_reset(ctx.guild, user, ctx.author, user_data, channel_deleted)

                # Send confirmation to staff
                embed = discord.Embed(
                    title="🔄 Whitelist Reseteada",
                    description=f"Se ha reseteado completamente la whitelist de {user.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.now())
                
                embed.add_field(
                    name="📧 Notificación",
                    value="Se ha enviado un DM al usuario con la información de su whitelist",
                    inline=False
                )
                
                embed.add_field(
                    name="📋 Registro",
                    value="La acción ha sido registrada en los logs",
                    inline=False
                )
                
                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")

        @reset_whitelist_command.error
        async def reset_whitelist_error(ctx, error):
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ No tienes permisos para usar este comando.")

        @self.bot.command(name='rechazar-whitelist')
        async def restart_whitelist_command(ctx):
            """Comando para reiniciar el proceso de whitelist después de timeout"""
            # Check if user already has completed whitelist
            if await self.has_whitelist_history(ctx.author.id):
                await ctx.send(
                    "❌ Ya has completado tu proceso de whitelist anteriormente. Solo se permite una whitelist por usuario."
                )
                return

            # Check if user already has a channel active
            if ctx.author.id in self.user_channels:
                await ctx.send("❌ Ya tienes un canal de whitelist activo.")
                return

            # Get the whitelist category
            category = self.bot.get_channel(WHITELIST_CATEGORY_ID)
            if not category:
                await ctx.send("❌ Error: No se encontró la categoría de whitelist.")
                return

            # Get staff role
            staff_role = ctx.guild.get_role(STAFF_ROLE_ID)
            if not staff_role:
                await ctx.send("❌ Error: No se encontró el rol de staff.")
                return

            try:
                # Create private channel
                channel_name = f"whitelist-{ctx.author.name.lower()}"
                overwrites = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                channel = await ctx.guild.create_text_channel(
                    channel_name, category=category, overwrites=overwrites)

                # Store channel mapping
                self.user_channels[ctx.author.id] = channel.id

                # Send restart message
                restart_embed = discord.Embed(
                    title="🔄 Whitelist Reiniciada",
                    description=f"**¡Bienvenido de vuelta {ctx.author.mention}!**\n\nSe ha creado un nuevo canal para completar tu proceso de whitelist.",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                restart_embed.add_field(
                    name="📍 Canal Creado",
                    value=f"Dirígete a {channel.mention} para continuar",
                    inline=False
                )
                
                restart_embed.add_field(
                    name="⏰ Recordatorio",
                    value="Tienes **5 minutos** para completar la verificación de Roblox una vez que inicies el proceso.",
                    inline=False
                )
                
                restart_embed.set_footer(text="Puro Chile RP - Sistema de Whitelist")

                await ctx.send(embed=restart_embed)

                # Send welcome message in the new channel
                welcome_embed = discord.Embed(
                    title="🎉 ¡Proceso de Whitelist Reiniciado!",
                    description=f"Hola {ctx.author.mention}, este es tu nuevo canal de whitelist.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                welcome_embed.add_field(
                    name="🚀 ¿Listo para continuar?",
                    value="El proceso de verificación comenzará en unos segundos. Asegúrate de tener tu perfil de Roblox listo.",
                    inline=False
                )
                
                welcome_embed.set_footer(text="Puro Chile RP - Segundo Intento")

                await channel.send(embed=welcome_embed)
                await asyncio.sleep(3)

                # Start Roblox verification process
                await self.start_roblox_verification(ctx.author, channel)

            except Exception as e:
                await ctx.send(f"❌ Error al reiniciar el canal de whitelist: {str(e)}")

    async def start_roblox_verification(self, user, channel):
        """Start Roblox account verification process"""
        try:
            # Generate short verification code with alternating prefixes
            code_options = ["PuroCL", "PuroChile", "PuroChileRP", "PRCL"]
            # Use user ID modulo to determine which code to use
            code_index = user.id % len(code_options)
            verification_code = code_options[code_index]
            
            self.pending_verifications[user.id] = {
                'code': verification_code,
                'channel_id': channel.id,
                'timestamp': datetime.now().isoformat()
            }

            # Create verification embed
            embed = discord.Embed(
                title="🎮 Vinculación de Cuenta de Roblox",
                description="Para continuar con tu whitelist, necesitas vincular tu cuenta de Roblox.",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📋 Instrucciones",
                value="1. Ve a tu perfil de Roblox\n2. Edita tu descripción\n3. Agrega el código de verificación\n4. Haz clic en 'Verificar Cuenta'",
                inline=False
            )
            
            embed.add_field(
                name="🔑 Código de Verificación",
                value=f"```{verification_code}```",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Importante",
                value="• Agrega EXACTAMENTE este código a tu descripción de Roblox\n• No modifiques el código\n• Puedes remover el código después de la verificación",
                inline=False
            )
            
            embed.add_field(
                name="⏰ Tiempo Límite",
                value="**Tienes 5 minutos para completar la verificación**\nSi no verificas en este tiempo, la whitelist será cancelada automáticamente.",
                inline=False
            )
            
            embed.set_footer(text="Puro Chile RP - Sistema de Whitelist con Roblox")

            # Create verification view
            view = RobloxVerificationView(user.id, self)
            
            verification_msg = await channel.send(embed=embed, view=view)
            
            # Start 5-minute countdown
            asyncio.create_task(self.handle_verification_timeout(user.id, channel, verification_msg))

        except Exception as e:
            await channel.send(f"❌ Error iniciando verificación de Roblox: {str(e)}")
    
    async def handle_verification_timeout(self, user_id, channel, verification_msg):
        """Handle timeout for Roblox verification"""
        try:
            # Wait 5 minutes (300 seconds)
            await asyncio.sleep(300)
            
            # Check if user is still pending verification
            if user_id in self.pending_verifications:
                # Remove from pending verifications
                del self.pending_verifications[user_id]
                
                # Remove user from active channels
                if user_id in self.user_channels:
                    del self.user_channels[user_id]
                
                # Get user and send timeout message (with error handling)
                user = None
                try:
                    user = channel.guild.get_member(user_id)
                except:
                    pass
                
                if user:
                    try:
                        # Create timeout embed
                        timeout_embed = discord.Embed(
                            title="⏰ Tiempo Límite Alcanzado",
                            description="La verificación de Roblox ha expirado por falta de tiempo.",
                            color=discord.Color.red(),
                            timestamp=datetime.now()
                        )
                        
                        timeout_embed.add_field(
                            name="❌ Whitelist Cancelada",
                            value="No completaste la verificación dentro del tiempo límite de 5 minutos.",
                            inline=False
                        )
                        
                        timeout_embed.add_field(
                            name="🔄 ¿Quieres intentar de nuevo?",
                            value="Usa el comando `pc!rechazar-whitelist` para reiniciar el proceso de whitelist.",
                            inline=False
                        )
                        
                        timeout_embed.set_footer(text="Puro Chile RP - Sistema de Whitelist")
                        
                        await channel.send(embed=timeout_embed)
                        
                        # Send DM to user
                        try:
                            dm_embed = discord.Embed(
                                title="⏰ Tiempo Límite Alcanzado",
                                description=f"**Tu proceso de whitelist en {channel.guild.name} ha expirado**",
                                color=discord.Color.orange(),
                                timestamp=datetime.now()
                            )
                            
                            dm_embed.add_field(
                                name="🚨 ¿Qué pasó?",
                                value="No completaste la verificación de Roblox dentro del tiempo límite de 5 minutos.",
                                inline=False
                            )
                            
                            dm_embed.add_field(
                                name="🔄 ¿Cómo continuar?",
                                value=f"Realiza de nuevo el comando `pc!rechazar-whitelist` para verificarte en **{channel.guild.name}**",
                                inline=False
                            )
                            
                            dm_embed.add_field(
                                name="💡 Consejos",
                                value="• Ten tu perfil de Roblox listo antes de empezar\n• Prepara la descripción de tu perfil para editarla rápidamente\n• Asegúrate de tener tiempo disponible para completar el proceso",
                                inline=False
                            )
                            
                            dm_embed.set_thumbnail(url=channel.guild.icon.url if channel.guild.icon else None)
                            dm_embed.set_footer(text=f"{channel.guild.name} - Sistema de Whitelist", 
                                              icon_url=channel.guild.icon.url if channel.guild.icon else None)
                            
                            await user.send(embed=dm_embed)
                        except discord.Forbidden:
                            print(f"No se pudo enviar DM a {user.name} - DMs cerrados")
                        except Exception as dm_error:
                            print(f"Error enviando DM: {dm_error}")
                    
                    except discord.NotFound:
                        print(f"Canal de whitelist ya no existe para usuario {user_id}")
                    except Exception as channel_error:
                        print(f"Error enviando mensaje de timeout: {channel_error}")
                
                # Delete channel after 10 seconds (with error handling)
                await asyncio.sleep(10)
                try:
                    await channel.delete()
                except discord.NotFound:
                    print(f"Canal ya fue eliminado para usuario {user_id}")
                except Exception as delete_error:
                    print(f"Error eliminando canal: {delete_error}")
                
        except Exception as e:
            print(f"Error en timeout de verificación: {e}")

    async def verify_roblox_account(self, interaction, roblox_username):
        """Verify Roblox account by checking description"""
        try:
            user_id = interaction.user.id
            
            if user_id not in self.pending_verifications:
                await interaction.response.send_message("❌ No tienes una verificación pendiente.", ephemeral=True)
                return

            verification_data = self.pending_verifications[user_id]
            expected_code = verification_data['code']

            # Get Roblox user data
            roblox_data = await self.get_roblox_user_data(roblox_username)
            if not roblox_data:
                await interaction.response.send_message("❌ Usuario de Roblox no encontrado.", ephemeral=True)
                return

            # Check if verification code is in description
            description = roblox_data.get('description', '')
            if expected_code not in description:
                embed = discord.Embed(
                    title="❌ Verificación Fallida",
                    description="El código de verificación no se encontró en tu descripción de Roblox.",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="🔑 Código Esperado",
                    value=f"```{expected_code}```",
                    inline=False
                )
                embed.add_field(
                    name="📝 Descripción Actual",
                    value=f"```{description[:200]}```",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Verification successful
            await interaction.response.send_message("✅ ¡Cuenta de Roblox verificada exitosamente!", ephemeral=True)
            
            # Remove from pending verifications (this will prevent timeout from triggering)
            del self.pending_verifications[user_id]
            
            # Start questionnaire with Roblox data
            channel = self.bot.get_channel(verification_data['channel_id'])
            if channel:
                await self.start_questionnaire_with_roblox_data(interaction.user, channel, roblox_data)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error durante la verificación: {str(e)}", ephemeral=True)
            print(f"Error en verificación de Roblox: {e}")

    async def get_roblox_user_data(self, username):
        """Get Roblox user data from API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get user ID from username
                search_url = f"https://users.roblox.com/v1/usernames/users"
                search_data = {
                    "usernames": [username],
                    "excludeBannedUsers": True
                }
                
                async with session.post(search_url, json=search_data) as response:
                    if response.status != 200:
                        return None
                    
                    search_result = await response.json()
                    if not search_result.get('data'):
                        return None
                    
                    user_id = search_result['data'][0]['id']

                # Get detailed user info
                user_url = f"https://users.roblox.com/v1/users/{user_id}"
                async with session.get(user_url) as response:
                    if response.status != 200:
                        return None
                    
                    user_data = await response.json()

                # Get avatar thumbnail
                avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=720x720&format=Png&isCircular=false"
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        avatar_data = await response.json()
                        if avatar_data.get('data'):
                            user_data['avatar_url'] = avatar_data['data'][0]['imageUrl']

                return user_data

        except Exception as e:
            print(f"Error obteniendo datos de Roblox: {e}")
            return None

    async def start_questionnaire_with_roblox_data(self, user, channel, roblox_data):
        """Start questionnaire with Roblox data already collected"""
        try:
            # Calculate account age
            created_date = datetime.fromisoformat(roblox_data['created'].replace('Z', '+00:00'))
            account_age_days = (datetime.now(created_date.tzinfo) - created_date).days
            account_age_years = account_age_days // 365
            account_age_months = (account_age_days % 365) // 30

            # Store Roblox data for later use
            roblox_info = {
                'username': roblox_data['name'],
                'display_name': roblox_data['displayName'],
                'profile_url': f"https://www.roblox.com/users/{roblox_data['id']}/profile",
                'avatar_url': roblox_data.get('avatar_url', ''),
                'account_age': f"{account_age_years} años, {account_age_months} meses",
                'account_created': created_date.strftime('%d/%m/%Y'),
                'description': roblox_data.get('description', 'Sin descripción')
            }

            # Clear channel and show Roblox info
            embed = discord.Embed(
                title="✅ Cuenta de Roblox Verificada",
                description="Tu cuenta de Roblox ha sido verificada exitosamente. Ahora responderás algunas preguntas.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Nombre de Roblox",
                value=roblox_info['username'],
                inline=True
            )
            
            embed.add_field(
                name="🏷️ Apodo de Roblox",
                value=roblox_info['display_name'],
                inline=True
            )
            
            embed.add_field(
                name="🔗 Link del Perfil",
                value=f"[Ver Perfil]({roblox_info['profile_url']})",
                inline=True
            )
            
            embed.add_field(
                name="📅 Edad de la Cuenta",
                value=roblox_info['account_age'],
                inline=True
            )
            
            embed.add_field(
                name="📆 Cuenta Creada",
                value=roblox_info['account_created'],
                inline=True
            )
            
            if roblox_info['avatar_url']:
                embed.set_thumbnail(url=roblox_info['avatar_url'])
            
            embed.set_footer(text="Puro Chile RP - Iniciando Cuestionario...")

            await channel.send(embed=embed)
            await asyncio.sleep(3)

            # Start questions
            await self.ask_questions(user, channel, roblox_info)

        except Exception as e:
            await channel.send(f"❌ Error iniciando cuestionario: {str(e)}")
            print(f"Error en cuestionario: {e}")

    async def ask_questions(self, user, channel, roblox_info):
        """Ask whitelist questions"""
        questions = [
            "¿Cuál es tu edad?",
            "¿Qué significa MG para ti?",
            "¿Cuál es la diferencia entre RK y CK?",
            "¿Tienes experiencia previa en roleplay? Describe brevemente.",
            "¿Por qué quieres unirte a nuestro servidor?",
            "¿Qué harías si 2 funcionarios policiales te apuntan?",
            "¿Qué roles realizarías dentro de nuestro server?",
            "¿Qué es Roleplay?"
        ]

        answers = []
        messages_to_delete = []

        try:
            # Send initial message
            initial_msg = await channel.send(
                f"🎭 **Cuestionario de Whitelist**\n{user.mention}, responde a las siguientes preguntas:"
            )
            messages_to_delete.append(initial_msg)

            # Ask each question
            for i, question in enumerate(questions, 1):
                embed = discord.Embed(
                    title=f"📋 Pregunta {i} de {len(questions)}",
                    description=question,
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Puro Chile RP - Sistema de Whitelist")

                question_msg = await channel.send(embed=embed)
                messages_to_delete.append(question_msg)

                def check(message):
                    return message.author == user and message.channel == channel

                try:
                    answer_msg = await self.bot.wait_for('message', check=check, timeout=300.0)
                    answers.append(answer_msg.content)
                    messages_to_delete.append(answer_msg)

                except asyncio.TimeoutError:
                    timeout_msg = await channel.send("⏰ Tiempo agotado. Whitelist cancelada.")
                    await asyncio.sleep(5)
                    await timeout_msg.delete()
                    return

            # Delete all messages
            for msg in messages_to_delete:
                try:
                    await msg.delete()
                except:
                    pass

            # Create final application embed
            await self.create_final_application(user, channel, roblox_info, answers)

        except Exception as e:
            await channel.send(f"❌ Error durante las preguntas: {str(e)}")

    async def create_final_application(self, user, channel, roblox_info, answers):
        """Create final application embed with all information"""
        try:
            # Create display name
            discord_original = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
            user_display = f"{roblox_info['username']} | {discord_original}"

            # Evaluate answers for semi-automated system
            evaluation_result = self.evaluate_answers(answers)
            
            if evaluation_result['needs_additional_questions']:
                # Ask additional questions if score is below 80%
                await self.ask_additional_questions(user, channel, roblox_info, answers, evaluation_result)
                return

            # Create comprehensive embed
            embed = discord.Embed(
                title="📋 Solicitud de Whitelist",
                description=f"**Usuario:** {user_display}\n**Discord:** {user.mention}\n**ID:** {user.id}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            # Add evaluation info
            score_color = "🟢" if evaluation_result['score'] >= 80 else "🟡" if evaluation_result['score'] >= 60 else "🔴"
            embed.add_field(
                name="🤖 Evaluación Automática",
                value=f"{score_color} **Puntuación:** {evaluation_result['score']}%\n📝 **Estado:** {evaluation_result['recommendation']}",
                inline=False
            )

            # Roblox Information Section
            embed.add_field(
                name="🎮 Información de Roblox",
                value=f"**Nombre:** {roblox_info['username']}\n**Apodo:** {roblox_info['display_name']}\n**Perfil:** [Ver Perfil]({roblox_info['profile_url']})\n**Edad de Cuenta:** {roblox_info['account_age']}",
                inline=False
            )

            # Questions and Answers
            questions = [
                "¿Cuál es tu edad?",
                "¿Qué significa MG para ti?",
                "¿Cuál es la diferencia entre RK y CK?",
                "¿Tienes experiencia previa en roleplay?",
                "¿Por qué quieres unirte a nuestro servidor?",
                "¿Qué harías si 2 funcionarios policiales te apuntan?",
                "¿Qué roles realizarías dentro de nuestro server?",
                "¿Qué es Roleplay?"
            ]

            for i, (question, answer) in enumerate(zip(questions, answers), 1):
                display_answer = answer[:150] + "..." if len(answer) > 150 else answer
                score_indicator = evaluation_result['detailed_scores'][i-1]
                score_emoji = "✅" if score_indicator >= 7 else "⚠️" if score_indicator >= 5 else "❌"
                
                embed.add_field(
                    name=f"**{i}. {question}** {score_emoji}",
                    value=display_answer,
                    inline=False
                )

            # Set Roblox avatar as thumbnail
            if roblox_info['avatar_url']:
                embed.set_thumbnail(url=roblox_info['avatar_url'])

            embed.set_footer(text="Puro Chile RP - Sistema de Whitelist Semi-Automatizado")

            # Check for auto-approval
            if evaluation_result.get('auto_approve', False):
                # Auto-approve the whitelist
                await self.auto_approve_whitelist(user, channel, roblox_info, answers, embed)
            else:
                # Create view with buttons for manual review
                view = WhitelistReviewView(user.id, channel.id, self, roblox_info)

                # Send to staff
                staff_role = channel.guild.get_role(STAFF_ROLE_ID)
                staff_mention = staff_role.mention if staff_role else "@Staff"

                await channel.send(
                    f"{staff_mention} Nueva solicitud de whitelist:",
                    embed=embed,
                    view=view
                )

            # Save application data
            await self.save_application_data(user.id, answers, channel.id, user_display, roblox_info)

        except Exception as e:
            await channel.send(f"❌ Error creando aplicación final: {str(e)}")

    def evaluate_answers(self, answers):
        """Evaluate answers using keyword detection system"""
        # Keywords for each question (weighted scoring) - Definiciones correctas de RP
        evaluation_criteria = {
            0: {  # Edad
                'good_keywords': ['15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25'],
                'weight': 5
            },
            1: {  # MG (MetaGaming) - Usar información OOC para beneficio IC
                'good_keywords': ['metagaming', 'meta gaming', 'información', 'ic', 'ooc', 'fuera del juego', 'beneficio', 'exterior', 'conoce', 'personaje', 'utiliza', 'decisiones'],
                'weight': 15
            },
            2: {  # RK vs CK - Revenge Kill vs Character Kill
                'good_keywords': ['revenge kill', 'venganza', 'character kill', 'definitiva', 'muerte', 'personaje', 'regresa', 'vuelve', 'antirol', 'ck', 'rk'],
                'weight': 15
            },
            3: {  # Experiencia RP
                'good_keywords': ['sí', 'si', 'experiencia', 'roleplay', 'servidores', 'juegos', 'roblox', 'fivem'],
                'weight': 10
            },
            4: {  # Por qué unirse
                'good_keywords': ['roleplay', 'diversión', 'amigos', 'comunidad', 'experiencia', 'entretenimiento'],
                'weight': 10
            },
            5: {  # Policías apuntando
                'good_keywords': ['manos', 'rendir', 'obedece', 'cooperar', 'arriba', 'quieto', 'levantar', 'no resistir', 'parar'],
                'weight': 15
            },
            6: {  # Roles a realizar
                'good_keywords': ['civil', 'ciudadano', 'policía', 'médico', 'mecánico', 'trabajo', 'empleo'],
                'weight': 10
            },
            7: {  # Qué es Roleplay
                'good_keywords': ['interpretar', 'actuar', 'personaje', 'simulación', 'real', 'vida', 'juego de roles', 'rolear'],
                'weight': 20
            }
        }

        detailed_scores = []
        total_score = 0
        max_possible_score = sum(criteria['weight'] for criteria in evaluation_criteria.values())

        for i, answer in enumerate(answers):
            if i < len(evaluation_criteria):
                criteria = evaluation_criteria[i]
                answer_lower = answer.lower()
                
                # Count keyword matches
                matches = sum(1 for keyword in criteria['good_keywords'] if keyword in answer_lower)
                
                # Calculate score for this answer (0-10 scale)
                if matches >= 2:
                    answer_score = 10
                elif matches == 1:
                    answer_score = 7
                elif len(answer) >= 10:  # At least tried to answer
                    answer_score = 4
                else:
                    answer_score = 0

                # Apply weight
                weighted_score = (answer_score / 10) * criteria['weight']
                total_score += weighted_score
                detailed_scores.append(answer_score)
            else:
                detailed_scores.append(0)

        # Calculate percentage
        final_percentage = (total_score / max_possible_score) * 100

        # Determine recommendation
        if final_percentage >= 100:
            recommendation = "🤖 AutoMod: Aprobación Automática"
            needs_additional = False
        elif final_percentage >= 80:
            recommendation = "✅ Recomendado para aprobación"
            needs_additional = False
        elif final_percentage >= 60:
            recommendation = "⚠️ Requiere revisión manual"
            needs_additional = False
        else:
            recommendation = "🔄 Requiere preguntas adicionales"
            needs_additional = True

        return {
            'score': round(final_percentage, 1),
            'recommendation': recommendation,
            'needs_additional_questions': needs_additional,
            'detailed_scores': detailed_scores,
            'auto_approve': final_percentage >= 100
        }

    async def ask_additional_questions(self, user, channel, roblox_info, initial_answers, evaluation_result):
        """Ask additional RP questions for users who scored below 80%"""
        try:
            # Notify about additional questions
            embed = discord.Embed(
                title="📚 Preguntas Adicionales de Roleplay",
                description=f"**{user.mention}**, necesitas responder algunas preguntas adicionales sobre conceptos básicos de roleplay.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="📊 Puntuación Inicial",
                value=f"**{evaluation_result['score']}%** - Se requiere 80% para aprobación automática",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Objetivo",
                value="Estas preguntas te ayudarán a demostrar tu conocimiento sobre roleplay básico.",
                inline=False
            )
            
            embed.set_footer(text="Puro Chile RP - Evaluación Adicional")

            await channel.send(embed=embed)
            await asyncio.sleep(2)

            # Additional questions
            additional_questions = [
                "¿Qué es PKT (PK Time)?",
                "¿Qué significa IC y OOC? Explica la diferencia.",
                "¿Qué es CarKill y cuándo se puede aplicar?",
                "¿Qué es VDM (Vehicle Death Match)?",
                "¿Qué es BD (Bunny Dancing) y por qué no se debe hacer?"
            ]

            additional_answers = []
            messages_to_delete = []

            # Ask each additional question
            for i, question in enumerate(additional_questions, 1):
                embed = discord.Embed(
                    title=f"📚 Pregunta Adicional {i} de {len(additional_questions)}",
                    description=question,
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Puro Chile RP - Preguntas Adicionales")

                question_msg = await channel.send(embed=embed)
                messages_to_delete.append(question_msg)

                def check(message):
                    return message.author == user and message.channel == channel

                try:
                    answer_msg = await self.bot.wait_for('message', check=check, timeout=300.0)
                    additional_answers.append(answer_msg.content)
                    messages_to_delete.append(answer_msg)

                except asyncio.TimeoutError:
                    timeout_msg = await channel.send("⏰ Tiempo agotado. Whitelist cancelada.")
                    await asyncio.sleep(5)
                    await timeout_msg.delete()
                    return

            # Delete all messages
            for msg in messages_to_delete:
                try:
                    await msg.delete()
                except:
                    pass

            # Combine all answers
            all_answers = initial_answers + additional_answers
            
            # Re-evaluate with additional answers
            final_evaluation = self.evaluate_all_answers(initial_answers, additional_answers)
            
            # Create final application with complete evaluation
            await self.create_final_application_with_additional(user, channel, roblox_info, all_answers, final_evaluation)

        except Exception as e:
            await channel.send(f"❌ Error en preguntas adicionales: {str(e)}")

    def evaluate_all_answers(self, initial_answers, additional_answers):
        """Evaluate both initial and additional answers"""
        # Evaluate initial answers
        initial_eval = self.evaluate_answers(initial_answers)
        
        # Evaluate additional answers - Definiciones correctas de RP
        additional_criteria = {
            0: {  # PKT (Player Kill Total) - Muerte con pérdida de memoria
                'good_keywords': ['player kill total', 'pkt', 'muerte', 'personaje', 'memoria', 'pérdida', 'total', 'organización', 'facción', 'vida anterior'],
                'weight': 10
            },
            1: {  # IC vs OOC - In Character vs Out of Character
                'good_keywords': ['in character', 'out of character', 'ic', 'ooc', 'personaje', 'fuera', 'dentro', 'rol', 'juego'],
                'weight': 10
            },
            2: {  # CarKill/CK - Matar con vehículo
                'good_keywords': ['car kill', 'ck', 'vehículo', 'vehiculo', 'atropellar', 'matar', 'carro', 'auto', 'encima', 'vida baja'],
                'weight': 10
            },
            3: {  # VDM (Vehicle Deathmatch) - Usar vehículo como arma sin razón
                'good_keywords': ['vehicle deathmatch', 'vdm', 'vehículo', 'vehiculo', 'arma', 'intencional', 'sin razón', 'justificada', 'daño'],
                'weight': 10
            },
            4: {  # BD (Bad Driving) - Mala conducción irreal
                'good_keywords': ['bad driving', 'bd', 'mala conducción', 'tránsito', 'leyes', 'realista', 'chocar', 'imprudente', 'altas velocidades'],
                'weight': 10
            }
        }

        additional_score = 0
        additional_max = sum(criteria['weight'] for criteria in additional_criteria.values())
        
        for i, answer in enumerate(additional_answers):
            if i < len(additional_criteria):
                criteria = additional_criteria[i]
                answer_lower = answer.lower()
                
                matches = sum(1 for keyword in criteria['good_keywords'] if keyword in answer_lower)
                
                if matches >= 1:
                    answer_score = 10
                elif len(answer) >= 10:
                    answer_score = 5
                else:
                    answer_score = 0

                weighted_score = (answer_score / 10) * criteria['weight']
                additional_score += weighted_score

        # Combine scores (70% initial, 30% additional)
        initial_weight = 0.7
        additional_weight = 0.3
        
        initial_percentage = initial_eval['score']
        additional_percentage = (additional_score / additional_max) * 100
        
        final_score = (initial_percentage * initial_weight) + (additional_percentage * additional_weight)

        if final_score >= 100:
            recommendation = "🤖 AutoMod: Aprobación Automática (tras preguntas adicionales)"
        elif final_score >= 80:
            recommendation = "✅ Recomendado para aprobación (tras preguntas adicionales)"
        elif final_score >= 65:
            recommendation = "⚠️ Requiere revisión manual detallada"
        else:
            recommendation = "❌ Se recomienda rechazar o más capacitación"

        return {
            'initial_score': initial_percentage,
            'additional_score': additional_percentage,
            'final_score': round(final_score, 1),
            'recommendation': recommendation,
            'auto_approve': final_score >= 100
        }

    async def create_final_application_with_additional(self, user, channel, roblox_info, all_answers, evaluation):
        """Create final application with additional questions evaluation"""
        try:
            discord_original = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
            user_display = f"{roblox_info['username']} | {discord_original}"

            embed = discord.Embed(
                title="📋 Solicitud de Whitelist - Evaluación Completa",
                description=f"**Usuario:** {user_display}\n**Discord:** {user.mention}\n**ID:** {user.id}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )

            # Evaluation results
            score_color = "🟢" if evaluation['final_score'] >= 80 else "🟡" if evaluation['final_score'] >= 65 else "🔴"
            embed.add_field(
                name="🤖 Evaluación Semi-Automatizada",
                value=f"{score_color} **Puntuación Final:** {evaluation['final_score']}%\n"
                      f"📊 **Preguntas Iniciales:** {evaluation['initial_score']}%\n"
                      f"📚 **Preguntas Adicionales:** {evaluation['additional_score']}%\n"
                      f"📝 **Recomendación:** {evaluation['recommendation']}",
                inline=False
            )

            # Roblox info
            embed.add_field(
                name="🎮 Información de Roblox",
                value=f"**Nombre:** {roblox_info['username']}\n**Apodo:** {roblox_info['display_name']}\n**Perfil:** [Ver Perfil]({roblox_info['profile_url']})\n**Edad de Cuenta:** {roblox_info['account_age']}",
                inline=False
            )

            # All questions and answers (truncated for space)
            all_questions = [
                "¿Cuál es tu edad?", "¿Qué significa MG para ti?", "¿Cuál es la diferencia entre RK y CK?",
                "¿Tienes experiencia previa en roleplay?", "¿Por qué quieres unirte a nuestro servidor?",
                "¿Qué harías si 2 funcionarios policiales te apuntan?", "¿Qué roles realizarías dentro de nuestro server?",
                "¿Qué es Roleplay?", "¿Qué es PKT (PK Time)?", "¿Qué significa IC y OOC?",
                "¿Qué es CarKill?", "¿Qué es VDM?", "¿Qué es BD?"
            ]

            # Show key answers only
            for i, (question, answer) in enumerate(zip(all_questions[:5], all_answers[:5])):
                display_answer = answer[:100] + "..." if len(answer) > 100 else answer
                embed.add_field(
                    name=f"**{i+1}. {question}**",
                    value=display_answer,
                    inline=False
                )

            if roblox_info['avatar_url']:
                embed.set_thumbnail(url=roblox_info['avatar_url'])

            embed.set_footer(text="Puro Chile RP - Sistema Semi-Automatizado")

            # Check for auto-approval
            if evaluation.get('auto_approve', False):
                # Auto-approve the whitelist
                await self.auto_approve_whitelist(user, channel, roblox_info, all_answers, embed)
            else:
                # Create view for manual review
                view = WhitelistReviewView(user.id, channel.id, self, roblox_info)

                # Send to staff
                staff_role = channel.guild.get_role(STAFF_ROLE_ID)
                staff_mention = staff_role.mention if staff_role else "@Staff"

                await channel.send(
                    f"{staff_mention} Solicitud de whitelist con evaluación completa:",
                    embed=embed,
                    view=view
                )

            # Save all data
            await self.save_application_data(user.id, all_answers, channel.id, user_display, roblox_info)

        except Exception as e:
            await channel.send(f"❌ Error creando aplicación final: {str(e)}")

    async def save_application_data(self, user_id, answers, channel_id, user_display, roblox_info):
        """Save application data to JSON file"""
        try:
            os.makedirs('data', exist_ok=True)

            # Load existing applications
            if os.path.exists('data/whitelist_applications.json'):
                with open('data/whitelist_applications.json', 'r', encoding='utf-8') as f:
                    applications = json.load(f)
            else:
                applications = {}

            # Asegurar que answers es una lista
            if not isinstance(answers, list):
                answers = []

            # Save new application
            applications[str(user_id)] = {
                'user_display': user_display,
                'answers': answers,
                'channel_id': channel_id,
                'status': 'pending',
                'timestamp': datetime.now().isoformat(),
                'roblox_info': roblox_info
            }

            # Save to file
            with open('data/whitelist_applications.json', 'w', encoding='utf-8') as f:
                json.dump(applications, f, indent=2, ensure_ascii=False)

            print(f"✅ Datos de whitelist guardados para usuario {user_id}")

        except Exception as e:
            print(f"Error saving application data: {e}")

    async def has_whitelist_history(self, user_id):
        """Check if user has already completed whitelist process"""
        try:
            if os.path.exists('data/whitelist_applications.json'):
                with open('data/whitelist_applications.json',
                          'r',
                          encoding='utf-8') as f:
                    applications = json.load(f)

                user_id_str = str(user_id)
                if user_id_str in applications:
                    # Check if user has been approved or rejected (completed process)
                    status = applications[user_id_str].get('status', 'pending')
                    return status in ['approved', 'rejected']

            return False
        except Exception as e:
            print(f"Error checking whitelist history: {e}")
            return False

    def remove_user_channel(self, user_id):
        """Remove user from active channels mapping"""
        if user_id in self.user_channels:
            del self.user_channels[user_id]

    async def send_reset_dm(self, user, user_data, staff_member):
        """Send DM to user with their whitelist information when reset"""
        try:
            embed = discord.Embed(
                title="🔄 Tu Whitelist Ha Sido Reseteada",
                description=f"**Hola {user.mention}**\n\nTu proceso de whitelist ha sido reseteado por un miembro del staff.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👮 Staff Responsable",
                value=f"{staff_member.display_name}\n`{staff_member}`",
                inline=True
            )
            
            embed.add_field(
                name="📅 Fecha del Reset",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            if user_data:
                # Show Roblox info if available
                roblox_info = user_data.get('roblox_info', {})
                if roblox_info:
                    embed.add_field(
                        name="🎮 Tu Información de Roblox",
                        value=f"**Nombre:** {roblox_info.get('username', 'N/A')}\n**Apodo:** {roblox_info.get('display_name', 'N/A')}\n**Perfil:** [Ver Perfil]({roblox_info.get('profile_url', 'N/A')})",
                        inline=False
                    )
                
                # Show status if available
                status = user_data.get('status', 'N/A')
                timestamp = user_data.get('timestamp', 'N/A')
                
                embed.add_field(
                    name="📊 Estado Anterior",
                    value=f"**Estado:** {status.title()}\n**Fecha Original:** {timestamp[:10] if timestamp != 'N/A' else 'N/A'}",
                    inline=False
                )
                
                # Show some answers if available
                answers = user_data.get('answers', [])
                if answers:
                    display_answers = []
                    questions = [
                        "¿Cuál es tu edad?",
                        "¿Qué significa MG para ti?",
                        "¿Cuál es la diferencia entre RK y CK?"
                    ]
                    
                    for i, (question, answer) in enumerate(zip(questions, answers[:3])):
                        short_answer = answer[:50] + "..." if len(answer) > 50 else answer
                        display_answers.append(f"**{question}**\n{short_answer}")
                    
                    if display_answers:
                        embed.add_field(
                            name="📝 Algunas de tus Respuestas Anteriores",
                            value="\n\n".join(display_answers),
                            inline=False
                        )
            
            embed.add_field(
                name="🔄 ¿Qué Significa Esto?",
                value="• Tu proceso de whitelist ha sido completamente eliminado\n• Puedes volver a hacer la whitelist usando `pc!whitelist`\n• Toda tu información anterior ha sido borrada del sistema",
                inline=False
            )
            
            embed.add_field(
                name="🚀 Próximos Pasos",
                value="Si deseas volver a hacer tu whitelist, puedes usar el comando `pc!whitelist` en el servidor para iniciar un nuevo proceso.",
                inline=False
            )
            
            embed.set_footer(text="Puro Chile RP - Sistema de Whitelist", 
                           icon_url=user.guild.icon.url if user.guild and user.guild.icon else None)
            
            await user.send(embed=embed)
            print(f"✅ DM de reset enviado a {user.name}")
            
        except discord.Forbidden:
            print(f"❌ No se pudo enviar DM a {user.name} - DMs cerrados")
        except Exception as e:
            print(f"❌ Error enviando DM de reset: {e}")

    async def auto_approve_whitelist(self, user, channel, roblox_info, answers, original_embed):
        """Auto-approve whitelist and handle all processes"""
        try:
            # Update embed for auto-approval
            auto_embed = discord.Embed(
                title="🤖 Whitelist Aprobada Automáticamente",
                description=f"**Usuario:** {roblox_info['username']} | {user.name}\n**Discord:** {user.mention}\n**ID:** {user.id}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            auto_embed.add_field(
                name="🤖 AutoMod",
                value="✅ **Puntuación:** 100%\n🎯 **Estado:** Aprobación Automática\n⚡ **Procesado por:** Sistema AutoMod",
                inline=False
            )
            
            # Assign roles and change nickname
            await self.assign_whitelist_roles_auto(user, roblox_info)
            
            # Send to results channel
            results_channel = channel.guild.get_channel(RESULTS_CHANNEL_ID)
            if results_channel:
                await results_channel.send(embed=auto_embed)
            
            # Log the auto-approval with detailed answers
            await self.log_auto_approval(channel.guild, user, roblox_info, answers)
            
            # Register user in history system
            try:
                from main import historial_user
                if hasattr(historial_user, 'register_new_whitelist_user'):
                    await historial_user.register_new_whitelist_user(user.id, answers)
            except Exception as e:
                print(f"Error registrando usuario en historial: {e}")
            
            # Update application status
            await self.update_application_status_auto(user.id)
            
            # Send confirmation to channel
            success_embed = discord.Embed(
                title="🎉 ¡Whitelist Aprobada Automáticamente!",
                description=f"**¡Felicidades {user.mention}!** Tu whitelist ha sido aprobada automáticamente por obtener una puntuación perfecta.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            success_embed.add_field(
                name="✅ Estado",
                value="Tu whitelist ha sido **aprobada automáticamente** por el sistema AutoMod.",
                inline=False
            )
            
            success_embed.add_field(
                name="🎯 Puntuación",
                value="**100%** - Respuestas perfectas",
                inline=True
            )
            
            success_embed.add_field(
                name="🔧 Procesado por",
                value="🤖 AutoMod (Sistema Automático)",
                inline=True
            )
            
            success_embed.add_field(
                name="🚀 Próximos Pasos",
                value="Ya tienes acceso completo al servidor. ¡Disfruta del roleplay!",
                inline=False
            )
            
            success_embed.set_footer(text="Puro Chile RP - Aprobación Automática")
            
            await channel.send(embed=success_embed)
            
            # Remove user from active channels and cleanup
            self.remove_user_channel(user.id)
            
            # Schedule channel deletion
            await asyncio.sleep(10)
            try:
                await channel.delete()
            except:
                pass
                
        except Exception as e:
            print(f"Error en aprobación automática: {e}")
    
    async def assign_whitelist_roles_auto(self, user, roblox_info=None):
        """Assign roles for auto-approved whitelist"""
        try:
            # Roles to add when approved
            roles_to_add = [
                1221496580742582356,  # Role 1
                1221496580721479892,  # Role 2
                1221496580700504071,  # Role 3
                1221496580700504070,  # Role 4
                1221496580700504068,  # Role 5
                1341452452301639740,  # Role 6
                1377159358898634792,  # Role 7
                1221496580683862099   # Role 8
            ]

            # Roles to remove when approved
            roles_to_remove = [1221496580700504067]  # Remove pending role

            # Add roles
            for role_id in roles_to_add:
                role = user.guild.get_role(role_id)
                if role and role not in user.roles:
                    try:
                        await user.add_roles(role, reason="Whitelist auto-approved by AutoMod")
                    except Exception as e:
                        print(f"Error adding role {role.name}: {e}")

            # Remove roles
            for role_id in roles_to_remove:
                role = user.guild.get_role(role_id)
                if role and role in user.roles:
                    try:
                        await user.remove_roles(role, reason="Whitelist auto-approved by AutoMod")
                    except Exception as e:
                        print(f"Error removing role {role.name}: {e}")

            # Change user nickname to Discord | Roblox format
            if roblox_info:
                await self.change_user_nickname(user, roblox_info)

        except Exception as e:
            print(f"Error managing roles auto: {e}")

    async def change_user_nickname(self, user, roblox_info):
        """Change user nickname to Discord | Roblox format"""
        try:
            # Get original Discord username (without discriminator if it's 0)
            discord_username = user.name
            
            # Get Roblox username
            roblox_username = roblox_info.get('username', 'Unknown')
            
            # Create new nickname format: DiscordUser | RobloxUser
            new_nickname = f"{discord_username} | {roblox_username}"
            
            # Limit nickname length (Discord max is 32 characters)
            if len(new_nickname) > 32:
                # Truncate but keep the format
                available_chars = 32 - 3  # 3 for " | "
                discord_part = discord_username[:available_chars//2]
                roblox_part = roblox_username[:available_chars//2]
                new_nickname = f"{discord_part} | {roblox_part}"
            
            # Change nickname
            await user.edit(nick=new_nickname, reason="Whitelist approved - Auto nickname update")
            print(f"✅ Nickname cambiado para {user.name}: {new_nickname}")
            
        except discord.Forbidden:
            print(f"❌ No se pudo cambiar el nickname de {user.name} - Sin permisos")
        except Exception as e:
            print(f"❌ Error cambiando nickname de {user.name}: {e}")
    
    async def log_auto_approval(self, guild, user, roblox_info, answers):
        """Log auto-approval with detailed answers"""
        try:
            # Canal de logs de whitelist
            LOG_CHANNEL_ID = 1390107154144563371
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            
            if not log_channel:
                print(f"❌ Canal de logs {LOG_CHANNEL_ID} no encontrado")
                return
            
            embed = discord.Embed(
                title="🤖 Whitelist Aprobada por AutoMod",
                description="El sistema AutoMod ha aprobado automáticamente una whitelist",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            # Información del usuario
            embed.add_field(
                name="👤 Usuario Aprobado",
                value=f"**Nombre:** {user.display_name}\n**Usuario:** {user.mention}\n**ID:** `{user.id}`",
                inline=True
            )
            
            # Información de Roblox
            embed.add_field(
                name="🎮 Cuenta de Roblox",
                value=f"**Usuario:** {roblox_info['username']}\n**Apodo:** {roblox_info['display_name']}\n**Edad:** {roblox_info['account_age']}",
                inline=True
            )
            
            # Información del sistema
            embed.add_field(
                name="🤖 Sistema AutoMod",
                value=f"**Puntuación:** 100%\n**Estado:** Aprobado Automáticamente\n**Fecha:** <t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            # Mostrar respuestas del usuario
            questions = [
                "¿Cuál es tu edad?",
                "¿Qué significa MG para ti?",
                "¿Cuál es la diferencia entre RK y CK?",
                "¿Tienes experiencia previa en roleplay?",
                "¿Por qué quieres unirte a nuestro servidor?",
                "¿Qué harías si 2 funcionarios policiales te apuntan?",
                "¿Qué roles realizarías dentro de nuestro server?",
                "¿Qué es Roleplay?"
            ]
            
            # Mostrar algunas respuestas clave
            key_answers = []
            for i, (question, answer) in enumerate(zip(questions[:4], answers[:4])):
                short_answer = answer[:80] + "..." if len(answer) > 80 else answer
                key_answers.append(f"**{i+1}. {question}**\n{short_answer}")
            
            if key_answers:
                embed.add_field(
                    name="📝 Respuestas Clave (AutoMod)",
                    value="\n\n".join(key_answers),
                    inline=False
                )
            
            embed.add_field(
                name="✅ Acciones Realizadas",
                value="• Roles asignados automáticamente\n• Usuario registrado en el sistema\n• Acceso completo otorgado\n• Canal de whitelist programado para eliminación",
                inline=False
            )
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.set_footer(text="Puro Chile RP - Log AutoMod")
            
            await log_channel.send(embed=embed)
            print(f"✅ Log de aprobación automática registrado para {user.name}")
            
        except Exception as e:
            print(f"❌ Error registrando log de aprobación automática: {e}")
    
    async def update_application_status_auto(self, user_id):
        """Update application status for auto-approval"""
        try:
            if os.path.exists('data/whitelist_applications.json'):
                with open('data/whitelist_applications.json', 'r', encoding='utf-8') as f:
                    applications = json.load(f)

                if str(user_id) in applications:
                    applications[str(user_id)]['status'] = 'approved'
                    applications[str(user_id)]['decided_at'] = datetime.now().isoformat()
                    applications[str(user_id)]['decided_by'] = 'AutoMod System'
                    applications[str(user_id)]['auto_approved'] = True

                    with open('data/whitelist_applications.json', 'w', encoding='utf-8') as f:
                        json.dump(applications, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error updating auto status: {e}")

    async def log_whitelist_reset(self, guild, user, staff_member, user_data, channel_deleted):
        """Log whitelist reset action to designated channel"""
        try:
            # Canal de logs de whitelist
            LOG_CHANNEL_ID = 1390107154144563371
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            
            if not log_channel:
                print(f"❌ Canal de logs {LOG_CHANNEL_ID} no encontrado")
                return
            
            embed = discord.Embed(
                title="🔄 Whitelist Reseteada por Staff",
                description="Un miembro del staff ha reseteado completamente una whitelist",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            # Información del usuario afectado
            embed.add_field(
                name="👤 Usuario Afectado",
                value=f"**Nombre:** {user.display_name}\n**Usuario:** {user.mention}\n**ID:** `{user.id}`",
                inline=True
            )
            
            # Información del staff
            embed.add_field(
                name="👮 Staff Responsable",
                value=f"**Nombre:** {staff_member.display_name}\n**Usuario:** {staff_member.mention}\n**ID:** `{staff_member.id}`",
                inline=True
            )
            
            # Información de la acción
            embed.add_field(
                name="🔧 Detalles de la Acción",
                value=f"**Canal Eliminado:** {'✅ Sí' if channel_deleted else '❌ No'}\n**DM Enviado:** ✅ Sí\n**Datos Eliminados:** ✅ Sí",
                inline=True
            )
            
            if user_data:
                # Información de la whitelist eliminada
                roblox_info = user_data.get('roblox_info', {})
                status = user_data.get('status', 'N/A')
                timestamp = user_data.get('timestamp', 'N/A')
                
                embed.add_field(
                    name="📊 Información de la Whitelist Eliminada",
                    value=f"**Estado:** {status.title()}\n**Fecha Original:** {timestamp[:10] if timestamp != 'N/A' else 'N/A'}\n**Tenía Roblox:** {'✅ Sí' if roblox_info else '❌ No'}",
                    inline=False
                )
                
                if roblox_info:
                    embed.add_field(
                        name="🎮 Datos de Roblox Eliminados",
                        value=f"**Usuario:** {roblox_info.get('username', 'N/A')}\n**Apodo:** {roblox_info.get('display_name', 'N/A')}\n**Edad de Cuenta:** {roblox_info.get('account_age', 'N/A')}",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="📊 Información de la Whitelist",
                    value="❌ No se encontraron datos previos de whitelist",
                    inline=False
                )
            
            embed.add_field(
                name="⚠️ Consecuencias",
                value="• El usuario puede volver a hacer whitelist\n• Todos los datos anteriores han sido eliminados\n• Se ha enviado notificación por DM al usuario",
                inline=False
            )
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.set_footer(text="Puro Chile RP - Log de Reset de Whitelist")
            
            await log_channel.send(embed=embed)
            print(f"✅ Log de reset registrado para {user.name}")
            
        except Exception as e:
            print(f"❌ Error registrando log de reset: {e}")


class RobloxVerificationView(discord.ui.View):
    def __init__(self, user_id, whitelist_system):
        super().__init__(timeout=None)  # Sin timeout para persistencia
        self.user_id = user_id
        self.whitelist_system = whitelist_system

    @discord.ui.button(label='🔗 Verificar Cuenta de Roblox', style=discord.ButtonStyle.primary, custom_id='verify_roblox_account')
    async def verify_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Solo el usuario puede usar este botón.", ephemeral=True)
            return

        # Create modal for username input
        modal = RobloxUsernameModal(self.whitelist_system)
        await interaction.response.send_modal(modal)


class RobloxUsernameModal(discord.ui.Modal, title='Ingresa tu Usuario de Roblox'):
    def __init__(self, whitelist_system):
        super().__init__()
        self.whitelist_system = whitelist_system

    username = discord.ui.TextInput(
        label='Usuario de Roblox',
        placeholder='Ingresa tu nombre de usuario exacto de Roblox...',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.whitelist_system.verify_roblox_account(interaction, self.username.value.strip())


class WhitelistReviewView(discord.ui.View):
    def __init__(self, user_id, channel_id, whitelist_system, roblox_info):
        super().__init__(timeout=None)  # Sin timeout para persistencia
        self.user_id = user_id
        self.channel_id = channel_id
        self.whitelist_system = whitelist_system
        self.roblox_info = roblox_info

    @discord.ui.button(label='✅ Aceptar Whitelist', style=discord.ButtonStyle.success, custom_id='approve_whitelist')
    async def approve_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ Solo el staff puede usar este botón.", ephemeral=True)
            return

        await self.process_decision(interaction, "approved")

    @discord.ui.button(label='❌ Rechazar Whitelist', style=discord.ButtonStyle.danger, custom_id='reject_whitelist')
    async def reject_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ Solo el staff puede usar este botón.", ephemeral=True)
            return

        await self.process_decision(interaction, "rejected")

    async def process_decision(self, interaction, decision):
        """Process whitelist decision"""
        try:
            user = interaction.guild.get_member(self.user_id)
            results_channel = interaction.guild.get_channel(RESULTS_CHANNEL_ID)

            if not user or not results_channel:
                await interaction.response.send_message("❌ Error: Usuario o canal no encontrado.", ephemeral=True)
                return

            # Responder inmediatamente a la interacción
            status_text = "APROBADA" if decision == "approved" else "RECHAZADA"
            await interaction.response.send_message(
                f"✅ Whitelist {status_text.lower()} correctamente. El canal se eliminará en 5 segundos.",
                ephemeral=True
            )

            # Create result embed
            color = discord.Color.green() if decision == "approved" else discord.Color.red()
            status_emoji = "✅" if decision == "approved" else "❌"

            discord_original = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
            user_display = f"{self.roblox_info['username']} | {discord_original}"

            result_embed = discord.Embed(
                title=f"{status_emoji} Whitelist {status_text}",
                description=f"**Usuario:** {user_display}\n**Discord:** {user.mention}\n**ID:** `{user.id}`",
                color=color,
                timestamp=datetime.now()
            )

            # Add Roblox info
            result_embed.add_field(
                name="🎮 Información de Roblox",
                value=f"**Nombre:** {self.roblox_info['username']}\n**Apodo:** {self.roblox_info['display_name']}\n**Perfil:** [Ver Perfil]({self.roblox_info['profile_url']})\n**Edad de Cuenta:** {self.roblox_info['account_age']}",
                inline=False
            )

            result_embed.add_field(
                name="👮 Staff Responsable",
                value=f"{interaction.user.mention}\n`{interaction.user.display_name}`",
                inline=True
            )

            if self.roblox_info['avatar_url']:
                result_embed.set_thumbnail(url=self.roblox_info['avatar_url'])

            result_embed.set_footer(text="Puro Chile RP - Sistema de Whitelist")

            # Send result
            await results_channel.send(embed=result_embed)

            # Handle role assignment if approved
            if decision == "approved":
                await self.assign_whitelist_roles(interaction, user)
                
                # Register user in history system
                try:
                    from main import historial_user
                    if hasattr(historial_user, 'register_new_whitelist_user'):
                        # Get user answers for registration
                        applications = {}
                        if os.path.exists('data/whitelist_applications.json'):
                            with open('data/whitelist_applications.json', 'r', encoding='utf-8') as f:
                                applications = json.load(f)
                        
                        user_data = applications.get(str(self.user_id), {})
                        answers = user_data.get('answers', [])
                        await historial_user.register_new_whitelist_user(self.user_id, answers)
                except Exception as e:
                    print(f"Error registrando usuario en historial: {e}")

            # Disable buttons
            for item in self.children:
                item.disabled = True

            # Edit the message to disable buttons
            try:
                await interaction.edit_original_response(view=self)
            except:
                # Si falla, intenta obtener el mensaje original
                pass

            # Update status and cleanup
            await self.update_application_status(decision, interaction.user.display_name)
            self.whitelist_system.remove_user_channel(self.user_id)
            
            # Schedule channel deletion
            asyncio.create_task(self.cleanup_channel(interaction))

        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ Error procesando decisión: {str(e)}", ephemeral=True)
            except:
                try:
                    await interaction.followup.send(f"❌ Error procesando decisión: {str(e)}", ephemeral=True)
                except:
                    pass
            print(f"Error en decisión de whitelist: {e}")

    async def assign_whitelist_roles(self, interaction, user):
        """Assign roles when whitelist is approved"""
        try:
            # Roles to add when approved
            roles_to_add = [
                1221496580742582356,  # Role 1
                1221496580721479892,  # Role 2
                1221496580700504071,  # Role 3
                1221496580700504070,  # Role 4
                1221496580700504068,  # Role 5
                1341452452301639740,  # Role 6
                1377159358898634792,  # Role 7
                1221496580683862099   # Role 8
            ]

            # Roles to remove when approved
            roles_to_remove = [1221496580700504067]  # Remove pending role

            # Add roles
            for role_id in roles_to_add:
                role = interaction.guild.get_role(role_id)
                if role and role not in user.roles:
                    try:
                        await user.add_roles(role, reason="Whitelist approved")
                    except discord.Forbidden:
                        print(f"No permission to add role {role.name}")
                    except Exception as e:
                        print(f"Error adding role {role.name}: {e}")

            # Remove roles
            for role_id in roles_to_remove:
                role = interaction.guild.get_role(role_id)
                if role and role in user.roles:
                    try:
                        await user.remove_roles(role, reason="Whitelist approved")
                    except discord.Forbidden:
                        print(f"No permission to remove role {role.name}")
                    except Exception as e:
                        print(f"Error removing role {role.name}: {e}")

            # Change user nickname to Discord | Roblox format
            await self.change_user_nickname(user, self.roblox_info)

        except Exception as e:
            print(f"Error managing roles: {e}")

    async def update_application_status(self, status, decided_by):
        """Update application status"""
        try:
            if os.path.exists('data/whitelist_applications.json'):
                with open('data/whitelist_applications.json', 'r', encoding='utf-8') as f:
                    applications = json.load(f)

                if str(self.user_id) in applications:
                    applications[str(self.user_id)]['status'] = status
                    applications[str(self.user_id)]['decided_at'] = datetime.now().isoformat()
                    applications[str(self.user_id)]['decided_by'] = decided_by

                    with open('data/whitelist_applications.json', 'w', encoding='utf-8') as f:
                        json.dump(applications, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error updating status: {e}")

    async def cleanup_channel(self, interaction):
        """Clean up channel"""
        try:
            await asyncio.sleep(5)
            channel = interaction.guild.get_channel(self.channel_id)
            if channel:
                await channel.delete()
        except Exception as e:
            print(f"Error cleaning up channel: {e}")
