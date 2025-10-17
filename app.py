from router import route
import json
print('KIT719 QA System – Member C')
while True:
 q=input('\nYou> ').strip()
 if q.lower() in {'exit','quit','q'}: break
 r=route(q)
 print('Route:', r.get('route'))
 if 'rag' in r: print('\nRAG:', r['rag'].get('answer',''))
 if 'tool' in r: print('\nTool:', json.dumps(r['tool'], indent=2))
 if 'tools' in r: print('\nTools:', json.dumps(r['tools'], indent=2))
