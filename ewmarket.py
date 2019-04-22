import time
import random

# import ewcmd
import ewitem
import ewrolemgr
import ewutils
import ewcfg
import ewstats
from ew import EwUser

class EwMarket:
	id_server = ""

	clock = 0
	weather = 'sunny'
	day = 0

	slimes_casino = 0
	slimes_revivefee = 0

	market_rate = 1000
	exchange_rate = 1000000
	boombust = 0
	time_lasttick = 0
	negaslime = 0
	decayed_slimes = 0

	""" Load the market data for this server from the database. """
	def __init__(self, id_server = None):
		if(id_server != None):
			self.id_server = id_server

			try:
				conn_info = ewutils.databaseConnect()
				conn = conn_info.get('conn')
				cursor = conn.cursor();

				# Retrieve object
				cursor.execute("SELECT {time_lasttick}, {slimes_revivefee}, {negaslime}, {clock}, {weather}, {day}, {decayed_slimes} FROM markets WHERE id_server = %s".format(
					time_lasttick = ewcfg.col_time_lasttick,
					slimes_revivefee = ewcfg.col_slimes_revivefee,
					negaslime = ewcfg.col_negaslime,
					clock = ewcfg.col_clock,
					weather = ewcfg.col_weather,
					day = ewcfg.col_day,
					decayed_slimes = ewcfg.col_decayed_slimes
				), (self.id_server, ))
				result = cursor.fetchone();

				if result != None:
					# Record found: apply the data to this object.
					self.time_lasttick = result[0]
					self.slimes_revivefee = result[1]
					self.negaslime = result[2]
					self.clock = result[3]
					self.weather = result[4]
					self.day = result[5]
					self.decayed_slimes = result[6]
				else:
					# Create a new database entry if the object is missing.
					cursor.execute("REPLACE INTO markets(id_server) VALUES(%s)", (id_server, ))

					conn.commit()
			finally:
				# Clean up the database handles.
				cursor.close()
				ewutils.databaseClose(conn_info)

	""" Save market data object to the database. """
	def persist(self):
		try:
			conn_info = ewutils.databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			# Save the object.
			cursor.execute("REPLACE INTO markets ({id_server}, {time_lasttick}, {slimes_revivefee}, {negaslime}, {clock}, {weather}, {day}, {decayed_slimes}) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)".format(
				id_server = ewcfg.col_id_server,
				time_lasttick = ewcfg.col_time_lasttick,
				slimes_revivefee = ewcfg.col_slimes_revivefee,
				negaslime = ewcfg.col_negaslime,
				clock = ewcfg.col_clock,
				weather = ewcfg.col_weather,
				day = ewcfg.col_day,
				decayed_slimes = ewcfg.col_decayed_slimes
			), (
				self.id_server,
				self.time_lasttick,
				self.slimes_revivefee,
				self.negaslime,
				self.clock,
				self.weather,
				self.day,
				self.decayed_slimes
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			ewutils.databaseClose(conn_info)

class EwStock:
	id_server = ""

	# The stock's identifying string
	id_stock = ""

	market_rate = 1000

	exchange_rate = 1000000

	boombust = 0

	total_shares = 0

	timestamp = 0

	previous_entry = 0

	def __init__(self, id_server = None, stock = None, timestamp = None):
		if id_server is not None and stock is not None:
			self.id_server = id_server
			self.id_stock = stock

			# get stock data at specified timestamp
			if timestamp is not None:
				data = ewutils.execute_sql_query("SELECT {stock}, {market_rate}, {exchange_rate}, {boombust}, {total_shares}, {timestamp} FROM stocks WHERE id_server = %s AND {stock} = %s AND {timestamp} = %s".format(
					stock = ewcfg.col_stock,
					market_rate = ewcfg.col_market_rate,
					exchange_rate = ewcfg.col_exchange_rate,
					boombust = ewcfg.col_boombust,
					total_shares = ewcfg.col_total_shares,
					timestamp = ewcfg.col_timestamp
				), (
					id_server,
					stock,
					timestamp
				))
			# otherwise get most recent data
			else:

				data = ewutils.execute_sql_query("SELECT {stock}, {market_rate}, {exchange_rate}, {boombust}, {total_shares}, {timestamp} FROM stocks WHERE id_server = %s AND {stock} = %s ORDER BY {timestamp} DESC".format(
					stock = ewcfg.col_stock,
					market_rate = ewcfg.col_market_rate,
					exchange_rate = ewcfg.col_exchange_rate,
					boombust = ewcfg.col_boombust,
					total_shares = ewcfg.col_total_shares,
					timestamp = ewcfg.col_timestamp,
				), (
					id_server,
					stock
				))

			# slimecoin_total = ewutils.execute_sql_query()

			if len(data) > 0:  # if data is not empty, i.e. it found an entry
				# data is always a two-dimensional array and if we only fetch one row, we have to type data[0][x]
				self.id_stock = data[0][0]
				self.market_rate = data[0][1]
				self.exchange_rate = data[0][2]
				self.boombust = data[0][3]
				self.total_shares = data[0][4]
				self.timestamp = data[0][5]
				self.previous_entry = data[1] if len(data) > 1 else 0 #gets the previous stock
			else:  # create new entry
				self.timestamp = time.time()
				self.market_rate = ewcfg.default_stock_market_rate
				self.exchange_rate = ewcfg.default_stock_exchange_rate
				self.persist()

	def persist(self):
		ewutils.execute_sql_query("INSERT INTO stocks ({id_server}, {stock}, {market_rate}, {exchange_rate}, {boombust}, {total_shares}, {timestamp}) VALUES(%s, %s, %s, %s, %s, %s, %s)".format(
			id_server = ewcfg.col_id_server,
			stock = ewcfg.col_stock,
			market_rate = ewcfg.col_market_rate,
			exchange_rate = ewcfg.col_exchange_rate,
			boombust = ewcfg.col_boombust,
			total_shares = ewcfg.col_total_shares,
			timestamp = ewcfg.col_timestamp
		), (
			self.id_server,
			self.id_stock,
			self.market_rate,
			self.exchange_rate,
			self.boombust,
			self.total_shares,
			self.timestamp
		))

class EwCompany:
	id_server = ""

	id_stock = ""

	recent_profits = 0

	total_profits = 0

	""" Load the Company data from the database. """
	def __init__(self, id_server = None, stock = None):
		if id_server is not None and stock is not None:
			self.id_server = id_server
			self.id_stock = stock

			try:
				# Retrieve object
				result = ewutils.execute_sql_query("SELECT {recent_profits}, {total_profits} FROM companies WHERE {id_server} = %s AND {stock} = %s".format(
					recent_profits = ewcfg.col_recent_profits,
					total_profits = ewcfg.col_total_profits,
					id_server = ewcfg.col_id_server,
					stock = ewcfg.col_stock
				), (self.id_server, self.id_stock))

				if len(result) > 0:
					# Record found: apply the data to this object.
					self.recent_profits = result[0][0]
					self.total_profits = result[0][1]
				else:
					# Create a new database entry if the object is missing.
					self.persist()
			except:
				ewutils.logMsg("Failed to retrieve company {} from database.".format(self.id_stock))


	""" Save company data object to the database. """
	def persist(self):
		try:
			ewutils.execute_sql_query("REPLACE INTO companies({recent_profits}, {total_profits}, {id_server}, {stock}) VALUES(%s,%s,%s,%s)".format(
				recent_profits = ewcfg.col_recent_profits,
				total_profits = ewcfg.col_total_profits,
				id_server = ewcfg.col_id_server,
				stock = ewcfg.col_stock
			    ), (self.recent_profits, self.total_profits, self.id_server, self.id_stock ))
		except:
			ewutils.logMsg("Failed to save company {} to the database.".format(self.id_stock))

""" player invests slimecoin in the market """
async def invest(cmd):
	user_data = EwUser(member = cmd.message.author)
	time_now = int(time.time())

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = ewcfg.str_exchange_channelreq.format(currency = "SlimeCoin", action = "invest")
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		return

	if user_data.time_lastinvest + ewcfg.cd_invest > time_now:
		# Limit frequency of investments.
		response = ewcfg.str_exchange_busy.format(action = "invest")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	roles_map_user = ewutils.getRoleMap(cmd.message.author.roles)
	if ewcfg.role_rowdyfucker in roles_map_user or ewcfg.role_copkiller in roles_map_user:
		# Disallow investments by RF and CK kingpins.
		response = "You need that money to buy more videogames."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		value = None
		stock = None

		if cmd.tokens_count > 1:
			for token in cmd.tokens[1:]:
				if token.startswith('<@') == False and token.lower() not in ewcfg.stocks:
					value = ewutils.getIntToken(cmd.tokens, allow_all = True)
					break
			for token in cmd.tokens[1:]:
				if token.lower() in ewcfg.stocks:
					stock = token
					break


		if value != None:
			if value < 0:
				value = user_data.slimecoin
			if value <= 0:
				value = None

		if value != None:
			if stock != None:

				stock = EwStock(id_server = cmd.message.server.id, stock = stock)
				# basic exchange rate / 1000 = 1 share
				exchange_rate = (stock.exchange_rate / 1000.0)

				cost_total = int(value * 1.05)

				# gets the highest value possible where the player can still pay the fee
				if value == user_data.slimecoin:
					while cost_total > user_data.slimecoin:
						value -= cost_total - value
						cost_total = int(value * 1.05)

				# The user can only buy a whole number of shares, so adjust their cost based on the actual number of shares purchased.
				net_shares = int(value / exchange_rate)

				if user_data.slimecoin < cost_total:
					response = "You don't have enough SlimeCoin. ({:,}/{:,})".format(user_data.slimecoin, cost_total)

				elif value > user_data.slimecoin:
					response = "You don't have that much SlimeCoin to invest."

				elif net_shares == 0:
					response = "You don't have enough SlimeCoin to buy a share in {stock}".format(stock = ewcfg.stock_names.get(stock.id_stock))

				else:
					user_data.change_slimecoin(n = -cost_total, coinsource = ewcfg.stat_total_slimecoin_invested)
					shares = getUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user)
					shares += net_shares
					updateUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user, shares = shares)
					user_data.time_lastinvest = time_now

					stock.total_shares += net_shares
					response = "You invest {coin} SlimeCoin and receive {shares} shares in {stock}. Your slimebroker takes his nominal fee of {fee:,} SlimeCoin.".format(coin = value, shares = net_shares, stock = ewcfg.stock_names.get(stock.id_stock), fee = (cost_total - value))

					user_data.persist()
					stock.timestamp = int(time.time())
					stock.persist()

			else:
				response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(names = ewcfg.stocks))

		else:
			response = ewcfg.str_exchange_specify.format(currency = "SlimeCoin", action = "invest")

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" player withdraws slimecoin from the market """
async def withdraw(cmd):
	user_data = EwUser(member = cmd.message.author)
	time_now = int(time.time())

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = ewcfg.str_exchange_channelreq.format(currency = "SlimeCoin", action = "withdraw")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		value = None
		stock = None

		if cmd.tokens_count > 1:
			for token in cmd.tokens[1:]:
				if token.startswith('<@') == False and token.lower() not in ewcfg.stocks:
					value = ewutils.getIntToken(cmd.tokens, allow_all = True)
					break
			for token in cmd.tokens[1:]:
				if token.lower() in ewcfg.stocks:
					stock = token
					break

		total_shares = getUserTotalShares(id_server = user_data.id_server, stock = stock, id_user = user_data.id_user)

		if value != None:
			if value < 0:
				value = total_shares
			if value <= 0:
				value = None

		if value != None:
			stock = EwStock(id_server = cmd.message.server.id, stock = stock)

			if value <= total_shares:
				exchange_rate = (stock.exchange_rate / 1000.0)

				shares = value
				slimecoin = int(value * exchange_rate)

				if user_data.time_lastinvest + ewcfg.cd_invest > time_now:
					# Limit frequency of withdrawals
					response = ewcfg.str_exchange_busy.format(action = "withdraw")
				else:
					user_data.change_slimecoin(n = slimecoin, coinsource = ewcfg.stat_total_slimecoin_withdrawn)
					total_shares -= shares
					user_data.time_lastinvest = time_now
					stock.total_shares -= shares

					response = "You exchange {shares} shares in {stock} for {coins} SlimeCoin.".format(coins = slimecoin, shares = shares, stock = ewcfg.stock_names.get(stock.id_stock))
					user_data.persist()
					stock.timestamp = int(time.time())
					stock.persist()
					updateUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user, shares = total_shares)
			else:
				response = "You don't have that many shares in {stock} to exchange.".format(stock = ewcfg.stock_names.get(stock.id_stock))
		else:
			response = ewcfg.str_exchange_specify.format(currency = "SlimeCoin", action = "withdraw")

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" donate slime to slimecorp in exchange for slimecoin """
async def donate(cmd):
	time_now = int(time.time())

	if cmd.message.channel.name != ewcfg.channel_slimecorphq:
		# Only allowed in SlimeCorp HQ.
		response = "You must go to SlimeCorp HQ to donate slime."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		return

	user_data = EwUser(member = cmd.message.author)

	value = None
	if cmd.tokens_count > 1:
		value = ewutils.getIntToken(tokens = cmd.tokens, allow_all = True)

	if value != None:
		if value < 0:
			value = user_data.slimes
		if value <= 0:
			value = None

	if value != None and value < ewcfg.slimecoin_exchangerate:
		response = "You must volunteer to donate at least %d slime to receive compensation." % ewcfg.slimecoin_exchangerate

	elif value != None:
		# Amount of slime invested.
		cost_total = int(value)
		coin_total = int(value / ewcfg.slimecoin_exchangerate)

		if user_data.slimes < cost_total:
			response = "Acid-green flashes of light and bloodcurdling screams emanate from small window of SlimeCorp HQ. Unfortunately, you did not survive the procedure. Your body is dumped down a disposal chute to the sewers."
			user_data.die(cause = ewcfg.cause_donation)
			user_data.persist()
			# Assign the corpse role to the player. He dead.
			await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
			sewerchannel = ewutils.get_channel(cmd.message.server, ewcfg.channel_sewers)
			await ewutils.send_message(cmd.client, sewerchannel, "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(cmd.message.author, "You have died in a medical mishap. {}".format(ewcfg.emote_slimeskull)))
		else:
			# Do the transfer if the player can afford it.
			user_data.change_slimes(n = -cost_total, source = ewcfg.source_spending)
			user_data.change_slimecoin(n = coin_total, coinsource = ewcfg.coinsource_donation)
			user_data.time_lastinvest = time_now

			# Persist changes
			user_data.persist()

			response = "You stumble out of a Slimecorp HQ vault room in a stupor. You don't remember what happened in there, but your body hurts and you've got {slimecoin:,} shiny new SlimeCoin in your pocket.".format(slimecoin = coin_total)

	else:
		response = ewcfg.str_exchange_specify.format(currency = "slime", action = "donate")

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" transfer slimecoin between players """
async def xfer(cmd):
	time_now = int(time.time())

	if cmd.message.channel.name != ewcfg.channel_stockexchange:
		# Only allowed in the stock exchange.
		response = ewcfg.str_exchange_channelreq.format(currency = "SlimeCoin", action = "transfer")
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		return

	if cmd.mentions_count != 1:
		# Must have exactly one target to send to.
		response = "Mention the player you want to send SlimeCoin to."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		return

	member = cmd.mentions[0]
	target_data = EwUser(member = member)

	if target_data.life_state == ewcfg.life_state_kingpin:
		# Disallow transfers to RF and CK kingpins.
		response = "You can't transfer SlimeCoin to a known criminal warlord."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		return

	user_data = EwUser(member = cmd.message.author)
	market_data = EwMarket(id_server = cmd.message.author.server.id)

	if cmd.message.author.id == member.id:
		user_data.id_killer = cmd.message.author.id
		user_data.die(cause = ewcfg.cause_suicide)
		user_data.persist()

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Gaming the slimeconomy is punishable by death. SlimeCorp soldiers execute you immediately."))
		await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
		return

	# Parse the slime value to send.
	value = None
	if cmd.tokens_count > 1:
		value = ewutils.getIntToken(tokens = cmd.tokens)

	if value != None:
		if value < 0:
			value = user_data.slimes
		if value <= 0:
			value = None

	if value != None:
		# Cost including the 5% transfer fee.
		cost_total = int(value * 1.05)

		if user_data.slimecoin < cost_total:
			response = "You don't have enough SlimeCoin. ({:,}/{:,})".format(user_data.slimecoin, cost_total)
		else:
			# Do the transfer if the player can afford it.
			target_data.change_slimecoin(n = value, coinsource = ewcfg.coinsource_transfer)
			user_data.change_slimecoin(n = -cost_total, coinsource = ewcfg.coinsource_transfer)
			user_data.time_lastinvest = time_now

			# Persist changes
			response = "You transfer {slime:,} SlimeCoin to {target_name}. Your slimebroker takes his nominal fee of {fee:,} SlimeCoin.".format(slime = value, target_name = member.display_name, fee = (cost_total - value))

			target_data.persist()
			user_data.persist()
	else:
		response = ewcfg.str_exchange_specify.format(currency = "SlimeCoin", action = "transfer")

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" show the current market exchange rate """
async def rate(cmd):
	user_data = EwUser(member = cmd.message.author)

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = "You must go to the Slime Stock Exchange to check the current stock exchange rates ."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		stock = None

		if cmd.tokens_count > 0:
			stock = ewutils.formatNiceList(cmd.tokens[1:])

		if stock in ewcfg.stocks:
			stock = EwStock(id_server = cmd.message.server.id, stock = stock)
			response = "The current value of {stock} stocks is {cred} SlimeCoin per Share.".format(stock = ewcfg.stock_names.get(stock.id_stock), cred = int(stock.exchange_rate / 1000.0))
		else:
			response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(ewcfg.stocks))

		# Send the response to the player.
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" show player's shares in a stock """
async def shares(cmd):
	user_data = EwUser(member = cmd.message.author)
	stock = None

	if cmd.tokens_count > 0:
		stock = ewutils.formatNiceList(cmd.tokens[1:])

	if stock in ewcfg.stocks:
		stock = EwStock(id_server = cmd.message.server.id, stock = stock)
		shares = getUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user)
		shares_value = int(shares * (stock.exchange_rate / 1000.0))

		response = "You have {shares} shares in {stock}, currently valued at {coin} SlimeCoin.".format(shares = shares, stock = ewcfg.stock_names.get(stock.id_stock), coin = shares_value)
	else:
		response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(ewcfg.stocks))

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" show all interactable stocks in the market """
async def stocks(cmd):
	user_data = EwUser(member = cmd.message.author)

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = "You must go to the Slime Stock Exchange to check the currently available stocks."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
			response = "Here are the currently available stocks: {}".format(ewutils.formatNiceList(ewcfg.stocks))

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" show player's slimecoin balance """
async def slimecoin(cmd):
	if cmd.mentions_count == 0:
		coins = EwUser(member = cmd.message.author).slimecoin
		response = "You have {:,} SlimeCoin.".format(coins)
	else:
		member = cmd.mentions[0]
		coins = EwUser(member = member).slimecoin
		response = "{} has {:,} SlimeCoin.".format(member.display_name, coins)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" update stock values according to market activity """
