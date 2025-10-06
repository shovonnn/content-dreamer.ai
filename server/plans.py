import json


import os


PLANS = [
    {
        'id': 'free',
        'price_usd': 0,
        'stripe_price_id': None,  # Free plan has no Stripe price
        'limits': {
            'products_per_user': 1,
            'content_generations_per_day': 1,
            'articles_per_day': 1,
            'guest_visibility_cutoff': 5,
        },
    },
    {
        'id': 'pro',
        'price_usd': 15,
        'stripe_price_id': os.getenv('STRIPE_PRICE_PRO'),
        'limits': {
            'products_per_user': 5,
            'content_generations_per_day': 5,
            'articles_per_day': 5,
            'guest_visibility_cutoff': 5,
        },
    },
    {
        'id': 'advanced',
        'price_usd': 50,
        'stripe_price_id': os.getenv('STRIPE_PRICE_ADVANCED'),
        'limits': {
            'products_per_user': -1,  # unlimited
            'content_generations_per_day': -1,
            'articles_per_day': -1,
            'guest_visibility_cutoff': 5,
        },
    },
]


def get_plans():
    return PLANS
