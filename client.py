#!/usr/bin/python3
#
# endless-war
# mperron (2018)
#
# a chat bot for the RFCK discord server

import discord
import asyncio
import random
import sys
import time

import ewutils
import ewcfg
from ew import EwUser

print('Starting up...')

client = discord.Client()

# A map containing user IDs and the last time in UTC seconds since we sent them
# the help doc via DM. This is to prevent spamming.
last_helped_times = {}

debug = False
while sys.argv:
	if sys.argv[0].lower() == '--debug':
		debug = True

	sys.argv = sys.argv[1:]

# When debug is enabled, additional commands are turned on.
if debug == True:
	print('Debug mode enabled.')

@client.event
async def on_ready():
	print('Logged in as {} ({}).'.format(client.user.name, client.user.id))
	print('Ready.')

	await client.change_presence(game=discord.Game(name=("dev. by @krak " + ewcfg.version)))


@client.event
async def on_message(message):
	""" do not interact with our own messages """
	if message.author.id == client.user.id or message.author.bot == True:
		return

	"""
		Wake up if we need to respond to messages. Could be:
			message starts with !
			direct message (server == None)
			user is new/has no roles (len(roles) < 2)
	"""
	if message.content.startswith(ewcfg.cmd_prefix) or message.server == None or len(message.author.roles) < 2:
		# tokenize the message. the command should be the first word.
		tokens = message.content.split(' ')
		tokens_count = len(tokens)
		cmd = tokens[0].lower()

		""" reply to DMs with help document """
		if message.server == None:
			time_now = int(time.time())
			time_last = last_helped_times.get(message.author.id, 0)

			# Only send the help doc once every thirty seconds. There's no need to spam it.
			if (time_now - time_last) > 30:
				last_helped_times[message.author.id] = time_now
				await client.send_message(message.channel, ewutils.getHelpText())

			# Nothing else to do in a DM.
			return

		# remove mentions to us
		mentions = list(filter(lambda user : user.id != client.user.id, message.mentions))

		# common data we'll need
		roles_map = ewutils.getRoleMap(message.server.roles)
		mentions_count = len(mentions)

		# assign the juveniles role to a user with only 1 or 0 roles.
		if len(message.author.roles) < 2:
			role_juvenile = roles_map[ewcfg.role_juvenile]
			await client.replace_roles(message.author, role_juvenile)
			return

		# let the user know we're working on it
		if cmd != ewcfg.cmd_mine or message.channel.name != ewcfg.channel_mines:
			resp = await client.send_message(message.channel, '...')

		# process command words
		if cmd == ewcfg.cmd_kill:
			response = ""

			if message.channel.name != ewcfg.channel_combatzone:
				response = "You must go to the #{} to commit gang violence.".format(ewcfg.channel_combatzone)

			# Only allow one kill at a time.
			elif mentions_count > 1:
				response = "One kill at a time!"

			elif mentions_count == 1:
				# The roles assigned to the author of this user.
				roles_map_user = ewutils.getRoleMap(message.author.roles)

				try:
					conn = ewutils.databaseConnect();
					cursor = conn.cursor();

					# Get killing player's info.
					user_data = EwUser(member=message.author, conn=conn, cursor=cursor)

					# Get target's info.
					member = mentions[0]
					killed_data = EwUser(member=member, conn=conn, cursor=cursor)

					conn.commit()
				finally:
					cursor.close()
					conn.close()

				if (int(time.time()) - user_data.time_lastkill) < ewcfg.cd_kill:
					# disallow kill if the player has killed recently
					response = "Take a moment to appreciate your last slaughter."
				elif killed_data.id_killer == user_data.id_user:
					# disallow kill if the player is the id_killer of killed_data
					response = "You have already proven your superiority over {}.".format(member.display_name)
				else:
					# new (more fair?) slime calculation. more slimes makes you harder to kill.
					slimes_tokill = ewcfg.slimes_tokill + int(user_data.slimes/10) + int(killed_data.slimes/2)

					if user_data.slimes < slimes_tokill:
						response = "You are currently too weak-willed and feminine. Harvest more Juveniles for their slime."
					else:
						user_iskillers = ewcfg.role_copkillers in roles_map_user or ewcfg.role_copkiller in roles_map_user
						user_isrowdys = ewcfg.role_rowdyfuckers in roles_map_user or ewcfg.role_rowdyfucker in roles_map_user

						# Only killers, rowdys, the cop killer, and the rowdy fucker can kill people
						if user_iskillers == False and user_isrowdys == False:
							response = "Juveniles lack the moral fiber necessary for murder."
						else:
							# slimes from this kill might be awarded to the boss
							role_boss = (ewcfg.role_copkiller if user_iskillers == True else ewcfg.role_rowdyfucker)
							boss_slimes = 0

							role_corpse = roles_map[ewcfg.role_corpse]

							was_juvenile = False
							was_killed = False
							was_invuln = False
							was_dead = False

							roles_map_target = ewutils.getRoleMap(member.roles)
							if (int(time.time()) - killed_data.time_lastrevive) < ewcfg.invuln_onrevive:
								# User is currently invulnerable
								was_invuln = True

							elif role_corpse in roles_map_target:
								# Target is already dead.
								was_dead = True

							elif (user_iskillers and (ewcfg.role_rowdyfuckers in roles_map_target)) or (user_isrowdys and (ewcfg.role_copkillers in roles_map_target)) or (ewcfg.role_juvenile in roles_map_target):
								# User can be killed.
								if ewcfg.role_juvenile in roles_map_target:
									was_juvenile = True

								was_killed = True
								await client.replace_roles(member, role_corpse)

							if was_killed == True:
								try:
									conn = ewutils.databaseConnect();
									cursor = conn.cursor();

									user_data.slimes -= slimes_tokill

									if killed_data.slimes > 0:
										if was_juvenile == True:
											# Add juvenile targets' slimes to this player.
											user_data.slimes += killed_data.slimes
										else:
											# Add adult tarets' slimes to the boss.
											boss_slimes += killed_data.slimes

									# Remove !revive invulnerability.
									user_data.time_lastrevive = 0

									# Set the last kill time for kill cooldown.
									user_data.time_lastkill = int(time.time())

									user_data.persist(conn=conn, cursor=cursor)

									# Remove all slimes from the dead player.
									killed_data.slimes = 0
									killed_data.id_killer = message.author.id
									killed_data.persist(conn=conn, cursor=cursor)

									conn.commit()
								finally:
									cursor.close()
									conn.close()

								# give slimes to the boss if possible.
								boss_member = None
								if boss_slimes > 0:
									for member_search in message.author.server.members:
										if role_boss in ewutils.getRoleMap(member_search.roles):
											boss_member = member_search
											break
									
									if boss_member != None:
										try:
											conn = ewutils.databaseConnect();
											cursor = conn.cursor();

											boss_data = EwUser(member=boss_member, conn=conn, cursor=cursor)
											boss_data.slimes += boss_slimes
											boss_data.persist(conn=conn, cursor=cursor)

											conn.commit()
										finally:
											cursor.close()
											conn.close()

								# player was killed
								response = '{} has been SLAUGHTERED. <:slime5:431659469844381717> :gun:'.format(member.display_name)
							else:
								if was_invuln == True:
									# player was invulnerable
									response = '{} has died too recently and is immune.'.format(member.display_name)
								elif was_dead == True:
									# target is already dead
									response = '{} is already dead.'.format(member.display_name)
								else:
									# teammate, or otherwise unkillable
									response = 'ENDLESS WAR finds this betrayal stinky. He will not allow you to slaughter {}.'.format(member.display_name)
			else:
				response = 'Your bloodlust is appreciated, but ENDLESS WAR didn\'t understand that name.'

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))


		# Spar with an ally
		elif cmd == ewcfg.cmd_spar:
			response = ""

			if message.channel.name != ewcfg.channel_dojo:
				response = "You must go to the #{} to spar.".format(ewcfg.channel_dojo)

			# Only allow one kill at a time.
			elif mentions_count > 1:
				response = "One sparring partner at a time!"

			elif mentions_count == 1:
				# The roles assigned to the author of this user.
				roles_map_user = ewutils.getRoleMap(message.author.roles)

				try:
					conn = ewutils.databaseConnect();
					cursor = conn.cursor();

					# Get killing player's info.
					user_data = EwUser(member=message.author, conn=conn, cursor=cursor)

					# Get target's info.
					member = mentions[0]
					sparred_data = EwUser(member=member, conn=conn, cursor=cursor)

					conn.commit()
				finally:
					cursor.close()
					conn.close()

				user_iskillers = ewcfg.role_copkillers in roles_map_user or ewcfg.role_copkiller in roles_map_user
				user_isrowdys = ewcfg.role_rowdyfuckers in roles_map_user or ewcfg.role_rowdyfucker in roles_map_user

				# Only killers, rowdys, the cop killer, and the rowdy fucker can spar
				if user_iskillers == False and user_isrowdys == False:
					response = "Juveniles lack the backbone necessary for combat."
				else:
					was_juvenile = False
					was_sparred = False
					was_dead = False
					was_player_tired = False
					was_target_tired = False

					roles_map_target = ewutils.getRoleMap(member.roles)

					if ewcfg.role_corpse in roles_map_target:
						# Target is already dead.
						was_dead = True
					elif (user_data.time_lastspar + ewcfg.cd_spar) > int(time.time()):
						# player sparred too recently
						was_player_tired = True
					elif (sparred_data.time_lastspar + ewcfg.cd_spar) > int(time.time()):
						# taret sparred too recently
						was_target_tired = True
					elif ewcfg.role_juvenile in roles_map_target:
						# Target is a juvenile.
						was_juvenile = True

					elif (user_iskillers and (ewcfg.role_copkillers in roles_map_target)) or (user_isrowdys and (ewcfg.role_rowdyfuckers in roles_map_target)):
						# User can be sparred.
						was_sparred = True


					#if the duel is successful
					if was_sparred:
						weaker_player = sparred_data if sparred_data.slimes < user_data.slimes else user_data
						stronger_player = sparred_data if user_data is weaker_player else user_data

						# Weaker player gains slime based on the slime of the stronger player.
						weaker_player.slimes += ewcfg.slimes_perspar if (stronger_player.slimes / 2) > ewcfg.slimes_perspar else (stronger_player.slimes / 2)
						weaker_player.time_lastspar = int(time.time())
						weaker_player.persist()

						# player was sparred with
						response = '{} parries the attack. <:knife: :slime5:431659469844381717>'.format(member.display_name)
					else:
						if was_dead:
							# target is already dead
							response = '{} is already dead.'.format(member.display_name)
						elif was_target_tired:
							# target has sparred too recently
							response = '{} is too tired to spar right now.'.format(member.display_name)
						elif was_player_tired:
							# player has sparred too recently
							response = 'You are too tired to spar right now.'
						else:
							#otherwise unkillable
							response = '{} cannot spar now.'.format(member.display_name)
			else:
				response = 'Your fighting spirit is appreciated, but ENDLESS WAR didn\'t understand that name.'

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))


		# revive yourself as a juvenile after having been killed.
		elif cmd == ewcfg.cmd_revive:
			response = ""

			if message.channel.name != ewcfg.channel_endlesswar and message.channel.name != ewcfg.channel_sewers:
				response = "Come to me. I hunger. #{}.".format(ewcfg.channel_sewers)
			else:
				roles_map_user = ewutils.getRoleMap(message.author.roles)

				if ewcfg.role_corpse in roles_map_user:
					try:
						conn = ewutils.databaseConnect();
						cursor = conn.cursor();

						player_data = EwUser(member=message.author, conn=conn, cursor=cursor)

						# Give player some initial slimes.
						player_data.slimes = ewcfg.slimes_onrevive
						player_data.time_lastrevive = int(time.time())
						player_data.persist(conn=conn, cursor=cursor)

						# Give some slimes to every living player (currently online)
						for member in message.server.members:
							if member.id != message.author.id and member.id != client.user.id:
								if ewcfg.role_corpse not in ewutils.getRoleMap(member.roles):
									member_data = EwUser(member=member, conn=conn, cursor=cursor)
									member_data.slimes += ewcfg.slimes_onrevive_everyone
									member_data.persist(conn=conn, cursor=cursor)

						# Commit all transactions at once.
						conn.commit()
					finally:
						cursor.close()
						conn.close()

					await client.replace_roles(message.author, roles_map[ewcfg.role_juvenile])
					response = '<:slime4:431570132901560320> A geyser of fresh slime erupts, showering Rowdy, Killer, and Juvenile alike. <:slime4:431570132901560320> {} has been reborn in slime. <:slime4:431570132901560320>'.format(message.author.display_name)
				else:
					response = 'You\'re not dead just yet.'

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))

		# move from juvenile to one of the armies (rowdys or killers)
		elif cmd == ewcfg.cmd_enlist:
			response = ""
			roles_map_user = ewutils.getRoleMap(message.author.roles)

			if ewcfg.role_juvenile in roles_map_user:
				faction = ""
				if tokens_count > 1:
					faction = tokens[1].lower()

				user_slimes = EwUser(member=message.author).slimes

				if user_slimes < ewcfg.slimes_toenlist:
					response = "You need to mine more slime to rise above your lowly station. ({}/{})".format(user_slimes, ewcfg.slimes_toenlist)
				else:
					if faction == ewcfg.faction_rowdys:
						await client.replace_roles(message.author, roles_map[ewcfg.role_rowdyfuckers])
						response = "Enlisted in the {}.".format(ewcfg.faction_rowdys)
					elif faction == ewcfg.faction_killers:
						await client.replace_roles(message.author, roles_map[ewcfg.role_copkillers])
						response = "Enlisted in the {}.".format(ewcfg.faction_killers)
					else:
						response = "Which faction? Say '{} {}' or '{} {}'.".format(ewcfg.cmd_enlist, ewcfg.faction_killers, ewcfg.cmd_enlist, ewcfg.faction_rowdys)

			elif ewcfg.role_corpse in roles_map_user:
				response = 'You are dead, bitch.'
			else:
				response = "You can't do that right now, bitch."

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))

		# faction leader consumes the mentioned players of their own faction to absorb their slime count
		# kills the mentioned players
		elif cmd == ewcfg.cmd_devour:
			response = ""
			roles_map_user = ewutils.getRoleMap(message.author.roles)
			is_copkiller = ewcfg.role_copkiller in roles_map_user
			is_rowdyfucker = ewcfg.role_rowdyfucker in roles_map_user

			if is_copkiller == False and is_rowdyfucker == False:
				response = "Know your place."
			else:
				if mentions_count == 0:
					response = "Devour who?"
				else:
					members_devoured = []
					members_na = []

					try:
						conn = ewutils.databaseConnect();
						cursor = conn.cursor();
						
						user_data = EwUser(member=message.author, conn=conn, cursor=cursor)

						# determine slime count for every member mentioned
						for member in mentions:
							roles_map_member = ewutils.getRoleMap(member.roles)

							if is_copkiller == True and ewcfg.role_copkillers in roles_map_member or is_rowdyfucker == True and ewcfg.role_rowdyfuckers in roles_map_member:

								# get slimes from the player
								member_data = EwUser(member=member, conn=conn, cursor=cursor)
								user_data.slimes += member_data.slimes

								# set player slimes to 0
								member_data.slimes = 0
								member_data.persist(conn=conn, cursor=cursor)

								members_devoured.append(member)
							else:
								members_na.append(member)

						# add slime to rf/ck
						user_data.persist(conn=conn, cursor=cursor)

						conn.commit()
					finally:
						cursor.close()
						conn.close()

					role_corpse = roles_map[ewcfg.role_corpse]
					for member in members_devoured:
						# update slime counts
						try:
							# set roles to corpse for mentioned players
							await client.replace_roles(member, role_corpse)
						except:
							pass

					if len(members_devoured) > 0:
						names = ewutils.userListToNameString(members_devoured)
						if len(members_na) > 0:
							response = '{} has been devoured. ({} was not devoured.)'.format(names, ewutils.userListToNameString(members_na))
						else:
							response = '{} has been devoured.'.format(names)
					elif len(members_na) > 0:
						response = '{} was not devoured.'.format(ewutils.userListToNameString(members_na))
					else:
						response = 'No one was devoured.'

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))

		# gives slime to the miner (message.author)
		elif cmd == ewcfg.cmd_mine:
			roles_map_user = ewutils.getRoleMap(message.author.roles)

			if ewcfg.role_corpse in roles_map_user:
				await client.send_message(message.channel, ewutils.formatMessage(message.author, "You can't mine while you're dead. Try {}.".format(ewcfg.cmd_revive)))
			else:
				if(message.channel.name == ewcfg.channel_mines):
					user_slimes = 0

					try:
						conn = ewutils.databaseConnect();
						cursor = conn.cursor();

						# Increment slimes for this user.
						user_data = EwUser(member=message.author, conn=conn, cursor=cursor)
						user_data.slimes += ewcfg.slimes_permine
						user_data.persist(conn=conn, cursor=cursor)

						conn.commit()
					finally:
						cursor.close()
						conn.close()
				else:
					await client.edit_message(resp, ewutils.formatMessage(message.author, "You can't mine here. Try #{}.".format(ewcfg.channel_mines)))

		# Show the current slime score of a player.
		elif cmd == ewcfg.cmd_score or cmd == ewcfg.cmd_score_alt1:
			response = ""

			if mentions_count == 0:
				user_slimes = EwUser(member=message.author).slimes

				# return my score
				response = "Your slime score is {} <:slime1:431564830541873182>".format(user_slimes)
			else:
				member = mentions[0]
				user_slimes = EwUser(member=member).slimes

				# return somebody's score
				response = "{}'s slime score is {} <:slime1:431564830541873182>".format(member.display_name, user_slimes)

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))

		# rowdy fucker and cop killer (leaders) can give slimes to anybody
		elif cmd == ewcfg.cmd_giveslime or cmd == ewcfg.cmd_giveslime_alt1:
			response = ""

			roles_map_user = ewutils.getRoleMap(message.author.roles)
			if (ewcfg.role_copkiller not in roles_map_user) and (ewcfg.role_rowdyfucker not in roles_map_user):
				response = "Only the Rowdy Fucker <:rowdyfucker:431275088076079105> and the Cop Killer <:copkiller:431275071945048075> can do that."
			else:
				if mentions_count == 0:
					response = "Give slimes to who?"
				else:
					if tokens_count > 1:
						value = None
						for token in tokens[1:]:
							try:
								value = int(token)
								break
							except:
								value = None

						if value != None:
							user_slimes = 0
							member_slimes = []
							try:
								conn = ewutils.databaseConnect();
								cursor = conn.cursor();

								user_data = EwUser(member=message.author, conn=conn, cursor=cursor)

								# determine slime count for every member mentioned
								for member in mentions:
									member_slimes.append(EwUser(member=member, conn=conn, cursor=cursor))
							finally:
								cursor.close()
								conn.close()

							if (value * mentions_count) > user_data.slimes:
								response = "You don't have that much slime to give ({}/{}).".format(user_data.slimes, (value * mentions_count))
							else:
								user_data.slimes -= (value * mentions_count)

								try:
									conn = ewutils.databaseConnect();
									cursor = conn.cursor();

									user_data.persist(conn=conn, cursor=cursor)

									# give value slimes to mentioned players
									for obj in member_slimes:
										obj.slimes += value
										obj.persist(conn=conn, cursor=cursor)

									conn.commit()
								finally:
									cursor.close()
									conn.close()

								response = "Slime scores altered! <:slime1:431564830541873182>"
								
						else:
							response = "Give how much slime?"

			# Send the response to the player.
			await client.edit_message(resp, ewutils.formatMessage(message.author, response))


		# !harvest is not a command
		elif cmd == ewcfg.cmd_harvest:
			await client.edit_message(resp, ewutils.formatMessage(message.author, '**HARVEST IS NOT A COMMAND YOU FUCKING IDIOT**'))

		# advertise help services
		elif cmd == ewcfg.cmd_help or cmd == ewcfg.cmd_help_alt1 or cmd == ewcfg.cmd_help_alt2:
			await client.edit_message(resp, ewutils.formatMessage(message.author, 'Send me a DM for help.'))

		# Debug command to override the role of a user
		elif debug == True and cmd == (ewcfg.cmd_prefix + 'setrole'):
			response = ""

			if mentions_count == 0:
				response = 'Set who\'s role?'
			else:
				role_target = tokens[1]
				role = roles_map.get(role_target)

				if role != None:
					for user in mentions:
						await client.replace_roles(user, role)

					response = 'Done.'
				else:
					response = 'Unrecognized role.'

			await client.edit_message(resp, ewutils.formatMessage(message.author, response))


		# didn't match any of the command words.
		else:
			""" couldn't process the command. bail out!! """
			""" bot rule 0: be cute """
			randint = random.randint(1,3)
			msg_mistake = "ENDLESS WAR is growing frustrated."
			if randint == 2:
				msg_mistake = "ENDLESS WAR denies you his favor."
			elif randint == 3:
				msg_mistake = "ENDLESS WAR pays you no mind."

			await asyncio.sleep(1)
			await client.edit_message(resp, msg_mistake)
			await asyncio.sleep(2)
			await client.delete_message(resp)

# find our REST API token
token = ewutils.getToken()

if token == None or len(token) == 0:
	print('Please place your API token in a file called "token", in the same directory as this script.')
	sys.exit(0)

# connect to discord and run indefinitely
client.run(token)