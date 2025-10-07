import openai
import config
from openai import OpenAI
from cache import cache_store
import json
import re
from config import logger
from tenacity import retry, stop_after_attempt, wait_random_exponential
from models.db_utils import db
from models.user import User
from models.credit_ledger import CreditLedger
from dataclasses import dataclass
import tiktoken

openai.api_key = config.openai_key

openai_client = OpenAI(api_key=config.openai_key)


def generate_job_description(user:User, title, short_description):
    system_content = f"""
Generate a job description for a job titled '{title}' with the following short description: '{short_description}'
Reply in following json format:
{{"content": "full job description here"}}    
    """
    response = get_reply_json(user, system_content, '')
    return response['content']

def generate_instructions(user: User, title, short_description, full_description):
    system_content = f"""
Generate instructions for QuickScreener AI which will generate questions for each applicants based on the submitted CV and determine if the applicant is right fit.
Job Title: '{title}'
Short description: '{short_description}' 
Full description: {full_description}
Reply in following json format:
{{"content": "instructions here"}}    
    """
    response = get_reply_json(user, system_content, '')
    return response['content']

def num_tokens(string: str, model_name: str = 'gpt-4') -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.model.encoding_for_model(model_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def _extract_outer_brackets(text, startChar, endChar):
    bracket_stack = []
    matches = []

    for index, char in enumerate(text):
        if char == startChar:
            bracket_stack.append(index)
        elif char == endChar:
            if not bracket_stack:
                continue
            start = bracket_stack.pop()
            if not bracket_stack:
                matches.append(text[start:index + 1])

    return matches

# @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(4))
def get_reply_json(user: User | None, system_content, user_msg, additional_messages=None, bracket_start='{', bracket_end='}'):
  try:
    content = get_reply(user, system_content, user_msg, additional_messages)
  except Exception as e:
    logger.exception(e)
    raise e
  json_match = _extract_outer_brackets(content, bracket_start, bracket_end)
  if len(json_match) == 0:
    logger.info(content)
    raise Exception("Error parsing json response")
  try:
    response = json.loads(json_match[0])
    return response
  except Exception as e:
    logger.info(content)
    raise e

def get_reply(user: User | None, system_content, user_msg, additional_messages=None):
    model = 'gpt-5-mini'
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_msg},
    ]
    if additional_messages:
        messages += additional_messages
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages
    )
    if response.usage and user and getattr(user, 'id', None):
        prompts = response.usage.prompt_tokens
        completion = response.usage.completion_tokens
        cost = CreditLedger.calculate_cost(prompts/1000, completion/1000, model)
        CreditLedger.create(user.id, 0, cost, model)

    return response.choices[0].message.content


def generate_image_base64(prompt: str, size: str = '1024x1024') -> str:
    """Generate an image with OpenAI image model and return base64 PNG string.

    Uses gpt-image-1 per product spec. May raise on failure.
    """
    try:
        res = openai_client.images.generate(
            model='gpt-image-1',
            prompt=prompt,
            size=size,
            quality="high",
        )
        data = res.data[0].b64_json if getattr(res, 'data', None) else None
        if not data:
            raise RuntimeError('No image data returned')
        return data
    except Exception as e:
        logger.exception(e)
        raise