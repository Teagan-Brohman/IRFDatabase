from django import template

register = template.Library()


@register.filter
def split_locations(value):
    """Split comma-separated locations and return as list"""
    if not value:
        return []
    locations = [loc.strip() for loc in value.split(',')]
    return locations


@register.filter
def format_location(value):
    """Format location slug to display name"""
    location_map = {
        'bare_rabbit_tube': 'Bare Rabbit Tube',
        'cadmium_rabbit_tube': 'Cadmium Rabbit Tube',
        'beam_port': 'Beam Port',
        'thermal_column': 'Thermal Column',
        'other': 'Other',
        # Legacy support for old format
        'bare_rabbit': 'Bare Rabbit Tube',
        'cad_rabbit': 'Cadmium Rabbit Tube',
    }
    return location_map.get(value, value.replace('_', ' ').title())