def market_tick(stock_data, id_server):
	market_data = EwMarket(id_server = id_server)
	company_data = EwCompany(id_server = id_server, stock = stock_data.id_stock)

	# Nudge the value back to stability.
	market_rate = stock_data.market_rate
	if market_rate >= 1030:
		market_rate -= 10
	elif market_rate <= 970:
		market_rate += 10


	# Invest/Withdraw effects
	coin_rate = 0
	stock_at_last_tick = EwStock(id_server = id_server, stock = stock_data.id_stock, timestamp = market_data.time_lasttick)
	latest_stock = EwStock(id_server = id_server, stock = stock_data.id_stock)
	total_shares = [latest_stock.total_shares, stock_at_last_tick.total_shares]

	# Add profit bonus.
	profits = company_data.recent_profits
	profit_bonus = profits / 100 - 1 * ((latest_stock.exchange_rate / ewcfg.default_stock_exchange_rate) ** 0.2)
	profit_bonus = min(50, max(profit_bonus, -50))
	market_rate += (profit_bonus / 2)

	if total_shares[0] != total_shares[1]:
		# Positive if net investment, negative if net withdrawal.
		coin_change = (total_shares[0] - total_shares[1])
		coin_rate = ((coin_change * 1.0) / total_shares[1] if total_shares[1] != 0 else 1)

		if coin_rate > 1.0:
			coin_rate = 1.0
		elif coin_rate < -0.5:
			coin_rate = -0.5

		coin_rate = int((coin_rate * ewcfg.max_iw_swing) if coin_rate > 0 else (
					coin_rate * 2 * ewcfg.max_iw_swing))

	market_rate += coin_rate

	# Tick down the boombust cooldown.
	if stock_data.boombust < 0:
		stock_data.boombust += 1
	elif stock_data.boombust > 0:
		stock_data.boombust -= 1

	# Adjust the market rate.
	fluctuation = 0  # (random.randrange(5) - 2) * 100
	noise = (random.randrange(19) - 9) * 2
	subnoise = (random.randrange(13) - 6)

	# Some extra excitement!
	if noise == 0 and subnoise == 0:
		boombust = (random.randrange(3) - 1) * 200

		# If a boombust occurs shortly after a previous boombust, make sure it's the opposite effect. (Boom follows bust, bust follows boom.)
		if (stock_data.boombust > 0 and boombust > 0) or (stock_data.boombust < 0 and boombust < 0):
			boombust *= -1

		if boombust != 0:
			stock_data.boombust = ewcfg.cd_boombust

			if boombust < 0:
				stock_data.boombust *= -1
	else:
		boombust = 0

	market_rate += fluctuation + noise + subnoise + boombust
	if market_rate < 300:
		market_rate = (300 + noise + subnoise)

	#percentage = ((market_rate / 10) - 100)
	#percentage_abs = percentage * -1


	exchange_rate_increase = int((market_rate - ewcfg.default_stock_market_rate) * ewcfg.default_stock_exchange_rate / ewcfg.default_stock_market_rate)

	percentage = exchange_rate_increase / stock_data.exchange_rate
	percentage_abs = percentage * -1


	# negative exchange rate causes problems, duh
	exchange_rate_increase = max(exchange_rate_increase, -stock_data.exchange_rate)

	points = abs(exchange_rate_increase / 1000.0)

	stock_data.exchange_rate += exchange_rate_increase
	stock_data.market_rate = market_rate


	stock_data.persist()

	company_data.total_profits += company_data.recent_profits
	company_data.recent_profits = 0
	company_data.persist()

	# Give some indication of how the market is doing to the users.
	response = ewcfg.stock_emotes.get(stock_data.id_stock) + ' ' + ewcfg.stock_names.get(stock_data.id_stock) + ' '

	# Market is up ...
	if market_rate > 1200:
		response += 'is skyrocketing!!! Slime stock is up {p:.3g} points!!!'.format(p = points)
	elif market_rate > 1100:
		response += 'is booming! Slime stock is up {p:.3g} points!'.format(p = points)
	elif market_rate > 1000:
		response += 'is doing well. Slime stock is up {p:.3g} points.'.format(p = points)
	# Market is down ...
	elif market_rate < 800:
		response += 'is plummeting!!! Slime stock is down {p:.3g} points!!!'.format(p = points)
	elif market_rate < 900:
		response += 'is stagnating! Slime stock is down {p:.3g} points!'.format(p = points)
	elif market_rate < 1000:
		response += 'is a bit sluggish. Slime stock is down {p:.3g} points.'.format(p = points)
	# Perfectly balanced
	else:
		response += 'is holding steady. No change in slime stock value.'

	response += ' ' + ewcfg.stock_emotes.get(stock_data.id_stock)

	# Send the announcement.
	return response

