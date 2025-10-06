import stripe
import config

stripe.api_key = config.stripe_api_key

# Optionally provide webhook secret via env
webhook_secret = None
try:
	import os
	webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
except Exception:
	webhook_secret = None