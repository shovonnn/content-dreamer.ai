from flask import request, jsonify
from functools import wraps
from werkzeug.exceptions import BadRequest
from wtforms import Form, StringField, validators
from wtforms.validators import DataRequired, Email
import json

class JSONForm(Form):
    def __init__(self, data, *args, **kwargs):
        super(JSONForm, self).__init__(formdata=None, *args, **kwargs)
        self.process(data=data)

def validate_request(validation_rules):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Define the form class inside the function to ensure it's fresh each time
            class DynamicRequestValidator(JSONForm):
                pass
            
            # Dynamically add fields to the form based on rules
            for field_name, rules in validation_rules.items():
                field_list = []
                if 'required' in rules:
                    field_list.append(DataRequired())
                if 'email' in rules:
                    field_list.append(Email())
                setattr(DynamicRequestValidator, field_name, StringField(validators=field_list))
            
            # Process JSON data with the form
            form = DynamicRequestValidator(data=request.get_json())

            if not form.validate():
                # Generate error message
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                error_message = "; ".join(error_messages)

                return jsonify({'message': error_message}), 400

            return f(*args, **kwargs)
        return decorated_function
    return decorator