""" Returns an array of the most recent counts of all invested slime coin, from newest at 0 to oldest. """
def getRecentTotalShares(id_server=None, stock=None, count=2):
	if id_server != None and stock != None:

		values = []

		try:

			count = int(count)
			data = ewutils.execute_sql_query("SELECT {total_shares} FROM stocks WHERE {id_server} = %s AND {stock} = %s ORDER BY {timestamp} DESC LIMIT %s".format(
				stock = ewcfg.col_stock,
				total_shares = ewcfg.col_total_shares,
				id_server = ewcfg.col_id_server,
				timestamp = ewcfg.col_timestamp,
			), (
				id_server,
				stock,
				(count if (count > 0) else 2)
			))

			for row in data:
				values.append(row[0])

			# Make sure we return at least one value.
			if len(values) == 0:
				values.append(0)

			# If we don't have enough data, pad out to count with the last value in the array.
			value_last = values[-1]
			while len(values) < count:
				values.append(value_last)
		except:
			pass
		finally:
			return values

"""" returns the total number of shares a player has in a certain stock """
def getUserTotalShares(id_server=None, stock=None, id_user=None):
	if id_server != None and stock != None and id_user != None:

		values = 0

		try:

			data = ewutils.execute_sql_query("SELECT {shares} FROM {shares} WHERE {id_server} = %s AND {id_user} = %s AND {stock} = %s".format(
				stock = ewcfg.col_stock,
				shares = ewcfg.col_shares,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				id_server,
				id_user,
				stock,
			))

			for row in data:
				values = row[0]
		except:
			pass
		finally:
			return values

"""" updates the total number of shares a player has in a certain stock """
def updateUserTotalShares(id_server=None, stock=None, id_user=None, shares=0):
	if id_server != None and stock != None and id_user != None:

		values = 0

		try:

			ewutils.execute_sql_query("REPLACE INTO shares({id_server}, {id_user}, {stock}, {shares}) VALUES(%s, %s, %s, %s)".format(
				stock = ewcfg.col_stock,
				shares = ewcfg.col_shares,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				id_server,
				id_user,
				stock,
				shares,
			))
		except:
			pass


