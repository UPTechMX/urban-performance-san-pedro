from django import template

register = template.Library()

color_list = ["bau", "vision", "my"]


@register.filter
def color(val):
    val = int(val) % 3
    return color_list[val]
