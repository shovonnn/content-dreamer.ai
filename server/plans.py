import json


PLANS = [
    {
        'id': 'basic',
        'price_usd': 5,
        'stripe_price_id': None,  # set in env or later
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
        'stripe_price_id': None,
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
        'stripe_price_id': None,
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
