import json

SERVER_CONFIG_TEMPLATE = {'inbounds': [
    {'port': 16823,
     'protocol': 'vmess',
     'settings': {
         'clients': [
             {'id': 'b831381d-6324-4d53-ad4f-8cda48b30811',
              'alterId': 0}]}}],
    'outbounds': [
        {'protocol': 'freedom',
         'settings': {}}]}