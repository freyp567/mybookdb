"""
give django templates access to particular context info
see
https://stackoverflow.com/questions/43207563/how-can-i-access-environment-variables-directly-in-a-django-template/43211490
and TEMPLATE_CONTEXT_PROCESSORS in settings.py
"""

import os 

def export_vars(request):
    data = {}
    if os.environ.get("LIBRARYTHING_APIKEY"):
        data['USE_LIBRARYTHING'] = '1'
    if os.environ.get("ONLEIHE_URL"):
        data['USE_ONLEIHE'] = '1'
    return data