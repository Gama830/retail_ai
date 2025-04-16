from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter(is_safe=True)
def safe_json(obj):
    """Safe JSON filter that handles Django QuerySets and models."""
    # Convert the dict of {Product: [Forecast, ...]} to {product_id: [{data}, ...]}
    data_for_json = {}
    for product, forecast_list in obj.items():
        data_for_json[product.id] = [
            {
                'date': f.date.isoformat(), # Format date as YYYY-MM-DD
                'predicted_demand': f.predicted_demand,
                'lower_bound': f.lower_bound,
                'upper_bound': f.upper_bound
            }
            for f in forecast_list
        ]
    
    # Dump the processed dictionary to JSON using Django's encoder
    json_string = json.dumps(data_for_json, cls=DjangoJSONEncoder)
    
    # Escape characters that could break HTML/JS
    escaped_json_string = (
        json_string.replace("<", "\\u003c")
                   .replace(">", "\\u003e")
                   .replace("&", "\\u0026")
    )
    return mark_safe(escaped_json_string) 